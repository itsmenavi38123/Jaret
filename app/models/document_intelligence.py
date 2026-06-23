from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class DocumentMetadata(BaseModel):
    document_id: str
    customer_id: str
    location_id: Optional[str] = None  # null or "business-wide"
    doc_type: Optional[str] = None     # Confirmed type after DIA process
    original_filename: str
    original_format: str
    working_format: str               # The format sent to the AI (e.g., pdf)
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    uploaded_by: str
    extraction_status: str = "pending" # pending -> reading -> done | needs_review | failed
    extraction_record_id: Optional[str] = None
    superseded_by: Optional[str] = None
    supersedes: Optional[str] = None
    original_file_id: Optional[Any] = None
    working_file_id: Optional[Any] = None
    outdated: bool = False
    owner_corrected: bool = False
    owner_correction: Optional[Dict[str, Any]] = None

class ExtractionField(BaseModel):
    target: str
    value: Any
    source_ref: str
    snippet: str
    confidence: str # high | medium | low
    needs_review: bool
    edited: bool = False
    edited_value: Optional[Any] = None
    edited_at: Optional[str] = None
    edited_by: Optional[str] = None

class LearningEntry(BaseModel):
    content: str
    source_ref: str
    confidence: str
    tags: List[str]

class ExtractionRecord(BaseModel):
    extraction_record_id: str
    document_id: str
    customer_id: str
    location_id: Optional[str] = None
    doc_type_detected: str
    doc_type_confidence: str
    path: str # vision | text
    model: str
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    supersedes: Optional[str] = None
    written_fields: List[ExtractionField]
    learnings: List[LearningEntry]
    not_found: List[str]
