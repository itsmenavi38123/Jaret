import os
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import Response
from typing import List, Optional, Any
from pydantic import BaseModel
from app.services.document_store_service import DocumentStoreService
from app.services.dia_agent_service import DIAService
from app.services.dia_orchestrator import DIAOrchestrator
from app.routes.auth.auth import get_current_user
from app.services.claude_service import ClaudeService
from app.services.customer_memory_service import CustomerMemoryService
from app.models.customer_memory import CustomerMemory
from app.db import get_collection
from datetime import datetime

class ReviewField(BaseModel):
    target: str
    edited_value: Any

class ReviewRequest(BaseModel):
    fields: List[ReviewField]

router = APIRouter(tags=["Documents"])

def get_dia_pipeline(current_user: dict = Depends(get_current_user)):
    store = DocumentStoreService()
    claude = ClaudeService()
    memory = CustomerMemoryService()
    agent = DIAService(claude, store)
    orchestrator = DIAOrchestrator(store, memory)
    return store, agent, orchestrator, current_user

@router.post("/upload")
async def upload_document(
    files: List[UploadFile] = File(...),
    hint: Optional[str] = Form(None),
    location_id: Optional[str] = Form(None),
    pipeline: tuple = Depends(get_dia_pipeline)
    ):
    store, agent, orchestrator, current_user = pipeline
    user_id = current_user["id"]
    
    results = []

    for file in files:
        from app.services.cost_guardrail_service import cost_guardrail_service
        allowed, reason = await cost_guardrail_service.check_and_reserve(user_id, "dia_upload")
        if not allowed:
            detail_msg = (
                "You've reached today's limit for this action. It resets at midnight."
                if reason == "surface_cap" else
                "You've reached today's usage limit for your account. It resets at midnight. Contact support if you need more."
            )
            raise HTTPException(status_code=429, detail=detail_msg)

        try:
            content = await file.read()
            doc_id = await store.save_uploaded_file(
                customer_id=user_id,
                file_content=content,
                filename=file.filename,
                uploaded_by=user_id,
                location_id=location_id
            )
            
            await store.update_status(doc_id, "reading")
            await store.convert_to_pdf(doc_id)
            
            print(f"DEBUG: Starting extraction for {doc_id}...")
            try:
                print(f"DEBUG: Calling agent.process_document with hint: {hint}")
                extraction_data = await agent.process_document(
                    document_id=doc_id, 
                    hint=hint, 
                    location_label=location_id
                )
                
                if isinstance(extraction_data, dict) and extraction_data.get("status") == "failed":
                    print(f"DEBUG: AI returned failure for {doc_id}: {extraction_data.get('error')}")
                    await store.update_status(doc_id, "failed")
                    results.append({"document_id": doc_id, "status": "failed", "error": extraction_data.get("error")})
                    await cost_guardrail_service.refund_reserve(user_id, "dia_upload")
                    continue
            except Exception as inner_exc:
                await cost_guardrail_service.refund_reserve(user_id, "dia_upload")
                raise inner_exc
        except Exception as e:
            # Re-raise HTTPExceptions (such as 429) directly, wrap others
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail=str(e))
            
            print(f"DEBUG: AI Extraction successful for {doc_id}")
            extraction_data["document_id"] = doc_id
            extraction_data["customer_id"] = user_id
            extraction_data["location_id"] = location_id
            extraction_data["original_filename"] = file.filename
            
            print(f"DEBUG: Distributing extraction for {doc_id} to profile and memory...")
            dist_res = await orchestrator.distribute_extraction(user_id, extraction_data)
            
            # Determine extraction status based on confidence / needs_review
            status = "done"
            if extraction_data.get("doc_type_confidence") == "low":
                status = "needs_review"
            else:
                for field in extraction_data.get("written_fields", []):
                    if field.get("needs_review"):
                        status = "needs_review"
                        break
            
            await store.update_status(doc_id, status, record_id=dist_res.get("record_id"))
            
            results.append({"document_id": doc_id, "status": "success", "filename": file.filename})
        except Exception as e:
            print(f"DEBUG: EXTRACTION ERROR for {doc_id}: {str(e)}")
            await store.update_status(doc_id, "failed")
            results.append({"document_id": doc_id, "status": "failed", "error": str(e)})
            
    return {"uploaded": results}

@router.get("/")
async def list_documents(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    store = DocumentStoreService()
    
    cursor = get_collection(store.collection_name).find({"customer_id": user_id}).sort("upload_timestamp", -1)
    docs = await cursor.to_list(length=100)
    
    summary_docs = []
    for doc in docs:
        summary_docs.append({
            "document_id": doc.get("document_id"),
            "filename": doc.get("original_filename"),
            "doc_type": doc.get("doc_type"),
            "extraction_status": doc.get("extraction_status"),
            "owner_corrected": doc.get("owner_corrected", False),
            "upload_timestamp": doc.get("upload_timestamp").isoformat() if isinstance(doc.get("upload_timestamp"), datetime) else doc.get("upload_timestamp"),
            "location_id": doc.get("location_id"),
            "outdated": doc.get("outdated", False)
        })
        
    return summary_docs

@router.get("/{document_id}/download")
async def download_document(
    document_id: str, 
    version: str = "working", 
    current_user: dict = Depends(get_current_user)
    ):
    if version not in ("working", "original"):
        raise HTTPException(status_code=400, detail="Invalid version parameter. Must be 'working' or 'original'.")
        
    user_id = current_user["id"]
    store = DocumentStoreService()
    
    meta = await store.get_metadata(document_id)
    if not meta or meta.get("customer_id") != user_id:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if version == "original":
        file_id = meta.get("original_file_id")
        fmt = meta.get("original_format")
        filename = meta.get("original_filename", "document")
    else:
        file_id = meta.get("working_file_id") or meta.get("original_file_id")
        fmt = meta.get("working_format") or meta.get("original_format") or "bin"
        filename = meta.get("original_filename", "document")
        # If serving a PDF, ensure the filename returned to client has a .pdf extension
        if fmt == "pdf" and not filename.lower().endswith(".pdf"):
            base, _ = os.path.splitext(filename)
            filename = f"{base}.pdf"
            
    if not file_id:
        raise HTTPException(status_code=404, detail="No file found for this document")
        
    try:
        content = await store.get_document_bytes(file_id)
            
        mime_mapping = {
            "pdf": "application/pdf",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "csv": "text/csv",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "xls": "application/vnd.ms-excel",
            "txt": "text/plain",
            "md": "text/markdown",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        }
        media_type = mime_mapping.get(fmt.lower(), "application/octet-stream")
        
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download error: {str(e)}")

@router.get("/{document_id}/review")
async def get_document_extraction(
    document_id: str, 
    pipeline: tuple = Depends(get_dia_pipeline)
):
    store, agent, orchestrator, current_user = pipeline
    user_id = current_user["id"]
    
    meta = await store.get_metadata(document_id)
    if not meta or meta.get("customer_id") != user_id:
        raise HTTPException(status_code=404, detail="Document not found")
        
    ext_coll = get_collection("extraction_records")
    ext_record = await ext_coll.find_one({"document_id": document_id})
    if not ext_record:
        raise HTTPException(status_code=404, detail="Extraction record not found")
        
    fields = []
    for field in ext_record.get("written_fields", []):
        target = field.get("target") or ""
        clean = target.replace("[]", "").replace("_", " ")
        acronyms = {"ein", "id", "ssn", "us", "dba"}
        display_name = " ".join(w.upper() if w.lower() in acronyms else w.capitalize() for w in clean.split())
        
        edited = field.get("edited", False)
        current_value = field.get("edited_value") if edited else field.get("value")
        
        fields.append({
            "key": target,
            "display_name": display_name,
            "current_value": current_value,
            "edited": edited
        })
        
    return {
        "document_id": document_id,
        "doc_type": meta.get("doc_type") or ext_record.get("doc_type_detected"),
        "extraction_status": meta.get("extraction_status"),
        "owner_corrected": meta.get("owner_corrected", False),
        "fields": fields
    }

@router.patch("/{document_id}/update")
async def review_fact(
    document_id: str, 
    review_data: ReviewRequest, 
    pipeline: tuple = Depends(get_dia_pipeline)
    ):
    store, agent, orchestrator, current_user = pipeline
    user_id = current_user["id"]
    memory = CustomerMemoryService()
    
    # 1. Update business profiles preserving provenance objects inside onboarding_data
    profile_coll = get_collection("business_profiles")
    profile = await profile_coll.find_one({"user_id": user_id})
    
    onboarding_data = {}
    if profile and "onboarding_data" in profile:
        onboarding_data = profile["onboarding_data"]
        if not isinstance(onboarding_data, dict):
            onboarding_data = {}
            
    unset_fields = {}
    
    # 2. Load extraction record
    ext_coll = get_collection("extraction_records")
    ext_record = await ext_coll.find_one({"document_id": document_id})
    
    doc_type_low_confidence = ext_record.get("doc_type_confidence") == "low" if ext_record else False
    written_fields = ext_record.get("written_fields", []) if ext_record else []
    
    corrections_made = []
    
    for review_field in review_data.fields:
        target_field = review_field.target
        corrected_value = review_field.edited_value
        
        correction = {
            "type": "owner_correction",
            "field": target_field,
            "old_value": "AI-extracted",
            "new_value": corrected_value,
            "doc_id": document_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        corrections_made.append(correction)
        
        is_array = isinstance(target_field, str) and target_field.endswith("[]")
        base_field = target_field[:-2] if is_array else target_field
        
        if profile and base_field in profile:
            unset_fields[base_field] = ""
            
        if is_array:
            existing_val = onboarding_data.get(base_field)
            if existing_val is not None:
                if not isinstance(existing_val, list):
                    existing_val = [existing_val]
                
                array = []
                for item in existing_val:
                    if isinstance(item, dict) and "value" in item and "source_ref" in item:
                        array.append(item)
                    else:
                        array.append({
                            "value": item,
                            "source_ref": "onboarding",
                            "snippet": "",
                            "confidence": "high",
                            "needs_review": False,
                            "doc_id": "onboarding",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        
                updated = False
                for item in array:
                    if isinstance(item, dict) and item.get("doc_id") == document_id:
                        item["value"] = corrected_value
                        item["owner_corrected"] = True
                        item["owner_correction"] = correction
                        updated = True
                        break
                if not updated:
                    new_item = {
                        "value": corrected_value,
                        "source_ref": "owner_correction",
                        "snippet": "",
                        "confidence": "high",
                        "needs_review": False,
                        "doc_id": document_id,
                        "timestamp": datetime.utcnow().isoformat(),
                        "owner_corrected": True,
                        "owner_correction": correction
                    }
                    array.append(new_item)
                onboarding_data[base_field] = array
            else:
                new_item = {
                    "value": corrected_value,
                    "source_ref": "owner_correction",
                    "snippet": "",
                    "confidence": "high",
                    "needs_review": False,
                    "doc_id": document_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "owner_corrected": True,
                    "owner_correction": correction
                }
                onboarding_data[base_field] = [new_item]
        else:
            existing_val = onboarding_data.get(base_field)
            if isinstance(existing_val, dict) and "value" in existing_val and "source_ref" in existing_val:
                existing_val["value"] = corrected_value
                existing_val["owner_corrected"] = True
                existing_val["owner_correction"] = correction
                onboarding_data[base_field] = existing_val
            else:
                new_item = {
                    "value": corrected_value,
                    "source_ref": "owner_correction",
                    "snippet": "",
                    "confidence": "high",
                    "needs_review": False,
                    "doc_id": document_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "owner_corrected": True,
                    "owner_correction": correction
                }
                onboarding_data[base_field] = new_item
                
        # Update extraction record field in memory
        for field in written_fields:
            if field.get("target") == target_field:
                field["edited"] = True
                field["edited_value"] = corrected_value
                field["edited_at"] = datetime.utcnow().isoformat()
                field["edited_by"] = user_id
                field["needs_review"] = False

    # Check if there are any remaining reviews
    has_remaining_reviews = False
    for field in written_fields:
        if field.get("needs_review") is True:
            has_remaining_reviews = True
            break
            
    # Save business profile changes
    update_op = {"$set": {"onboarding_data": onboarding_data}}
    if profile and unset_fields:
        update_op["$unset"] = unset_fields
    await profile_coll.update_one({"user_id": user_id}, update_op, upsert=True)
    
    # Save extraction record changes
    if ext_record:
        await ext_coll.update_one(
            {"document_id": document_id},
            {"$set": {"written_fields": written_fields}}
        )
        
    # Determine extraction status
    new_status = "needs_review" if (doc_type_low_confidence or has_remaining_reviews) else "done"
    
    # Update documents_metadata with owner review status
    docs_coll = get_collection("documents_metadata")
    await docs_coll.update_one(
        {"document_id": document_id},
        {"$set": {
            "owner_corrected": True,
            "owner_correction": corrections_made[0] if corrections_made else {},
            "extraction_status": new_status
        }}
    )
    
    # Log the audit trails in memory
    for corr in corrections_made:
        await memory.create_memory(
            CustomerMemory(
                user_id=user_id,
                content=f"User corrected {corr['field']} to {corr['new_value']}",
                path=f"/memories/customer_{user_id}/correction_{datetime.utcnow().timestamp()}.json",
                observation_type="owner_correction",
                metadata={"correction": corr}
            )
        )
        
    return {"status": "updated"}

@router.delete("/cleanup")
async def cleanup_documents(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    docs_coll = get_collection("documents_metadata")
    ext_coll = get_collection("extraction_records")
    
    from app.db import get_gridfs_bucket
    bucket = get_gridfs_bucket()
    
    cursor = docs_coll.find({"customer_id": user_id})
    doc_ids = []
    async for doc in cursor:
        doc_ids.append(doc["document_id"])
        # Delete GridFS files (deduplicating to avoid double deletion attempts)
        deleted_fids = set()
        for field in ("original_file_id", "working_file_id"):
            file_id = doc.get(field)
            if file_id and file_id not in deleted_fids:
                try:
                    await bucket.delete(file_id)
                    deleted_fids.add(file_id)
                except Exception as e:
                    print(f"Error deleting GridFS file {file_id}: {e}")
                    
    await docs_coll.delete_many({"customer_id": user_id})
    await ext_coll.delete_many({"customer_id": user_id})
    
    return {"status": "success", "deleted_count": len(doc_ids)}

@router.delete("/{document_id}")
async def delete_document(
    document_id: str, 
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    docs_coll = get_collection("documents_metadata")
    ext_coll = get_collection("extraction_records")
    
    doc = await docs_coll.find_one({"document_id": document_id, "customer_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    from app.db import get_gridfs_bucket
    bucket = get_gridfs_bucket()
    
    deleted_fids = set()
    for field in ("original_file_id", "working_file_id"):
        file_id = doc.get(field)
        if file_id and file_id not in deleted_fids:
            try:
                await bucket.delete(file_id)
                deleted_fids.add(file_id)
            except Exception as e:
                print(f"Error deleting GridFS file {file_id}: {e}")
                
    await docs_coll.delete_one({"document_id": document_id, "customer_id": user_id})
    await ext_coll.delete_many({"document_id": document_id, "customer_id": user_id})
    
    filename = doc.get("original_filename") or "document"
    return {"status": "success", "message": f"Document {filename} is deleted successfully"}

