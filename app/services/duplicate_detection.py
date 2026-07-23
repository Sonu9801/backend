import hashlib
from difflib import SequenceMatcher
from sqlalchemy.orm import Session
from app.models.invoice import Invoice
from app.models.sales_invoice import SalesInvoice

class DuplicateDetectionService:
    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        """
        Layer 1: Generate SHA-256 hash of the uploaded file.
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read and update hash string value in blocks of 4K
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    @staticmethod
    def check_hash_exists(db: Session, file_hash: str, model_class=Invoice) -> bool:
        """
        Check if the file hash already exists in the database.
        """
        if not file_hash:
            return False
        return db.query(model_class).filter(model_class.file_hash == file_hash).first() is not None

    @staticmethod
    def check_invoice_number(db: Session, invoice_number: str, party_name: str, model_class=Invoice) -> bool:
        """
        Layer 2: Compare Invoice Number and Vendor/Customer Name.
        """
        if not invoice_number or not party_name:
            return False
            
        if model_class == Invoice:
            return db.query(model_class).filter(
                model_class.invoice_number == invoice_number,
                model_class.vendor_name == party_name
            ).first() is not None
        else:
            return db.query(model_class).filter(
                model_class.invoice_number == invoice_number,
                model_class.customer_name == party_name
            ).first() is not None

    @staticmethod
    def check_business_rules(db: Session, data: dict, model_class=Invoice) -> bool:
        """
        Layer 3: Compare Invoice Number, Vendor/Customer GSTIN, Invoice Date, Grand Total, and GST Amount.
        """
        invoice_number = data.get("invoice_number")
        
        if model_class == Invoice:
            party_gstin = data.get("vendor_gstin")
        else:
            party_gstin = data.get("customer_gstin")
            
        invoice_date = data.get("invoice_date")
        grand_total = data.get("grand_total")
        gst_amount = data.get("gst_amount")

        if not invoice_number or not party_gstin:
            return False

        # Strictly check for identical record
        if model_class == Invoice:
            return db.query(model_class).filter(
                model_class.invoice_number == invoice_number,
                model_class.vendor_gstin == party_gstin,
                model_class.invoice_date == invoice_date,
                model_class.grand_total == grand_total,
                model_class.gst_amount == gst_amount
            ).first() is not None
        else:
            return db.query(model_class).filter(
                model_class.invoice_number == invoice_number,
                model_class.customer_gstin == party_gstin,
                model_class.invoice_date == invoice_date,
                model_class.grand_total == grand_total,
                model_class.gst_amount == gst_amount
            ).first() is not None

    @staticmethod
    def calculate_similarity(db: Session, data: dict, model_class=Invoice) -> bool:
        """
        Layer 4: OCR Similarity Validation.
        Check recent invoices and compute similarity across key fields.
        Returns True if a highly similar invoice (>95%) is found.
        """
        recent_invoices = db.query(model_class).order_by(model_class.id.desc()).limit(1000).all()
        
        party_name = data.get('vendor_name') if model_class == Invoice else data.get('customer_name')
        
        target_str = f"{party_name} {data.get('invoice_number')} {data.get('invoice_date')} {data.get('grand_total')} {data.get('gst_amount')}".lower()
        
        for inv in recent_invoices:
            inv_party = inv.vendor_name if model_class == Invoice else inv.customer_name
            inv_str = f"{inv_party} {inv.invoice_number} {inv.invoice_date} {inv.grand_total} {inv.gst_amount}".lower()
            similarity = SequenceMatcher(None, target_str, inv_str).ratio()
            
            if similarity > 0.95:
                return True
                
        return False
