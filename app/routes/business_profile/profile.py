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
from app.services.mapbox_service import MapboxService
from app.services.business_profile_classifier_service import business_profile_classifier_service
from app.services.internal_event_bus import internal_event_bus

router = APIRouter(tags=["business_profile"])
mapbox_service = MapboxService()

@router.post("/onboarding")
async def create_or_update_onboarding(
    data: BusinessProfileCreate,
    current_user: dict = Depends(get_current_user)
):

    try:
        business_profiles = get_collection("business_profiles")
        opportunities_profiles = get_collection("opportunities_profiles")

        user_id = current_user["id"]

        onboarding_data = data.onboarding_data.copy()

        city = onboarding_data.get("city")
        state = onboarding_data.get("state")
        headquarters = onboarding_data.get("headquarters")

        address_parts = []

        if headquarters:
            address_parts.append(headquarters)

        if city:
            address_parts.append(city)

        if state:
            address_parts.append(state)

        full_address = ", ".join(address_parts)

        geo_data = {}

        try:
            if full_address:
                geo_data = await mapbox_service.geocode_address(full_address)

        except Exception as geo_error:
            print(f"Mapbox geocode failed: {geo_error}")

        onboarding_data["geo"] = {
            "business_address": full_address,
            "city": geo_data.get("city"),
            "state": geo_data.get("state"),
            "latitude": geo_data.get("lat"),
            "longitude": geo_data.get("lng"),
            "company_timezone": geo_data.get("timezone"),
            "geocode_confidence": geo_data.get("geocode_confidence"),
        }

        opportunities_profile = await opportunities_profiles.find_one(
            {"user_id": user_id}
        )

        classification_result = business_profile_classifier_service.classify_business(
            onboarding=onboarding_data,
            opportunities_profile=opportunities_profile,
        )

        existing = await business_profiles.find_one(
            {"user_id": user_id}
        )

        now = _now_utc()

        if existing:

            await business_profiles.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "onboarding_data": onboarding_data,
                        "business_classifications": classification_result["business_classifications"],
                        "business_tags": classification_result["business_tags"],
                        "proven_capabilities": classification_result["proven_capabilities"],
                        "updated_at": now
                    }
                }
            )

            await internal_event_bus.publish(
                "business.profile_classified",
                {
                    "business_id": user_id,
                    "business_classifications": classification_result["business_classifications"],
                    "business_tags": classification_result["business_tags"],
                    "proven_capabilities": classification_result["proven_capabilities"],
                    "classified_at": now.isoformat(),
                }
            )

            message = "Onboarding data updated successfully"

        else:

            profile = BusinessProfile(
                user_id=user_id,
                onboarding_data=onboarding_data,
                business_classifications=classification_result["business_classifications"],
                business_tags=classification_result["business_tags"],
                proven_capabilities=classification_result["proven_capabilities"],
                created_at=now,
                updated_at=now
            )

            await business_profiles.insert_one(
                profile.dict(by_alias=True)
            )

            await internal_event_bus.publish(
                "business.profile_classified",
                {
                    "business_id": user_id,
                    "business_classifications": classification_result["business_classifications"],
                    "business_tags": classification_result["business_tags"],
                    "proven_capabilities": classification_result["proven_capabilities"],
                    "classified_at": now.isoformat(),
                }
            )

            message = "Onboarding data created successfully"

        return JSONResponse(
            status_code=status.HTTP_200_OK if existing else status.HTTP_201_CREATED,
            content={
                "success": True,
                "message": message,
                "has_existing_data": bool(existing),
                "data": {
                    "user_id": user_id,
                    "onboarding_data": onboarding_data,
                    "business_classifications": classification_result["business_classifications"],
                    "business_tags": classification_result["business_tags"],
                    "proven_capabilities": classification_result["proven_capabilities"],
                }
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": str(e)
            }
        )

@router.put("/onboarding")
async def update_onboarding(
    data: BusinessProfileUpdate,
    current_user: dict = Depends(get_current_user)
):

    try:
        business_profiles = get_collection("business_profiles")
        opportunities_profiles = get_collection("opportunities_profiles")

        user_id = current_user["id"]

        existing = await business_profiles.find_one(
            {"user_id": user_id}
        )

        if not existing:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "success": False,
                    "error": "Onboarding data not found"
                }
            )

        onboarding_data = data.onboarding_data.copy()

        city = onboarding_data.get("city")
        state = onboarding_data.get("state")
        headquarters = onboarding_data.get("headquarters")

        address_parts = []

        if headquarters:
            address_parts.append(headquarters)

        if city:
            address_parts.append(city)

        if state:
            address_parts.append(state)

        full_address = ", ".join(address_parts)

        geo_data = {}

        try:
            if full_address:
                geo_data = await mapbox_service.geocode_address(full_address)

        except Exception as geo_error:
            print(f"Mapbox geocode failed: {geo_error}")

        onboarding_data["geo"] = {
            "business_address": full_address,
            "city": geo_data.get("city"),
            "state": geo_data.get("state"),
            "latitude": geo_data.get("lat"),
            "longitude": geo_data.get("lng"),
            "company_timezone": geo_data.get("timezone"),
            "geocode_confidence": geo_data.get("geocode_confidence"),
        }

        opportunities_profile = await opportunities_profiles.find_one(
            {"user_id": user_id}
        )

        classification_result = business_profile_classifier_service.classify_business(
            onboarding=onboarding_data,
            opportunities_profile=opportunities_profile,
        )

        now = _now_utc()

        await business_profiles.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "onboarding_data": onboarding_data,
                    "business_classifications": classification_result["business_classifications"],
                    "business_tags": classification_result["business_tags"],
                    "proven_capabilities": classification_result["proven_capabilities"],
                    "updated_at": now
                }
            }
        )

        await internal_event_bus.publish(
            "business.profile_classified",
            {
                "business_id": user_id,
                "business_classifications": classification_result["business_classifications"],
                "business_tags": classification_result["business_tags"],
                "proven_capabilities": classification_result["proven_capabilities"],
                "classified_at": now.isoformat(),
            }
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": "Onboarding data updated successfully",
                "data": {
                    "user_id": user_id,
                    "onboarding_data": onboarding_data,
                    "business_classifications": classification_result["business_classifications"],
                    "business_tags": classification_result["business_tags"],
                    "proven_capabilities": classification_result["proven_capabilities"],
                }
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": str(e)
            }
        )

@router.get("/onboarding")
async def get_onboarding(
    current_user: dict = Depends(get_current_user)
):

    try:
        business_profiles = get_collection("business_profiles")

        user_id = current_user["id"]

        profile = await business_profiles.find_one(
            {"user_id": user_id}
        )

        if not profile:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success": True,
                    "has_existing_data": False,
                    "data": None
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "has_existing_data": True,
                "data": {
                    "user_id": profile["user_id"],
                    "onboarding_data": profile["onboarding_data"],
                    "business_classifications": profile.get("business_classifications", []),
                    "business_tags": profile.get("business_tags", []),
                    "proven_capabilities": profile.get("proven_capabilities", []),
                    "created_at": profile["created_at"].isoformat() if profile.get("created_at") else None,
                    "updated_at": profile["updated_at"].isoformat() if profile.get("updated_at") else None
                }
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": str(e)
            }
        )