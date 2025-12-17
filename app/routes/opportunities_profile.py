# backend/app/routes/opportunities_profile.py
import os
from datetime import datetime, timezone
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.db import get_collection
from app.routes.auth.auth import get_current_user
from app.models.opportunities_profile import OpportunitiesProfile, OpportunitiesProfileCreate, OpportunitiesProfileUpdate
from app.config import _now_utc

router = APIRouter(tags=["opportunities_profile"])

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_opportunities_profile(
    data: OpportunitiesProfileCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create opportunities profile for the current user.
    """
    try:
        opportunities_profiles = get_collection("opportunities_profiles")
        user_id = current_user["id"]

        # Check if profile already exists for this user
        existing = await opportunities_profiles.find_one({"user_id": user_id})
        if existing:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "error": "Opportunities profile already exists for this user"}
            )

        now = _now_utc()
        profile = OpportunitiesProfile(
            user_id=user_id,
            business_type=data.business_type,
            operating_region=data.operating_region,
            preferred_opportunity_types=data.preferred_opportunity_types,
            radius=data.radius,
            max_budget=data.max_budget,
            travel_range=data.travel_range,
            staffing_capacity=data.staffing_capacity,
            risk_appetite=data.risk_appetite,
            created_at=now,
            updated_at=now
        )
        await opportunities_profiles.insert_one(profile.dict(by_alias=True))

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "success": True,
                "message": "Opportunities profile created successfully",
                "data": {
                    "user_id": profile.user_id,
                    "business_type": profile.business_type,
                    "operating_region": profile.operating_region,
                    "preferred_opportunity_types": profile.preferred_opportunity_types,
                    "radius": profile.radius,
                    "max_budget": profile.max_budget,
                    "travel_range": profile.travel_range,
                    "staffing_capacity": profile.staffing_capacity,
                    "risk_appetite": profile.risk_appetite,
                    "created_at": profile.created_at.isoformat(),
                    "updated_at": profile.updated_at.isoformat()
                }
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )

@router.get("/", status_code=status.HTTP_200_OK)
async def get_opportunities_profile(current_user: dict = Depends(get_current_user)):
    """
    Get opportunities profile for the current user.
    """
    try:
        opportunities_profiles = get_collection("opportunities_profiles")
        user_id = current_user["id"]

        profile = await opportunities_profiles.find_one({"user_id": user_id})
        if not profile:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"success": False, "error": "Opportunities profile not found", "data": None}
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": {
                    "user_id": profile["user_id"],
                    "business_type": profile["business_type"],
                    "operating_region": profile["operating_region"],
                    "preferred_opportunity_types": profile["preferred_opportunity_types"],
                    "radius": profile["radius"],
                    "max_budget": profile["max_budget"],
                    "travel_range": profile["travel_range"],
                    "staffing_capacity": profile["staffing_capacity"],
                    "risk_appetite": profile["risk_appetite"],
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

@router.put("/",status_code=status.HTTP_200_OK)
async def update_opportunities_profile(
    data: OpportunitiesProfileUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update opportunities profile for the current user.
    """
    try:
        opportunities_profiles = get_collection("opportunities_profiles")
        user_id = current_user["id"]

        # Check if profile exists
        existing = await opportunities_profiles.find_one({"user_id": user_id})

        # Custom Upsert Logic
        if not existing:
            # Create new if not exists (Upsert)
            now = _now_utc()
            
            new_profile = OpportunitiesProfile(
                user_id=user_id,
                business_type=data.business_type or "Unknown",
                operating_region=data.operating_region or "Unknown",
                preferred_opportunity_types=data.preferred_opportunity_types or [],
                radius=data.radius or 50,
                max_budget=data.max_budget or 0.0,
                travel_range=data.travel_range or "Local",
                staffing_capacity=data.staffing_capacity or 1,
                risk_appetite=data.risk_appetite or "medium",
                auto_sync=data.auto_sync if data.auto_sync is not None else True,
                indoor_only=data.indoor_only if data.indoor_only is not None else False,
                created_at=now,
                updated_at=now
            )
            await opportunities_profiles.insert_one(new_profile.dict(by_alias=True))
            
            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={
                    "success": True, 
                    "message": "Opportunities profile created (upsert)",
                    "data": jsonable_encoder(new_profile)
                }
            )

        # Update existing
        update_data = {}
        if data.business_type is not None: update_data["business_type"] = data.business_type
        if data.operating_region is not None: update_data["operating_region"] = data.operating_region
        if data.preferred_opportunity_types is not None: update_data["preferred_opportunity_types"] = data.preferred_opportunity_types
        if data.radius is not None: update_data["radius"] = data.radius
        if data.max_budget is not None: update_data["max_budget"] = data.max_budget
        if data.travel_range is not None: update_data["travel_range"] = data.travel_range
        if data.staffing_capacity is not None: update_data["staffing_capacity"] = data.staffing_capacity
        if data.risk_appetite is not None: update_data["risk_appetite"] = data.risk_appetite
        if data.auto_sync is not None: update_data["auto_sync"] = data.auto_sync
        if data.indoor_only is not None: update_data["indoor_only"] = data.indoor_only

        now = _now_utc()
        update_data["updated_at"] = now

        await opportunities_profiles.update_one(
            {"user_id": user_id},
            {"$set": update_data}
        )

        # Fetch updated profile
        updated_profile = await opportunities_profiles.find_one({"user_id": user_id})

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": "Opportunities profile updated successfully",
                "data": {
                    "user_id": updated_profile["user_id"],
                    "business_type": updated_profile["business_type"],
                    "operating_region": updated_profile["operating_region"],
                    "preferred_opportunity_types": updated_profile["preferred_opportunity_types"],
                    "radius": updated_profile["radius"],
                    "max_budget": updated_profile["max_budget"],
                    "travel_range": updated_profile["travel_range"],
                    "staffing_capacity": updated_profile["staffing_capacity"],
                    "risk_appetite": updated_profile["risk_appetite"],
                    "created_at": updated_profile["created_at"].isoformat() if updated_profile.get("created_at") else None,
                    "updated_at": updated_profile["updated_at"].isoformat() if updated_profile.get("updated_at") else None
                }
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )