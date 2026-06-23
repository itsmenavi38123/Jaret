import os
from typing import Tuple, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from docx import Document as DocxDocument
from app.db import get_collection

# Windows-native path to ensure reportlab and os.open can write to disk correctly
UPLOAD_ROOT = Path(r"C:\Users\Admin\OneDrive\Desktop\jret\Jaret\Jaret\storage\documents")

class DocumentStoreService:
    def __init__(self):
        self.base_storage_path = UPLOAD_ROOT
        self.collection_name = "documents_metadata"
        try:
            self.base_storage_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Storage directory creation warning: {e}")

    async def get_metadata(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves metadata for a specific document."""
        docs_coll = get_collection(self.collection_name)
        return await docs_coll.find_one({"document_id": doc_id})

    async def save_uploaded_file(self, customer_id: str, file_content: bytes, filename: str, uploaded_by: str, location_id: Optional[str] = None) -> Tuple[str, str]:
        """Saves the original uploaded file to the store."""
        import uuid
        doc_id = f"doc_{uuid.uuid4().hex}"
        
        customer_dir = self.base_storage_path / customer_id
        customer_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = customer_dir / f"{doc_id}_{filename}"
        
        with open(file_path, "wb") as f:
            f.write(file_content)
            
        docs_coll = get_collection(self.collection_name)
        await docs_coll.insert_one({
            "document_id": doc_id,
            "customer_id": customer_id,
            "location_id": location_id,
            "original_filename": filename,
            "original_format": filename.split('.')[-1].lower() if '.' in filename else 'txt',
            "working_format": filename.split('.')[-1].lower() if '.' in filename else 'txt',
            "upload_timestamp": datetime.utcnow(),
            "uploaded_by": uploaded_by,
            "extraction_status": "pending",
            "outdated": False,
            "file_path": str(file_path)
        })
        
        return doc_id, str(file_path)

    async def convert_to_pdf(self, doc_id: str, original_path: str):
        """
        Implementation of Section 6A: Office Document Conversion.
        Converts office docs to PDF for the Vision Agent.
        Text and spreadsheets are NOT converted to ensure they follow the text path.
        """
        docs_coll = get_collection(self.collection_name)
        doc_meta = await docs_coll.find_one({"document_id": doc_id})
        if not doc_meta:
            return

        ext = doc_meta.get("original_format", "").lower()
        
        # Only convert visual-heavy formats. Skip text/data formats to preserve Opus routing.
        if ext in ["pdf", "txt", "md", "csv", "xlsx"]:
            return 

        orig_p = Path(original_path)
        pdf_path = orig_p.with_suffix('.pdf')
        
        try:
            if ext == "docx":
                doc = DocxDocument(str(orig_p))
                full_text = [para.text for para in doc.paragraphs]
                text_content = "\n".join(full_text)
                self._text_to_pdf(text_content, str(pdf_path))
            
            await docs_coll.update_one(
                {"document_id": doc_id},
                {"$set": {"working_format": "pdf", "pdf_path": str(pdf_path)}}
            )
        except Exception as e:
            print(f"Conversion error for {doc_id}: {e}")

    def _text_to_pdf(self, text: str, output_path: str):
        """Helper to convert raw text into a PDF file using reportlab."""
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        # Ensure the directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        c = canvas.Canvas(output_path, pagesize=letter)
        text_object = c.beginText(50, 750)
        text_object.setFont("Helvetica", 10)
        
        lines = text.split('\n')
        for line in lines:
            text_object.textLine(line)
        
        c.drawText(text_object)
        c.save()

    async def update_status(self, doc_id: str, status: str, record_id: Optional[str] = None):
        """Updates the extraction status and optionally links the extraction record."""
        docs_coll = get_collection(self.collection_name)
        update_data = {"extraction_status": status}
        if record_id:
            update_data["extraction_record_id"] = record_id
            
        await docs_coll.update_one({"document_id": doc_id}, {"$set": update_data})
