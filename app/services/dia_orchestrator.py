from typing import Any, Dict, List, Optional
from datetime import datetime
from app.db import get_collection
from app.models.customer_memory import CustomerMemory
from app.services.document_store_service import DocumentStoreService

class DIAOrchestrator:
    def __init__(self, store: DocumentStoreService, memory=None):
        self.store = store
        self.memory = memory
        self.profile_collection_name = "business_profiles"
        self.extraction_collection_name = "extraction_records"

    async def _resolve_location(self, user_id: str, extracted_address: Optional[str], provided_location_id: Optional[str]) -> str:
        if not extracted_address:
            return provided_location_id or "unassigned"

        profile_coll = get_collection(self.profile_collection_name)
        profile = await profile_coll.find_one({"user_id": user_id})
        
        if not profile:
            return provided_location_id or "unassigned"

        locations = profile.get("locations", [])
        normalized_extracted = extracted_address.lower().strip()
        
        for loc in locations:
            loc_val = loc.get("address", loc) if isinstance(loc, dict) else loc
            if isinstance(loc_val, str) and (normalized_extracted in loc_val.lower() or loc_val.lower() in normalized_extracted):
                return loc.get("location_id", loc) if isinstance(loc, dict) else loc

        return provided_location_id or "unassigned"

    async def distribute_extraction(self, user_id: str, extraction_data: Dict[str, Any]):
        doc_id = extraction_data.get("document_id")
        doc_type = extraction_data.get("doc_type_detected")
        provided_location_id = extraction_data.get("location_id")
        filename = extraction_data.get("original_filename", "")
        extracted_address = extraction_data.get("extracted_address")

        location_id = await self._resolve_location(user_id, extracted_address, provided_location_id)
        extraction_data["location_id"] = location_id

        docs_coll = get_collection("documents_metadata")
        existing_doc = None
        
        # 1. Try Exact Version Match (e.g., v2 looks for v1)
        if filename:
            import re
            version_match = re.search(r'_v(\d+)', filename.lower())
            if version_match:
                current_ver = int(version_match.group(1))
                prev_ver = current_ver - 1
                # Look for a file with the same name but version - 1
                prev_filename_pattern = re.sub(r'_v\d+', f'_v{prev_ver}', filename.lower())
                existing_doc = await docs_coll.find_one({
                    "customer_id": user_id,
                    "location_id": location_id,
                    "original_filename": {"$regex": f"^{prev_filename_pattern}"},
                    "document_id": {"$ne": doc_id},
                    "outdated": {"$ne": True}
                })

        # 2. Fallback to Most Recent Fuzzy Match
        if not existing_doc and filename:
            import re
            base_name = re.sub(r'(_v\d+|-v\d+|_final|_new)$', '', filename.lower())
            if base_name:
                existing_doc = await docs_coll.find_one(
                    filter={
                        "customer_id": user_id,
                        "location_id": location_id,
                        "original_filename": {"$regex": f"^{base_name}"},
                        "document_id": {"$ne": doc_id},
                        "outdated": {"$ne": True}
                    },
                    sort=[("upload_timestamp", -1)]
                )

        if existing_doc:
            old_doc_id = existing_doc["document_id"]
            await docs_coll.update_one({"document_id": old_doc_id}, {"$set": {"outdated": True, "superseded_by": doc_id}})
            await docs_coll.update_one({"document_id": doc_id}, {"$set": {"supersedes": old_doc_id}})
            await get_collection(self.extraction_collection_name).update_many({"document_id": old_doc_id}, {"$set": {"outdated": True}})

        profile_coll = get_collection(self.profile_collection_name)
        for field in extraction_data.get("written_fields", []):
            target = field.get("target")
            value = field.get("value")
            if not target or value is None: continue

            # Construct a professional provenance object for every fact
            fact_object = {
                "value": value,
                "source_ref": field.get("source_ref", "unknown"),
                "snippet": field.get("snippet", ""),
                "confidence": field.get("confidence", "medium"),
                "needs_review": field.get("needs_review", False),
                "doc_id": doc_id,
                "timestamp": datetime.utcnow().isoformat()
            }

            if isinstance(target, str) and target.endswith("[]"):
                # Store as an array of provenance objects
                await profile_coll.update_one({"user_id": user_id}, {"$push": {target[:-2]: fact_object}})
            else:
                # Store as a single provenance object (overwriting previous version)
                await profile_coll.update_one({"user_id": user_id}, {"$set": {target: fact_object}})


        extraction_record = {
            "extraction_record_id": f"extr_{datetime.utcnow().timestamp()}",
            "document_id": doc_id,
            "customer_id": user_id,
            "location_id": location_id,
            "doc_type_detected": doc_type,
            "extracted_at": datetime.utcnow(),
            "written_fields": extraction_data.get("written_fields", []),
            "learnings": extraction_data.get("learnings", []),
            "not_found": extraction_data.get("not_found", []),
            "outdated": False
        }
        await get_collection(self.extraction_collection_name).insert_one(extraction_record)

        if self.memory and "learnings" in extraction_data:
            for learning in extraction_data["learnings"]:
                content = learning.get("content")
                if content:
                    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                    memory_path = f"/memories/customer_{user_id}/{timestamp}-dia-{doc_id}.json"
                    memory_entry = CustomerMemory(
                        user_id=user_id,
                        content=content,
                        path=memory_path,
                        observation_type="document_derived",
                        metadata={
                            "source_doc": doc_id,
                            "confidence": learning.get("confidence"),
                            "tags": learning.get("tags", []),
                        }
                    )
                    await self.memory.create_memory(memory_entry)

        return {"status": "success", "record_id": extraction_record["extraction_record_id"]}
