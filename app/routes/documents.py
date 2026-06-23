from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from typing import List, Optional, Any
from app.services.document_store_service import DocumentStoreService
from app.services.dia_agent_service import DIAService
from app.services.dia_orchestrator import DIAOrchestrator
from app.routes.auth.auth import get_current_user
from app.services.claude_service import ClaudeService
from app.services.customer_memory_service import CustomerMemoryService
from app.db import get_collection
from datetime import datetime

router = APIRouter(prefix="/documents", tags=["Documents"])

def get_dia_pipeline(user=Depends(get_current_user)):
    store = DocumentStoreService()
    claude = ClaudeService()
    memory = CustomerMemoryService()
    agent = DIAService(claude, store)
    orchestrator = DIAOrchestrator(store, memory)
    return store, agent, orchestrator, user

@router.post("/upload")
async def upload_document(
    files: List[UploadFile] = File(...),
    hint: Optional[str] = Form(None),
    location_id: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    
    store = DocumentStoreService()
    claude = ClaudeService()
    memory = CustomerMemoryService()
    agent = DIAService(claude, store)
    orchestrator = DIAOrchestrator(store, memory)
    
    results = []

    for file in files:
        content = await file.read()
        doc_id, path = await store.save_uploaded_file(
            customer_id=user_id,
            file_content=content,
            filename=file.filename,
            uploaded_by=user_id,
            location_id=location_id
        )
        
        await store.convert_to_pdf(doc_id, path)
        
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
                continue
            
            print(f"DEBUG: AI Extraction successful for {doc_id}")
            extraction_data["document_id"] = doc_id
            extraction_data["customer_id"] = user_id
            extraction_data["location_id"] = location_id
            extraction_data["original_filename"] = file.filename
            
            print(f"DEBUG: Distributing extraction for {doc_id} to profile and memory...")
            await orchestrator.distribute_extraction(user_id, extraction_data)
            await store.update_status(doc_id, "done")
            
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
    
    for doc in docs:
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
            
    return docs

@router.patch("/{document_id}/review")
async def review_fact(
    document_id: str, 
    target_field: str, 
    corrected_value: Any, 
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    store = DocumentStoreService()
    memory = CustomerMemoryService()
    orchestrator = DIAOrchestrator(store, memory)
    
    await get_collection("business_profiles").update_one(
        {"user_id": user_id},
        {"$set": {target_field: corrected_value}}
    )
    
    correction = {
        "type": "owner_correction",
        "field": target_field,
        "old_value": "AI-extracted",
        "new_value": corrected_value,
        "doc_id": document_id
    }
    await memory.create_memory(
        CustomerMemory(
            user_id=user_id,
            content=f"User corrected {target_field} to {corrected_value}",
            path=f"/memories/customer_{user_id}/correction_{datetime.utcnow().timestamp()}.json",
            observation_type="owner_correction",
            metadata={"correction": correction}
        )
    )
    
    return {"status": "updated"}

@router.delete("/cleanup")
async def cleanup_documents(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    docs_coll = get_collection("documents_metadata")
    ext_coll = get_collection("extraction_records")
    
    cursor = docs_coll.find({"customer_id": user_id})
    doc_ids = []
    async for doc in cursor:
        doc_ids.append(doc["document_id"])
    
    await docs_coll.delete_many({"customer_id": user_id})
    await ext_coll.delete_many({"customer_id": user_id})
    
    return {"status": "success", "deleted_count": len(doc_ids)}
