import base64
import json
import os
from typing import Any, Dict, Optional, List
from datetime import datetime
from app.services.document_store_service import DocumentStoreService
from app.services.claude_service import ClaudeService
from app.services.dia_orchestrator import DIAOrchestrator

class DIAService:
    def __init__(self, claude=None, store=None):
        self.store = store or DocumentStoreService()
        self.claude = claude or ClaudeService()
        self.orchestrator = DIAOrchestrator(store=self.store)

    async def process_document(self, document_id: str, customer_id: Optional[str] = None, location_id: Optional[str] = None, hint: Optional[str] = None, location_label: Optional[str] = None) -> Dict[str, Any]:
        meta = await self.store.get_metadata(document_id)
        if not meta:
            return {"status": "failed", "error": f"Document metadata not found for {document_id}"}

        # §4 Dual-Path Model Routing
        original_format = meta.get("original_format", "txt").lower()
        working_format = meta.get("working_format", "txt").lower()
        
        file_id = meta.get("working_file_id") or meta.get("original_file_id")
        if not file_id:
            return {"status": "failed", "error": f"No valid GridFS file ID found for {document_id}"}
        
        try:
            file_bytes = await self.store.get_document_bytes(file_id)

            # Determine Path: Vision vs Text
            # PDF, Image, converted Office docs -> Vision Path
            # .txt, .md, .xlsx, .xls, .csv -> Text Path
            if working_format in ("pdf", "jpeg", "jpg", "png"):
                path_type = "vision"
                print(f"DEBUG-DIA: Routing {document_id} to VISION path")
                content = self._build_vision_content(file_bytes, working_format, hint, location_label)
                completion_fn = self.claude.vision_json_completion
            elif original_format in ("txt", "md", "xlsx", "xls", "csv") or working_format in ("txt", "md", "xlsx", "xls", "csv"):
                path_type = "text"
                print(f"DEBUG-DIA: Routing {document_id} to TEXT path")
                content = await self._handle_text_path(file_bytes, original_format)
                completion_fn = self.claude.json_completion
            else:
                path_type = "text" # Default fallback
                content = await self._handle_text_path(file_bytes, working_format)
                completion_fn = self.claude.json_completion

            print(f"DEBUG-DIA: Calling Claude AI for {document_id} via {path_type} path...")
            extraction_result = await completion_fn(
                system_prompt=self._get_dia_prompt(meta, hint, location_label),
                user_content=content
            )
            
            extracted_data = json.loads(extraction_result) if isinstance(extraction_result, str) else extraction_result
            
            # Add routing metadata for provenance (§7)
            if isinstance(extracted_data, dict):
                extracted_data["path"] = path_type
                extracted_data["model"] = getattr(extraction_result, "model", self.claude.text_model if path_type == "text" else self.claude.vision_model)
                
            return extracted_data
            
        except Exception as e:
            print(f"DEBUG-DIA: Processing Error for {document_id}: {str(e)}")
            await self.store.update_status(document_id, "failed")
            return {"status": "failed", "error": str(e)}

    def _build_vision_content(self, file_bytes: bytes, fmt: str, hint: Optional[str] = None, location_label: Optional[str] = None) -> Any:
        """
        Build a proper multimodal content list: the actual document/image
        bytes as base64, plus an instruction text block. Sent to whichever
        model claude.vision_json_completion picks.
        No pre-OCR -- native vision reads scanned pages, tables, and layout
        directly, exactly per §4/§17 of the DIA spec.
        """
        encoded = base64.standard_b64encode(file_bytes).decode("utf-8")

        if fmt == "pdf":
            media_block = {
                "type": "document",
                "source": {"type": "base64", "media_type": "application/pdf", "data": encoded},
            }
        else:
            media_type = "image/jpeg" if fmt in ("jpeg", "jpg") else "image/png"
            media_block = {
                "type": "image",
                "source": {"type": "base64", "media_type": media_type, "data": encoded},
            }

        instruction = (
            f"Document type hint from owner: {hint or 'none'}. "
            f"Location: {location_label or 'none'}. "
            "Extract per your system prompt. Return only the JSON object."
        )

        return [media_block, {"type": "text", "text": instruction}]

    async def _handle_text_path(self, file_bytes: bytes, fmt: str) -> Any:
        import io
        # §5B Spreadsheet handling: Capture contents, do NOT analyze.
        if fmt in ("xlsx", "xls", "csv"):
            try:
                import pandas as pd
                df = pd.read_csv(io.BytesIO(file_bytes)) if fmt == "csv" else pd.read_excel(io.BytesIO(file_bytes))
                summary = f"Spreadsheet {fmt} content:\nColumns: {list(df.columns)}\nFirst 5 rows:\n{df.head().to_string()}"
                return f"SPREADSHEET-DATA (Capture Only):\n{summary}"
            except Exception as e:
                return f"Error parsing spreadsheet: {str(e)}"
        
        # Standard text/md
        try:
            return file_bytes.decode("utf-8")
        except Exception as e:
            return f"Error reading text file: {str(e)}"

    def _get_dia_prompt(self, meta: Dict, hint: Optional[str] = None, location_label: Optional[str] = None) -> str:
        hint_text = f"USER SPECIFIC EXTRACTION HINT: {hint}" if hint else "No specific hint provided."
        loc_text = f"TARGET LOCATION CONTEXT: {location_label}" if location_label else "No location label provided."
        
        prompt = (
            "You are the LightSignal Document Intelligence Agent (DIA). Your role is to convert unstructured documents into structured state. "
            "STRICT OUTPUT FORMAT: Return ONLY a JSON object with 'doc_type_detected', 'doc_type_confidence', 'extracted_address', 'written_fields', 'learnings', and 'not_found'.\n\n"
            "S-P-R-E-A-D-S-H-E-E-T RULE: If the document is a spreadsheet, capture what is in it (headers, totals, dates). "
            "Do NOT perform financial analysis, compute ratios, or build forecasts. Just describe the contents.\n\n"
            "EXTRACTION DISCIPLINE:\n"
            "1. Extract ONLY what is present. Never invent or fabricate values. Missing values must be returned in 'not_found'.\n"
            "2. Every field in 'written_fields' MUST have: target, value, source_ref (page/line/cell), snippet, confidence (high/medium/low), needs_review (boolean).\n"
            "3. If confidence is low, you must set needs_review=true.\n"
            "4. If a field is missing, put it in 'not_found'.\n\n"
            "SCHEMA:\n"
            "{\n"
            "  'doc_type_detected': 'document_type_like_invoice_or_bank_statement',\n"
            "  'doc_type_confidence': 'high' | 'medium' | 'low',\n"
            "  'extracted_address': 'extracted physical address string or null if not found',\n"
            "  'written_fields': [{'target': 'field_name', 'value': 'val', 'source_ref': 'ref', 'snippet': 'quote', 'confidence': 'high', 'needs_review': false}],\n"
            "  'learnings': [{'content': 'insight', 'source_ref': 'ref', 'confidence': 'high', 'tags': []}],\n"
            "  'not_found': ['field_name']\n"
            "}"
        )
        prompt += f"\n\nCONTEXT:\nFilename: {meta.get('original_filename')}\n{hint_text}\n{loc_text}\n\nBEGIN EXTRACTION:"
        return prompt