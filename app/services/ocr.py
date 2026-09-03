import os
import json
import re
from PIL import Image, ImageOps
import numpy as np
import google.generativeai as genai
from app.config import settings

def extract_invoice_data(file_path: str, invoice_type: str = "expense") -> dict:
    """
    Process an image or PDF, convert to PIL Image with EXIF orientation correction,
    and parse required fields using Gemini AI Vision with automatic model fallbacks and multi-angle orientation trial.
    Returns a dictionary of extracted fields.
    """
    try:
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "paste_your_key_here":
            print("WARNING: GEMINI_API_KEY is not set or invalid.")
            raise ValueError("GEMINI_API_KEY is not set in environment.")

        # Configure Gemini
        genai.configure(api_key=settings.GEMINI_API_KEY)
        
        # Candidate vision models sequence
        candidate_models = [
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-flash-latest",
            "gemini-2.5-flash",
            "gemini-flash-lite-latest"
        ]
        
        if invoice_type == "expense":
            prompt = """
            Analyze this tax invoice / purchase bill document image carefully and extract the requested fields.
            NOTE: This document image might be taken from a phone camera and could be oriented sideways, upside down, or vertically (90°, 180°, 270°). Read text in any orientation.
            
            Return ONLY a valid JSON object matching this structure with no extra text or markdown:
            {
              "invoice_number": "string (e.g. INV-102 or Invoice No)",
              "vendor_name": "string (Company / Vendor header name)",
              "vendor_gstin": "string (15-digit GSTIN format e.g. 06AAAAA0000A1Z5)",
              "invoice_date": "YYYY-MM-DD (e.g. 2026-07-28 or converted to YYYY-MM-DD)",
              "hsn_sac": "string (HSN or SAC code if available)",
              "cgst": float,
              "sgst": float,
              "igst": float,
              "gst_amount": float,
              "subtotal": float,
              "grand_total": float
            }
            """
        else:
            prompt = """
            Analyze this sales invoice / dispatch bill document image carefully and extract the requested fields.
            NOTE: This document image might be taken from a phone camera and could be oriented sideways, upside down, or vertically (90°, 180°, 270°). Read text in any orientation.

            Return ONLY a valid JSON object matching this structure with no extra text or markdown:
            {
              "invoice_number": "string (or null)",
              "customer_name": "string (or null)",
              "customer_gstin": "string (or null)",
              "invoice_date": "YYYY-MM-DD (or null)",
              "po_number": "string (or null)",
              "vehicle_number": "string (or null)",
              "oem": "string (or null)",
              "hsn_sac": "string (or null)",
              "cgst": float,
              "sgst": float,
              "igst": float,
              "gst_amount": float,
              "subtotal": float,
              "grand_total": float,
              "payment_terms": "string (or null)",
              "due_date": "YYYY-MM-DD (or null)"
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
                zoom = 2.0  # zoom factor for high resolution OCR
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                
                mode = "RGBA" if pix.alpha else "RGB"
                pil_img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
                pil_img = pil_img.convert('RGB')
            except Exception as e:
                raise ValueError(f"Failed to convert PDF using PyMuPDF. Error: {str(e)}")
        else:
            try:
                raw_img = Image.open(file_path)
                # Auto-rotate image according to EXIF orientation metadata tag
                pil_img = ImageOps.exif_transpose(raw_img).convert('RGB')
            except Exception:
                raise ValueError("Could not read image file.")

        # Downscale large smartphone photos to max 1800px to avoid memory & payload timeouts
        if pil_img and max(pil_img.width, pil_img.height) > 1800:
            pil_img.thumbnail((1800, 1800), Image.Resampling.LANCZOS)

        def run_model_extraction(img_obj):
            for model_name in candidate_models:
                try:
                    model = genai.GenerativeModel(model_name)
                    res = model.generate_content([img_obj, prompt], request_options={"timeout": 25})
                    if res and res.text:
                        print(f"[OCR] Successfully extracted using Gemini model '{model_name}'!")
                        return res.text
                except Exception as e:
                    print(f"[OCR WARNING] Model '{model_name}' failed: {e}. Trying next model...")
            return None

        # Trial 1: Original Image
        result_text = run_model_extraction(pil_img)
        
        # Helper to parse & sanitize JSON/Text
        def parse_and_sanitize(text_in):
            if not text_in:
                return {}
            text_str = text_in.strip()
            data = {}
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text_str, re.DOTALL)
            if json_match:
                raw_json = json_match.group(1)
            else:
                json_match = re.search(r'\{.*?\}', text_str, re.DOTALL)
                raw_json = json_match.group(0) if json_match else text_str

            try:
                data = json.loads(raw_json)
            except Exception:
                # Regex Fallback Extractor
                data = {}
                gstin_m = re.search(r'\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z0-9]{1}Z[A-Z0-9]{1}\b', text_str, re.IGNORECASE)
                if gstin_m:
                    data["vendor_gstin" if invoice_type == "expense" else "customer_gstin"] = gstin_m.group(0).upper()
                    
                date_m = re.search(r'\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})\b', text_str)
                if date_m:
                    d, m, y = date_m.groups()
                    data["invoice_date"] = f"{y}-{int(m):02d}-{int(d):02d}"
                    
                inv_m = re.search(r'(?:Invoice|Bill|Inv)\s*(?:No|Number|#)?[.:\s]*([A-Za-z0-9/-]+)', text_str, re.IGNORECASE)
                if inv_m:
                    data["invoice_number"] = inv_m.group(1).strip()
                    
                amounts = [float(x.replace(',', '')) for x in re.findall(r'\b\d{1,6}(?:\.\d{2})?\b', text_str) if '.' in x]
                if amounts:
                    data["grand_total"] = max(amounts)
            return data

        extracted_data = parse_and_sanitize(result_text)
        has_primary = bool(extracted_data.get("invoice_number") or extracted_data.get("vendor_name") or extracted_data.get("customer_name") or extracted_data.get("grand_total"))

        # Trial 2: If Trial 1 yields 0 primary fields, try rotating 90 deg (270 CW)
        if not has_primary and not file_path.lower().endswith('.pdf'):
            print("[OCR INFO] Trial 1 yielded empty fields. Attempting 90° image rotation trial...")
            try:
                img_rot90 = pil_img.rotate(270, expand=True)
                result_text2 = run_model_extraction(img_rot90)
                extracted_data2 = parse_and_sanitize(result_text2)
                has_primary2 = bool(extracted_data2.get("invoice_number") or extracted_data2.get("vendor_name") or extracted_data2.get("customer_name") or extracted_data2.get("grand_total"))
                if has_primary2:
                    extracted_data = extracted_data2
                    has_primary = True
            except Exception as rot_err:
                print("[OCR WARNING] Rotation trial failed:", rot_err)

        # Sanitize float fields
        float_fields = ['cgst', 'sgst', 'igst', 'gst_amount', 'subtotal', 'grand_total']
        for field in float_fields:
            val = extracted_data.get(field)
            if val is None or str(val).strip().lower() in ["", "null", "none", "n/a"]:
                extracted_data[field] = 0.0
            else:
                try:
                    val_clean = re.sub(r'[^\d.]', '', str(val))
                    extracted_data[field] = float(val_clean) if val_clean else 0.0
                except (ValueError, TypeError):
                    extracted_data[field] = 0.0

        # Sanitize date fields (Format to YYYY-MM-DD)
        date_fields = ["invoice_date", "due_date"]
        for d_field in date_fields:
            date_val = extracted_data.get(d_field)
            if date_val:
                date_str = str(date_val).strip()
                m_dmy = re.match(r'^(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})$', date_str)
                if m_dmy:
                    day, month, year = m_dmy.groups()
                    extracted_data[d_field] = f"{year}-{int(month):02d}-{int(day):02d}"
                elif re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                    extracted_data[d_field] = date_str
                else:
                    extracted_data[d_field] = None
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

        # Compute calculated confidence based on extracted key fields
        extracted_keys = sum(1 for k, v in extracted_data.items() if v not in [None, 0.0, 0, "", "0.0"])
        total_keys = len(extracted_data)
        
        if has_primary:
            confidence = round(min(98.5, max(85.0, (extracted_keys / max(total_keys, 1)) * 100)), 1)
        else:
            confidence = 0.0

        extracted_data["ocr_confidence_score"] = confidence
        
        return extracted_data

    except Exception as e:
        print(f"Gemini OCR Error: {str(e)}")
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
