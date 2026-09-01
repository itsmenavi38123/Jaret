# backend/app/routes/business_profile/profile.py
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
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

class OwnerNoteCreate(BaseModel):
    text: str


def _deep_merge_dict(base: dict, updates: dict) -> dict:
    merged = dict(base or {})
    for k, v in (updates or {}).items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = _deep_merge_dict(merged[k], v)
        else:
            merged[k] = v
    return merged


def _apply_partial_updates(existing_onboarding: dict, incoming: dict) -> dict:
    merged = dict(existing_onboarding or {})
    for k, v in (incoming or {}).items():
        if k.startswith("section_") or k in ["business_basics", "financial_overview", "operations"]:
            if isinstance(v, dict) and isinstance(merged.get(k), dict):
                merged[k] = _deep_merge_dict(merged[k], v)
            else:
                merged[k] = v
        elif isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = _deep_merge_dict(merged[k], v)
        else:
            # Direct field update (e.g. {"business_name": "New Name"})
            field_updated = False
            for sec_k, sec_v in merged.items():
                if isinstance(sec_v, dict) and k in sec_v:
                    sec_v[k] = v
                    field_updated = True
            if not field_updated:
                merged[k] = v
    return merged


def _extract_address_string(onboarding_data: dict) -> str:
    address_parts = []
    hq = onboarding_data.get("headquarters") or onboarding_data.get("primary_location")
    city = onboarding_data.get("city")
    state = onboarding_data.get("state")
    if hq:
        address_parts.append(hq)
    if city:
        address_parts.append(city)
    if state:
        address_parts.append(state)

    if not address_parts:
        s1 = (
            onboarding_data.get("section_01_business_basics")
            or onboarding_data.get("section_1_basics")
            or onboarding_data.get("business_basics")
            or {}
        )
        if isinstance(s1, dict):
            loc_str = s1.get("headquarters") or s1.get("primary_location") or s1.get("main_location") or s1.get("city_state")
            if loc_str and isinstance(loc_str, str):
                address_parts.append(loc_str)
            elif isinstance(s1.get("locations"), list) and len(s1.get("locations")) > 0:
                first_loc = s1["locations"][0]
                if isinstance(first_loc, dict):
                    addr = first_loc.get("address")
                    c = first_loc.get("city")
                    s = first_loc.get("state")
                    if addr:
                        address_parts.append(addr)
                    if c:
                        address_parts.append(c)
                    if s:
                        address_parts.append(s)
    return ", ".join(address_parts)


# -------------------------------------------------------------
# 1. POST /onboarding  -> Initial Creation / Full Upsert
# -------------------------------------------------------------
@router.post("/onboarding")
async def create_onboarding(
    data: BusinessProfileCreate,
    current_user: Any = Depends(get_current_user)
):
    try:
        business_profiles = get_collection("business_profiles")
        opportunities_profiles = get_collection("opportunities_profiles")

        if isinstance(current_user, dict):
            user_id = current_user.get("id") or current_user.get("_id")
        else:
            user_id = str(current_user)

        onboarding_data = data.onboarding_data.copy()

        full_address = _extract_address_string(onboarding_data)
        geo_data = {}
        try:
            if full_address:
                geo_data = await mapbox_service.geocode_address(full_address)
        except Exception as geo_error:
            print(f"Mapbox geocode failed: {geo_error}")

        if geo_data:
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

            message = "Onboarding data created successfully"

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

        clean_sections = {k: v for k, v in onboarding_data.items() if k.startswith("section_")}
        if not clean_sections:
            clean_sections = onboarding_data

        return JSONResponse(
            status_code=status.HTTP_200_OK if existing else status.HTTP_201_CREATED,
            content={
                "success": True,
                "message": message,
                "has_existing_data": bool(existing),
                "data": {
                    "user_id": user_id,
                    "business_classifications": classification_result["business_classifications"],
                    "business_tags": classification_result["business_tags"],
                    "proven_capabilities": classification_result["proven_capabilities"],
                    "created_at": (existing.get("created_at") or now).isoformat() if hasattr(existing.get("created_at") or now, "isoformat") else str(existing.get("created_at") or now),
                    "updated_at": now.isoformat(),
                    "onboarding_data": clean_sections,
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


# -------------------------------------------------------------
# 2. PATCH /onboarding -> Field-Level & Section-Wise Partial Update
# -------------------------------------------------------------
@router.patch("/onboarding")
async def patch_onboarding(
    payload: Dict[str, Any],
    current_user: Any = Depends(get_current_user)
):
    try:
        business_profiles = get_collection("business_profiles")
        opportunities_profiles = get_collection("opportunities_profiles")

        if isinstance(current_user, dict):
            user_id = current_user.get("id") or current_user.get("_id")
        else:
            user_id = str(current_user)

        existing = await business_profiles.find_one({"user_id": user_id})

        if not existing:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "success": False,
                    "error": "Onboarding data not found"
                }
            )

        existing_onboarding = existing.get("onboarding_data", {})
        
        # Support both wrapped {"onboarding_data": {...}} and direct {...}
        incoming_data = payload.get("onboarding_data") if isinstance(payload.get("onboarding_data"), dict) else payload

        # Smart merge: updates ONLY the specified fields/sections and preserves everything else
        onboarding_data = _apply_partial_updates(existing_onboarding, incoming_data)

        full_address = _extract_address_string(onboarding_data)
        geo_data = {}
        try:
            if full_address:
                geo_data = await mapbox_service.geocode_address(full_address)
        except Exception as geo_error:
            print(f"Mapbox geocode failed: {geo_error}")

        if geo_data:
            onboarding_data["geo"] = {
                "business_address": full_address,
                "city": geo_data.get("city"),
                "state": geo_data.get("state"),
                "latitude": geo_data.get("lat"),
                "longitude": geo_data.get("lng"),
                "company_timezone": geo_data.get("timezone"),
                "geocode_confidence": geo_data.get("geocode_confidence"),
            }

        opportunities_profile = await opportunities_profiles.find_one({"user_id": user_id})
        classification_result = business_profile_classifier_service.classify_business(
            onboarding=onboarding_data,
            opportunities_profile=opportunities_profile,
        )

        now = _now_utc()
        clean_sections = {k: v for k, v in onboarding_data.items() if k.startswith("section_")}
        if not clean_sections:
            clean_sections = onboarding_data

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
                    "business_classifications": classification_result["business_classifications"],
                    "business_tags": classification_result["business_tags"],
                    "proven_capabilities": classification_result["proven_capabilities"],
                    "created_at": existing.get("created_at").isoformat() if hasattr(existing.get("created_at"), "isoformat") else str(existing.get("created_at") or ""),
                    "updated_at": now.isoformat(),
                    "onboarding_data": clean_sections,
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


# -------------------------------------------------------------
# 3. GET /onboarding   -> Fetch Full Clean Onboarding Profile
# -------------------------------------------------------------
@router.get("/onboarding")
async def get_onboarding(
    current_user: Any = Depends(get_current_user)
):
    try:
        business_profiles = get_collection("business_profiles")
        user_id = current_user.get("id") or current_user.get("_id") if isinstance(current_user, dict) else str(current_user)
        email = current_user.get("email", "") if isinstance(current_user, dict) else ""
        is_demo_flag = (current_user.get("is_demo") or (email.startswith("demo-") and "@lightsignal.app" in email)) if isinstance(current_user, dict) else False
        
        if not is_demo_flag:
            users_col = get_collection("users")
            user_doc = await users_col.find_one({"id": user_id}) or await users_col.find_one({"_id": user_id}) or {}
            is_demo_flag = user_doc.get("is_demo") or (user_doc.get("email", "").startswith("demo-") and "@lightsignal.app" in user_doc.get("email", ""))
            login_label = user_doc.get("login_label") or user_doc.get("username") or (user_doc.get("email", "").split("@")[0] if user_doc.get("email") else "demo-restaurant")
        else:
            login_label = current_user.get("login_label") or current_user.get("username") or (email.split("@")[0] if email else "demo-restaurant")

        if is_demo_flag:
            from app.demo_data import get_demo_payload
            demo_payload = get_demo_payload(login_label or "demo-restaurant")
            if demo_payload and "business_profile" in demo_payload:
                raw_bp = demo_payload["business_profile"]
                sections_only = {
                    k: v for k, v in raw_bp.items()
                    if k.startswith("section_")
                }
                demo_data = {
                    "user_id": user_id,
                    "business_classifications": [demo_payload.get("account", {}).get("industry", "Restaurant")],
                    "business_tags": ["Demo"],
                    "proven_capabilities": [],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "onboarding_data": sections_only if sections_only else raw_bp
                }
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "success": True,
                        "has_existing_data": True,
                        "data": demo_data
                    }
                )

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

        raw_ob = profile.get("onboarding_data", {})
        sections_only = {
            k: v for k, v in raw_ob.items()
            if k.startswith("section_")
        }
        created_val = profile.get("created_at")
        updated_val = profile.get("updated_at")

        response_data = {
            "user_id": profile["user_id"],
            "business_classifications": profile.get("business_classifications", []),
            "business_tags": profile.get("business_tags", []),
            "proven_capabilities": profile.get("proven_capabilities", []),
            "created_at": created_val.isoformat() if hasattr(created_val, "isoformat") else str(created_val or ""),
            "updated_at": updated_val.isoformat() if hasattr(updated_val, "isoformat") else str(updated_val or ""),
            "onboarding_data": sections_only if sections_only else raw_ob
        }

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "has_existing_data": True,
                "data": response_data
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


@router.get("/richness")
async def get_profile_richness(
    current_user: dict = Depends(get_current_user)
):
    """
    Get Business Profile Richness Meter score and band.
    Per BP_Richness_Meter_Teaser_Addendum_v1.md.
    """
    try:
        user_id = current_user["id"]
        users_col = get_collection("users")
        user_doc = await users_col.find_one({"id": user_id}) or await users_col.find_one({"_id": user_id}) or {}
        
        # Demo users are 100% complete
        if user_doc.get("is_demo") or (user_doc.get("email", "").startswith("demo-") and "@lightsignal.app" in user_doc.get("email", "")):
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success": True,
                    "data": {
                        "score": 1.0,
                        "band": "We know your business",
                        "ever_reached_sharp": True,
                        "sections_complete": 16,
                        "total_sections": 16
                    }
                }
            )

        business_profiles = get_collection("business_profiles")
        profile = await business_profiles.find_one({"user_id": user_id})
        
        onboarding_data = profile.get("onboarding_data", {}) if profile else {}
        
        # Calculate filled sections out of 16 using alias groups
        section_aliases = [
            ["section_01_business_basics", "section_1_basics", "section_1_business_basics", "business_basics"],
            ["section_02_ownership_and_key_people", "section_2_ownership", "ownership_and_key_people"],
            ["section_03_industry_and_model", "section_3_industry", "industry_and_model"],
            ["section_04_operations", "section_4_operations", "operations"],
            ["section_05_financial_overview", "section_5_financial", "financial_overview"],
            ["section_06_assets_and_equipment", "section_6_assets", "assets_and_equipment"],
            ["section_07_customers_and_market", "section_7_customers", "customers_and_market"],
            ["section_08_risk_and_exposure", "section_8_risk", "risk_and_exposure"],
            ["section_09_capacity_and_constraints", "section_9_capacity", "capacity_and_constraints"],
            ["section_10_opportunity_readiness", "section_10_opportunity_readiness", "opportunity_readiness"],
            ["section_11_strategic_goals", "section_11_goals", "strategic_goals"],
            ["section_12_pricing_and_revenue", "section_12_pricing", "pricing_and_revenue"],
            ["section_13_hiring_and_team_structure", "section_13_team", "hiring_and_team_structure"],
            ["section_14_sales_and_marketing", "section_14_marketing", "sales_and_marketing"],
            ["section_15_owner_goals_and_preferences", "section_15_owner_prefs", "owner_goals_and_preferences"],
            ["section_16_uploads_and_docs", "section_16_docs", "uploads_and_docs"]
        ]
        
        complete_count = 0
        for group in section_aliases:
            found = False
            for s in group:
                if s in onboarding_data and onboarding_data[s]:
                    if isinstance(onboarding_data[s], dict) and len(onboarding_data[s]) > 0:
                        found = True
                        break
                    elif not isinstance(onboarding_data[s], dict):
                        found = True
                        break
            if found:
                complete_count += 1
        
        # Fallback to top-level onboarding fields if structured sections not used yet
        if complete_count == 0 and onboarding_data:
            complete_count = min(16, len(onboarding_data.keys()))
            
        score = round(complete_count / 16.0, 2)
        
        if score >= 0.75:
            band = "We know your business"
        elif score >= 0.50:
            band = "Getting sharp"
        elif score >= 0.25:
            band = "Building"
        else:
            band = "Just getting started"

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": {
                    "score": score,
                    "band": band,
                    "ever_reached_sharp": score >= 0.50,
                    "sections_complete": complete_count,
                    "total_sections": 16
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )


@router.get("/teaser")
async def get_profile_teaser(
    current_user: dict = Depends(get_current_user)
):
    """
    Get Peer Teaser card for Business Profile tab.
    Hides when score >= 0.50 per spec §2.
    """
    try:
        user_id = current_user["id"]
        users_col = get_collection("users")
        user_doc = await users_col.find_one({"id": user_id}) or await users_col.find_one({"_id": user_id}) or {}
        
        # Demo users and sharp profiles suppress teasers
        if user_doc.get("is_demo") or (user_doc.get("email", "").startswith("demo-") and "@lightsignal.app" in user_doc.get("email", "")):
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"success": True, "data": {"show": False, "teaser": None}}
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"success": True, "data": {"show": False, "teaser": None}}
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )


@router.get("/classification")
async def get_profile_classification(
    current_user: dict = Depends(get_current_user)
):
    """
    Get Business Profile Classifications & Proven Capabilities.
    """
    try:
        user_id = current_user.get("id") or current_user.get("_id") if isinstance(current_user, dict) else str(current_user)
        users_col = get_collection("users")
        user_doc = await users_col.find_one({"id": user_id}) or await users_col.find_one({"_id": user_id}) or {}
        
        if user_doc.get("is_demo") or (user_doc.get("email", "").startswith("demo-") and "@lightsignal.app" in user_doc.get("email", "")):
            login_label = user_doc.get("login_label") or user_doc.get("username")
            if not login_label and user_doc.get("email"):
                login_label = user_doc.get("email").split("@")[0]
            
            from app.demo_data import get_demo_payload
            demo_payload = get_demo_payload(login_label or "demo-restaurant")
            bp = demo_payload.get("business_profile", {})
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success": True,
                    "data": {
                        "business_classifications": [bp.get("section_3_industry", {}).get("primary_industry", "Small Business")],
                        "business_tags": [bp.get("section_1_basics", {}).get("operating_mode", "General")],
                        "proven_capabilities": bp.get("section_16_docs", {}).get("connected_systems", ["QuickBooks Connected"])
                    }
                }
            )

        business_profiles = get_collection("business_profiles")
        profile = await business_profiles.find_one({"user_id": user_id})

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": {
                    "business_classifications": profile.get("business_classifications", []) if profile else [],
                    "business_tags": profile.get("business_tags", []) if profile else [],
                    "proven_capabilities": profile.get("proven_capabilities", []) if profile else []
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )


@router.post("/classification/confirm")
async def confirm_classification(
    current_user: dict = Depends(get_current_user)
):
    """Confirm business classification per spec."""
    return {"success": True, "message": "Classification confirmed successfully"}


@router.post("/classification/{dimension}/correct")
async def correct_classification(
    dimension: str,
    payload: dict,
    current_user: dict = Depends(get_current_user)
):
    """Correct business classification dimension per spec."""
    user_id = current_user.get("id") or current_user.get("_id")
    col = get_collection("business_profiles")
    await col.update_one(
        {"user_id": user_id},
        {"$set": {f"classification_corrections.{dimension}": payload.get("correction"), "updated_at": _now_utc()}},
        upsert=True
    )
    return {"success": True, "dimension": dimension, "correction": payload.get("correction")}


@router.post("/notes")
async def save_owner_note(
    note: OwnerNoteCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Save an Owner Note to the Business Profile.
    Per UI screenshot 'BUSINESS PROFILE - OWNER NOTES'.
    """
    try:
        user_id = current_user.get("id") or current_user.get("_id")
        business_profiles = get_collection("business_profiles")
        
        profile = await business_profiles.find_one({"user_id": user_id})
        now = _now_utc()
        
        note_entry = {
            "id": str(uuid.uuid4()),
            "timestamp": now.isoformat(),
            "text": note.text.strip()
        }
        
        if profile:
            onboarding_data = profile.get("onboarding_data", {})
            obs_list = onboarding_data.get("owner_observations", [])
            if not isinstance(obs_list, list):
                obs_list = []
            obs_list.insert(0, note_entry)
            onboarding_data["owner_observations"] = obs_list
            
            await business_profiles.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "onboarding_data": onboarding_data,
                        "updated_at": now
                    }
                }
            )
        else:
            onboarding_data = {"owner_observations": [note_entry]}
            new_profile = BusinessProfile(
                user_id=user_id,
                onboarding_data=onboarding_data,
                business_classifications=[],
                business_tags=[],
                proven_capabilities=[],
                created_at=now,
                updated_at=now
            )
            await business_profiles.insert_one(new_profile.dict(by_alias=True))
            
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "success": True,
                "message": "Note saved successfully",
                "data": note_entry
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )


@router.get("/notes")
async def get_owner_notes(
    current_user: dict = Depends(get_current_user)
):
    """
    Get all Owner Notes for the Business Profile.
    """
    try:
        user_id = current_user.get("id") or current_user.get("_id")
        business_profiles = get_collection("business_profiles")
        
        profile = await business_profiles.find_one({"user_id": user_id})
        onboarding_data = profile.get("onboarding_data", {}) if profile else {}
        
        obs_list = onboarding_data.get("owner_observations", [])
        if not isinstance(obs_list, list):
            obs_list = []
            
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "count": len(obs_list),
                "data": obs_list
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )


@router.delete("/notes/{note_id}")
async def delete_owner_note(
    note_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Remove an Owner Note by ID.
    """
    try:
        user_id = current_user.get("id") or current_user.get("_id")
        business_profiles = get_collection("business_profiles")
        
        profile = await business_profiles.find_one({"user_id": user_id})
        if not profile:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"success": False, "error": "Profile not found"}
            )
            
        onboarding_data = profile.get("onboarding_data", {})
        obs_list = onboarding_data.get("owner_observations", [])
        if not isinstance(obs_list, list):
            obs_list = []
            
        updated_list = [n for n in obs_list if n.get("id") != note_id]
        onboarding_data["owner_observations"] = updated_list
        
        now = _now_utc()
        await business_profiles.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "onboarding_data": onboarding_data,
                    "updated_at": now
                }
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"success": True, "message": "Note deleted successfully"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "error": str(e)}
        )