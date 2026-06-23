from typing import Any, Dict, List, Optional
from datetime import datetime
import os
import re
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
            version_match = re.search(r'_v(\d+)', filename.lower())
            if version_match:
                current_ver = int(version_match.group(1))
                prev_ver = current_ver - 1
                prev_filename_pattern = re.sub(r'_v\d+', f'_v{prev_ver}', filename.lower())
                # Safe regex escaping
                escaped_pattern = re.escape(prev_filename_pattern)
                existing_doc = await docs_coll.find_one({
                    "customer_id": user_id,
                    "location_id": location_id,
                    "original_filename": {"$regex": f"^{escaped_pattern}"},
                    "document_id": {"$ne": doc_id},
                    "outdated": {"$ne": True}
                })

        # 2. Fallback to Most Recent Fuzzy Match
        if not existing_doc and filename:
            base, ext = os.path.splitext(filename.lower())
            base_name = re.sub(r'(_v\d+|-v\d+|_final|_new)$', '', base)
            if base_name:
                escaped_base = re.escape(base_name)
                existing_doc = await docs_coll.find_one(
                    filter={
                        "customer_id": user_id,
                        "location_id": location_id,
                        "original_filename": {"$regex": f"^{escaped_base}"},
                        "document_id": {"$ne": doc_id},
                        "outdated": {"$ne": True}
                    },
                    sort=[("upload_timestamp", -1)]
                )

        supersedes_id = None
        if existing_doc:
            supersedes_id = existing_doc["document_id"]
            await docs_coll.update_one({"document_id": supersedes_id}, {"$set": {"outdated": True, "superseded_by": doc_id}})
            await docs_coll.update_one({"document_id": doc_id}, {"$set": {"supersedes": supersedes_id}})
            await get_collection(self.extraction_collection_name).update_many({"document_id": supersedes_id}, {"$set": {"outdated": True}})

        # Write to business profile (supporting upsert if profile does not exist)
        profile_coll = get_collection(self.profile_collection_name)
        profile = await profile_coll.find_one({"user_id": user_id})
        
        onboarding_data = {}
        if profile and "onboarding_data" in profile:
            onboarding_data = profile["onboarding_data"]
            if not isinstance(onboarding_data, dict):
                onboarding_data = {}
                
        unset_fields = {}

        for field in extraction_data.get("written_fields", []):
            target = field.get("target")
            value = field.get("value")
            if not target or value is None: continue

            is_array = isinstance(target, str) and target.endswith("[]")
            base_field = target[:-2] if is_array else target
            
            if profile and base_field in profile:
                unset_fields[base_field] = ""

            fact_object = {
                "value": value,
                "source_ref": field.get("source_ref", "unknown"),
                "snippet": field.get("snippet", ""),
                "confidence": field.get("confidence", "medium"),
                "needs_review": field.get("needs_review", False),
                "doc_id": doc_id,
                "timestamp": datetime.utcnow().isoformat()
            }

            if is_array:
                existing_val = onboarding_data.get(base_field)
                if existing_val is not None:
                    if not isinstance(existing_val, list):
                        existing_val = [existing_val]
                    
                    new_list = []
                    for item in existing_val:
                        if isinstance(item, dict) and "value" in item and "source_ref" in item:
                            new_list.append(item)
                        else:
                            new_list.append({
                                "value": item,
                                "source_ref": "onboarding",
                                "snippet": "",
                                "confidence": "high",
                                "needs_review": False,
                                "doc_id": "onboarding",
                                "timestamp": datetime.utcnow().isoformat()
                            })
                    new_list.append(fact_object)
                    onboarding_data[base_field] = new_list
                else:
                    onboarding_data[base_field] = [fact_object]
            else:
                onboarding_data[base_field] = fact_object

        update_op = {"$set": {"onboarding_data": onboarding_data}}
        if profile and unset_fields:
            update_op["$unset"] = unset_fields
            
        await profile_coll.update_one({"user_id": user_id}, update_op, upsert=True)

        extraction_record = {
            "extraction_record_id": f"extr_{datetime.utcnow().timestamp()}",
            "document_id": doc_id,
            "customer_id": user_id,
            "location_id": location_id,
            "doc_type_detected": doc_type or "unknown",
            "doc_type_confidence": extraction_data.get("doc_type_confidence", "medium"),
            "path": extraction_data.get("path", "text"),
            "model": extraction_data.get("model", "unknown"),
            "extracted_at": datetime.utcnow(),
            "supersedes": supersedes_id,
            "written_fields": extraction_data.get("written_fields", []),
            "learnings": extraction_data.get("learnings", []),
            "not_found": extraction_data.get("not_found", []),
            "outdated": False
        }
        await get_collection(self.extraction_collection_name).insert_one(extraction_record)

        # Link extraction_record_id, doc_type, and location_id back to document metadata
        await docs_coll.update_one(
            {"document_id": doc_id},
            {"$set": {
                "extraction_record_id": extraction_record["extraction_record_id"],
                "doc_type": doc_type,
                "location_id": location_id
            }}
        )

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

    @classmethod
    async def migrate_profiles(cls) -> int:
        """
        Migrates all business profiles:
        1. Moves root-level DIA fields (dictionaries/lists with value/source_ref) into onboarding_data.
        2. Converts existing primitive values in onboarding_data for target DIA fields into the DIA fact object format.
        3. Removes legacy root-level DIA fields.
        """
        profile_coll = get_collection("business_profiles")
        cursor = profile_coll.find({})
        
        system_keys = {
            "_id", "user_id", "onboarding_data", "business_classifications", 
            "business_tags", "proven_capabilities", "created_at", "updated_at"
        }
        
        dia_fields = {
            "business_name", "legal_name", "ein", "address", "locations",
            "business_license_number", "lease_end_date", "insurance_policy_number",
            "contract_expiration_date"
        }
        
        updated_count = 0
        async for profile in cursor:
            onboarding_data = profile.get("onboarding_data", {})
            if not isinstance(onboarding_data, dict):
                onboarding_data = {}
                
            unset_fields = {}
            modified = False
            
            # Step 1: Detect root-level DIA fields and move to onboarding_data
            for k, v in list(profile.items()):
                if k in system_keys:
                    continue
                    
                is_dia = False
                if isinstance(v, dict) and "value" in v and "source_ref" in v:
                    is_dia = True
                elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict) and "value" in v[0] and "source_ref" in v[0]:
                    is_dia = True
                    
                if is_dia:
                    onboarding_data[k] = v
                    unset_fields[k] = ""
                    modified = True
            
            # Step 2: Convert primitive values inside onboarding_data for DIA fields into DIA fact objects
            for k, v in list(onboarding_data.items()):
                if k in dia_fields:
                    is_dia = False
                    if isinstance(v, dict) and "value" in v and "source_ref" in v:
                        is_dia = True
                    elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict) and "value" in v[0] and "source_ref" in v[0]:
                        is_dia = True
                        
                    if not is_dia and v is not None:
                        if isinstance(v, list):
                            new_list = []
                            for item in v:
                                if isinstance(item, dict) and "value" in item and "source_ref" in item:
                                    new_list.append(item)
                                else:
                                    new_list.append({
                                        "value": item,
                                        "source_ref": "onboarding",
                                        "snippet": "",
                                        "confidence": "high",
                                        "needs_review": False,
                                        "doc_id": "onboarding",
                                        "timestamp": datetime.utcnow().isoformat()
                                    })
                            onboarding_data[k] = new_list
                        else:
                            onboarding_data[k] = {
                                "value": v,
                                "source_ref": "onboarding",
                                "snippet": "",
                                "confidence": "high",
                                "needs_review": False,
                                "doc_id": "onboarding",
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        modified = True
                        
            if modified:
                update_op = {"$set": {"onboarding_data": onboarding_data}}
                if unset_fields:
                    update_op["$unset"] = unset_fields
                    
                await profile_coll.update_one({"_id": profile["_id"]}, update_op)
                updated_count += 1
                
        return updated_count
