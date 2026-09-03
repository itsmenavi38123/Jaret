from fastapi import APIRouter, Depends, HTTPException, status, Body, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.encoders import jsonable_encoder
from datetime import datetime, timedelta
from jose import jwt

from app.services.facebook_token_service import facebook_token_service
from app.services.facebook_service import facebook_service
from app.models.facebook.token import FacebookTokenCreate
from app.routes.auth.auth import get_current_user, check_demo_write_guard
from app.db import get_collection
from app.config import JWT_SECRET, JWT_ALGORITHM

router = APIRouter()

@router.get("/login")
async def login(current_user: dict = Depends(get_current_user)):
    """
    Returns the Facebook OAuth authorization URL. Mirrors the QuickBooks /login
    convention (app/routes/quickbooks/auth.py): state is a short-lived JWT
    carrying the user_id, decoded back out in /callback.
    """
    state_data = {
        "user_id": current_user["id"],
        "exp": datetime.utcnow() + timedelta(minutes=10)
    }
    state = jwt.encode(state_data, JWT_SECRET, algorithm=JWT_ALGORITHM)
    auth_url = facebook_service.get_authorization_url(state=state)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({
            "success": True,
            "data": {"auth_url": auth_url}
        })
    )

@router.get("/callback")
async def callback(request: Request):
    """
    Handles the Facebook OAuth redirect: exchanges the code for a long-lived
    user token, fetches the user's managed Pages, and persists a
    FacebookToken per page. Publishes business.profile_classified so the
    Storefront Agent picks up the newly connected photo source (on-new-imagery
    trigger).
    """
    code = request.query_params.get("code")
    state = request.query_params.get("state")

    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Authorization code not found in callback.")
    if not state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="State parameter not found in callback.")

    try:
        state_data = jwt.decode(state, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = state_data["user_id"]
    except jwt.JWTError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state parameter.")

    short_lived_token = await facebook_service.exchange_code_for_user_token(code)
    long_lived_token = await facebook_service.get_long_lived_user_token(short_lived_token)
    pages = await facebook_service.get_user_pages(long_lived_token)

    for page in pages:
        page_access_token = page.get("access_token")
        page_id = page.get("id")
        if not page_id or not page_access_token:
            continue
        await facebook_token_service.create_token(FacebookTokenCreate(
            user_id=user_id,
            page_id=page_id,
            page_name=page.get("name"),
            access_token=page_access_token,
        ))

    if pages:
        try:
            from app.services.internal_event_bus import internal_event_bus
            await internal_event_bus.publish(
                "business.profile_classified",
                {"business_id": user_id, "classified_at": datetime.utcnow().isoformat()}
            )
        except Exception as ex:
            print(f"Failed to publish profile_classified after Facebook connect: {ex}")

    return RedirectResponse(url="https://lightsignal.app/dashboard")

@router.get("/status")
async def get_status(current_user: dict = Depends(get_current_user)):
    """
    Returns whether the authenticated user has an active Facebook connection.
    """
    user_id = current_user["id"]
    tokens = await facebook_token_service.get_tokens_by_user(user_id)
    active_tokens = [token for token in tokens if token.is_active]

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({
            "success": True,
            "data": {
                "connected": len(active_tokens) > 0,
                "page_ids": [token.page_id for token in active_tokens]
            }
        })
    )

@router.post("/disconnect")
async def disconnect(current_user: dict = Depends(get_current_user)):
    """
    Disconnects Facebook for the authenticated user (deactivates and deletes token).
    """
    user_id = current_user["id"]
    success = await facebook_token_service.disconnect_and_delete_tokens_by_user(user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active Facebook connection found to disconnect."
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({
            "success": True,
            "message": "Facebook account disconnected and tokens permanently deleted."
        })
    )

@router.post("/learnings/{learning_id}/confirm")
async def confirm_learning(
    learning_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Confirms an AI storefront/location learning, graduating it to durable truth.
    """
    user_id = current_user["id"]
    collection = get_collection("customer_memory")
    
    memory = await collection.find_one({"_id": learning_id, "user_id": user_id})
    if not memory:
        raise HTTPException(status_code=404, detail="Learning not found.")
        
    await collection.update_one(
        {"_id": learning_id},
        {
            "$set": {
                "pinned": True,
                "under_review": False,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"success": True, "message": "Observation confirmed and pinned as durable learning."}
    )

@router.post("/learnings/{learning_id}/correct")
async def correct_learning(
    learning_id: str,
    correction: str = Body(..., embed=True),
    current_user: dict = Depends(get_current_user)
):
    """
    Corrects an AI storefront/location learning, updating the business profile and suppressing the old read.
    """
    check_demo_write_guard(current_user)
    user_id = current_user["id"]
    collection = get_collection("customer_memory")
    
    memory = await collection.find_one({"_id": learning_id, "user_id": user_id})
    if not memory:
        raise HTTPException(status_code=404, detail="Learning not found.")
        
    # 1. Update user's business profile
    profile_collection = get_collection("business_profiles")
    profile = await profile_collection.find_one({"user_id": user_id})
    if profile:
        onboarding_data = profile.get("onboarding_data", {})
        # Update the stated_positioning in the profile to user correction
        onboarding_data["stated_positioning"] = correction
        await profile_collection.update_one(
            {"_id": profile["_id"]},
            {"$set": {
                "onboarding_data": onboarding_data,
                "updated_at": datetime.utcnow()
            }}
        )
        
    # 2. Suppress the old read
    await collection.update_one(
        {"_id": learning_id},
        {
            "$set": {
                "outdated": True,
                "date_marked_outdated": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"success": True, "message": "Observation corrected and business profile updated."}
    )

@router.post("/learnings/{learning_id}/dismiss")
async def dismiss_learning(
    learning_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Dismisses an AI storefront/location learning, suppressing the read.
    """
    check_demo_write_guard(current_user)
    user_id = current_user["id"]
    collection = get_collection("customer_memory")
    
    memory = await collection.find_one({"_id": learning_id, "user_id": user_id})
    if not memory:
        raise HTTPException(status_code=404, detail="Learning not found.")
        
    # Suppress the read
    await collection.update_one(
        {"_id": learning_id},
        {
            "$set": {
                "outdated": True,
                "date_marked_outdated": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"success": True, "message": "Observation dismissed and suppressed."}
    )
