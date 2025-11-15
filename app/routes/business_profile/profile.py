# backend/app/routes/business_profile/profile.py
import os
from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.db import get_collection
from app.routes.auth.auth import get_current_user
from app.models.business_profile import BusinessProfile, BusinessProfileCreate, BusinessProfileUpdate
from app.config import _now_utc

router = APIRouter(tags=["business_profile"])

@router.post("/onboarding")
async def create_or_update_onboarding(
    data: BusinessProfileCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create or update onboarding data for the current user.
    If onboarding data already exists, it will be updated.
    """
    try:
        business_profiles = get_collection("business_profiles")
        user_id = current_user["id"]

        # Check if onboarding data already exists for this user
        existing = await business_profiles.find_one({"user_id": user_id})

        now = _now_utc()
        if existing:
            # Update existing
            await business_profiles.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "onboarding_data": data.onboarding_data,
                        "updated_at": now
                    }
                }
            )
            message = "Onboarding data updated successfully"
        else:
            # Create new
            profile = BusinessProfile(
                user_id=user_id,
                onboarding_data=data.onboarding_data,
                created_at=now,
                updated_at=now
            )
            await business_profiles.insert_one(profile.dict(by_alias=True))
            message = "Onboarding data created successfully"

        return JSONResponse(
            status_code=status.HTTP_200_OK if existing else status.HTTP_201_CREATED,
            content={
                "success": True,
                "message": message,
                "data": {
                    "user_id": user_id,
                    "onboarding_data": data.onboarding_data
                }
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )

@router.put("/onboarding")
async def update_onboarding(
    data: BusinessProfileUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update existing onboarding data for the current user.
    If no onboarding data exists, returns 404.
    """
    try:
        business_profiles = get_collection("business_profiles")
        user_id = current_user["id"]

        # Check if onboarding data exists
        existing = await business_profiles.find_one({"user_id": user_id})
        if not existing:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"success": False, "error": "Onboarding data not found"}
            )

        # Update
        now = _now_utc()
        await business_profiles.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "onboarding_data": data.onboarding_data,
                    "updated_at": now
                }
            }
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": "Onboarding data updated successfully",
                "data": {
                    "user_id": user_id,
                    "onboarding_data": data.onboarding_data
                }
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )

@router.get("/onboarding")
async def get_onboarding(current_user: dict = Depends(get_current_user)):
    """
    Get onboarding data for the current user.
    """
    try:
        business_profiles = get_collection("business_profiles")
        user_id = current_user["id"]

        profile = await business_profiles.find_one({"user_id": user_id})
        if not profile:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"success": False, "error": "Onboarding data not found"}
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": {
                    "user_id": profile["user_id"],
                    "onboarding_data": profile["onboarding_data"],
                    "created_at": profile["created_at"].isoformat() if profile.get("created_at") else None,
                    "updated_at": profile["updated_at"].isoformat() if profile.get("updated_at") else None
                }
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )