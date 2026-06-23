from typing import Optional, Dict, Any
from datetime import datetime
from docx import Document as DocxDocument
from app.db import get_collection
from app.db import get_gridfs_bucket

class DocumentStoreService:
    def __init__(self):
        self.collection_name = "documents_metadata"

    async def get_metadata(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves metadata for a specific document."""
        docs_coll = get_collection(self.collection_name)
        return await docs_coll.find_one({"document_id": doc_id})

    async def save_uploaded_file(self, customer_id: str, file_content: bytes, filename: str, uploaded_by: str, location_id: Optional[str] = None) -> str:
        """Saves the original uploaded file to MongoDB GridFS."""
        import uuid
        doc_id = f"doc_{uuid.uuid4().hex}"
        bucket = get_gridfs_bucket()

        doc_format = filename.split('.')[-1].lower() if '.' in filename else 'txt'

        # Save to GridFS with improved metadata for traceability
        grid_in = bucket.open_upload_stream(
            filename,
            metadata={
                "document_id": doc_id,
                "customer_id": customer_id,
                "original_filename": filename,
                "original_format": doc_format
            }
        )
        await grid_in.write(file_content)
        await grid_in.close()
        file_id = grid_in._id

        docs_coll = get_collection(self.collection_name)
        await docs_coll.insert_one({
            "document_id": doc_id,
            "customer_id": customer_id,
            "location_id": location_id,
            "original_filename": filename,
            "original_format": doc_format,
            "working_format": doc_format,
            "upload_timestamp": datetime.utcnow(),
            "uploaded_by": uploaded_by,
            "extraction_status": "pending",
            "outdated": False,
            "original_file_id": file_id,
            "working_file_id": file_id
        })
        
        return doc_id

    async def convert_to_pdf(self, doc_id: str):
        """
        Implementation of Section 6A: Office Document Conversion.
        Converts office docs to PDF for the Vision Agent.
        Text and spreadsheets are NOT converted to ensure they follow the text path.
        """
        import io
        docs_coll = get_collection(self.collection_name)
        doc_meta = await docs_coll.find_one({"document_id": doc_id})
        if not doc_meta:
            return

        ext = doc_meta.get("original_format", "").lower()
        
        # Skip formats that don't need PDF conversion:
        # - text/data formats go to text path directly (including xls)
        # - PDF and images are natively supported by the vision path
        if ext in ["pdf", "txt", "md", "csv", "xlsx", "xls", "png", "jpg", "jpeg"]:
            return 

        original_file_id = doc_meta.get("original_file_id")
        if not original_file_id:
            return

        bucket = get_gridfs_bucket()
        try:
            grid_out = await bucket.open_download_stream(original_file_id)
            original_bytes = await grid_out.read()
        except Exception as e:
            print(f"Error downloading original file from GridFS for {doc_id}: {e}")
            return

        try:
            pdf_bytes = None
            if ext == "docx":
                doc = DocxDocument(io.BytesIO(original_bytes))
                full_text = [para.text for para in doc.paragraphs]
                text_content = "\n".join(full_text)
                pdf_bytes = self._text_to_pdf_bytes(text_content)
            
            if pdf_bytes is not None:
                orig_filename = doc_meta.get("original_filename", "document")
                pdf_filename = orig_filename.rsplit('.', 1)[0] + ".pdf" if '.' in orig_filename else orig_filename + ".pdf"
                
                # Save converted PDF with trace metadata
                grid_in = bucket.open_upload_stream(
                    pdf_filename,
                    metadata={
                        "document_id": doc_id,
                        "customer_id": doc_meta.get("customer_id"),
                        "original_filename": orig_filename,
                        "original_format": ext
                    }
                )
                await grid_in.write(pdf_bytes)
                await grid_in.close()
                working_file_id = grid_in._id
                
                await docs_coll.update_one(
                    {"document_id": doc_id},
                    {"$set": {
                        "working_format": "pdf", 
                        "working_file_id": working_file_id
                    }}
                )
        except Exception as e:
            print(f"Conversion error for {doc_id}: {e}")

    def _text_to_pdf_bytes(self, text: str) -> bytes:
        """Helper to convert raw text into a PDF file in-memory using reportlab."""
        import io
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        pdf_buffer = io.BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=letter)
        text_object = c.beginText(50, 750)
        text_object.setFont("Helvetica", 10)
        
        lines = text.split('\n')
        for line in lines:
            text_object.textLine(line)
        
        c.drawText(text_object)
        c.save()
        return pdf_buffer.getvalue()

    async def get_document_bytes(self, file_id) -> bytes:
        """Retrieves the file bytes directly from MongoDB GridFS."""
        from bson.objectid import ObjectId
        if isinstance(file_id, str):
            file_id = ObjectId(file_id)
        bucket = get_gridfs_bucket()
        grid_out = await bucket.open_download_stream(file_id)
        return await grid_out.read()

    async def update_status(self, doc_id: str, status: str, record_id: Optional[str] = None):
        """Updates the extraction status and optionally links the extraction record."""
        docs_coll = get_collection(self.collection_name)
        update_data = {"extraction_status": status}
        if record_id:
            update_data["extraction_record_id"] = record_id
            
        await docs_coll.update_one({"document_id": doc_id}, {"$set": update_data})
