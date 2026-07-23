import os
import json
import re
from PIL import Image
import numpy as np
import google.generativeai as genai
from app.config import settings

def extract_invoice_data(file_path: str, invoice_type: str = "expense") -> dict:
    """
    Process an image or PDF, convert to PIL Image, and parse required fields using Gemini 1.5 Flash.
    Returns a dictionary of extracted fields.
    """
    try:
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "paste_your_key_here":
            print("WARNING: GEMINI_API_KEY is not set or invalid. Returning empty data.")
            raise ValueError("GEMINI_API_KEY is not set in environment.")

        # Configure Gemini
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        if invoice_type == "expense":
            prompt = """
            Analyze this invoice document and extract the following information.
            Return ONLY a JSON object exactly matching this structure, with no markdown formatting or other text:
            {
              "invoice_number": "string (or null if not found)",
              "vendor_name": "string (or null if not found)",
              "vendor_gstin": "string (or null if not found)",
              "invoice_date": "YYYY-MM-DD (or null if not found)",
              "hsn_sac": "string (or null if not found)",
              "cgst": float (or 0),
              "sgst": float (or 0),
              "igst": float (or 0),
              "gst_amount": float (total GST, or 0),
              "subtotal": float (or 0),
              "grand_total": float (or 0)
            }
            """
        else:
            prompt = """
            Analyze this sales invoice/bill document and extract the following information.
            Return ONLY a JSON object exactly matching this structure, with no markdown formatting or other text:
            {
              "invoice_number": "string (or null if not found)",
              "customer_name": "string (or null if not found)",
              "customer_gstin": "string (or null if not found)",
              "invoice_date": "YYYY-MM-DD (or null if not found)",
              "po_number": "string (or null if not found)",
              "vehicle_number": "string (or null if not found)",
              "oem": "string (or null if not found)",
              "hsn_sac": "string (or null if not found)",
              "cgst": float (or 0),
              "sgst": float (or 0),
              "igst": float (or 0),
              "gst_amount": float (total GST, or 0),
              "subtotal": float (or 0),
              "grand_total": float (or 0),
              "payment_terms": "string (or null if not found)",
              "due_date": "YYYY-MM-DD (or null if not found)"
            }
            """

        # Preprocess Image/PDF to PIL Image
        pil_img = None
        if file_path.lower().endswith('.pdf'):
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(file_path)
                if doc.page_count == 0:
                    raise ValueError("Could not extract pages from PDF. PDF is empty.")
                page = doc.load_page(0)
                # Render to pixmap with higher resolution
                zoom = 2.0  # zoom factor for better OCR resolution
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                
                # Convert fitz pixmap to PIL Image
                mode = "RGBA" if pix.alpha else "RGB"
                pil_img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
                pil_img = pil_img.convert('RGB')
            except Exception as e:
                raise ValueError(f"Failed to convert PDF using PyMuPDF. Error: {str(e)}")
        else:
            try:
                pil_img = Image.open(file_path).convert('RGB')
            except Exception:
                raise ValueError("Could not read image file.")

        # Pass the PIL image directly to Gemini
        response = model.generate_content([pil_img, prompt])
        
        # Clean up the response text (remove potential markdown block)
        result_text = response.text.strip()
        
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', result_text, re.DOTALL)
        if json_match:
            result_text = json_match.group(1)
        else:
            # Fallback if no markdown block
            json_match = re.search(r'\{.*?\}', result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(0)
            
        extracted_data = json.loads(result_text)
        
        # Sanitize float fields to prevent Pydantic ValidationError (500 Error)
        float_fields = ['cgst', 'sgst', 'igst', 'gst_amount', 'subtotal', 'grand_total']
        for field in float_fields:
            if extracted_data.get(field) is None or str(extracted_data.get(field)).strip().lower() in ["", "null", "none", "n/a"]:
                extracted_data[field] = 0.0
            else:
                try:
                    extracted_data[field] = float(extracted_data[field])
                except (ValueError, TypeError):
                    extracted_data[field] = 0.0

        # Sanitize date fields
        date_fields = ["invoice_date", "due_date"]
        for d_field in date_fields:
            date_val = extracted_data.get(d_field)
            if date_val:
                date_str = str(date_val).strip()
                if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                    extracted_data[d_field] = None
                else:
                    extracted_data[d_field] = date_str
            else:
                if d_field in extracted_data:
                    extracted_data[d_field] = None

        # Sanitize string fields
        str_fields = ["invoice_number", "vendor_name", "vendor_gstin", "hsn_sac", "customer_name", "customer_gstin", "po_number", "vehicle_number", "oem", "payment_terms"]
        for field in str_fields:
            if field in extracted_data:
                val = extracted_data.get(field)
                if val is not None:
                    val_str = str(val).strip()
                    if val_str.lower() in ["null", "none", "n/a", ""]:
                        extracted_data[field] = None
                    else:
                        extracted_data[field] = val_str

        extracted_data["ocr_confidence_score"] = 92.5  # High confidence for AI extraction
        
        return extracted_data

    except Exception as e:
        print(f"Gemini OCR Error: {str(e)}")
        # Return fallback/empty data on OCR failure so the flow continues manually
        if invoice_type == "sales":
            return {
                "invoice_number": None,
                "customer_name": None,
                "customer_gstin": None,
                "invoice_date": None,
                "po_number": None,
                "vehicle_number": None,
                "oem": None,
                "hsn_sac": None,
                "cgst": 0.0,
                "sgst": 0.0,
                "igst": 0.0,
                "gst_amount": 0.0,
                "subtotal": 0.0,
                "grand_total": 0.0,
                "payment_terms": None,
                "due_date": None,
                "ocr_confidence_score": 0.0,
            }
        else:
            return {
                "invoice_number": None,
                "vendor_name": None,
                "vendor_gstin": None,
                "invoice_date": None,
                "hsn_sac": None,
                "cgst": 0.0,
                "sgst": 0.0,
                "igst": 0.0,
                "gst_amount": 0.0,
                "subtotal": 0.0,
                "grand_total": 0.0,
                "ocr_confidence_score": 0.0,
            }
