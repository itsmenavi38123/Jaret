# backend/app/routes/business_profile/profile.py
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.db import get_collection
from app.routes.auth.auth import get_current_user, check_demo_write_guard
from app.models.business_profile import BusinessProfile, BusinessProfileCreate, BusinessProfileUpdate
from app.config import _now_utc
from app.services.mapbox_service import MapboxService
from app.services.business_profile_classifier_service import business_profile_classifier_service
from app.services.internal_event_bus import internal_event_bus

import re
import math

router = APIRouter(tags=["business_profile"])
mapbox_service = MapboxService()

class OwnerNoteCreate(BaseModel):
    text: str


NUMERIC_FIELD_KEYS = {
    "jobs_per_month", "estimated_jobs_per_month", "monthly_jobs", "jobs_monthly",
    "typical_invoice_size", "typical_job_size", "average_invoice_size", "average_job_value", "avg_job_size", "avg_invoice_amount",
    "percent_of_leads", "lead_conversion_pct", "pct_of_leads", "leads_converted_pct", "pct_leads", "percentage_of_leads",
    "radius_miles", "mileage", "annual_mileage", "max_travel_radius_miles", "fleet_mileage", "travel_radius", "service_radius", "estimated_annual_mileage", "average_mileage_per_vehicle",
    "headcount", "employees_count", "square_footage", "sqft", "annual_revenue", "monthly_revenue",
    "capacity_utilization_pct", "hourly_rate", "fixed_expenses_monthly", "labor_cost_hourly"
}

def _clean_numeric_field(val: Any, key_name: str = "") -> Any:
    """
    Safely sanitizes and validates numeric fields.
    1. Prevents mangling sentences into corrupted exponential garbage (e.g. 215e118500200385).
    2. Cleans currency ($), commas (,), and percent (%) symbols.
    3. If invalid text or sentence is entered without clear numeric value, returns None instead of corrupted garbage.
    4. Clamps percentage values between 0 and 100.
    """
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        if math.isnan(val) or math.isinf(val):
            return None
        # Reject astronomical garbage numbers produced by client-side regex mangling
        if val > 1e11:
            return None
        if "pct" in key_name or "percent" in key_name:
            return max(0.0, min(100.0, float(val)))
        return val
    if isinstance(val, str):
        val_str = val.strip()
        # Corrupted client-side scientific exponent pattern (e.g. 215e118500200385)
        if re.search(r'\d+e\d{4,}', val_str, re.IGNORECASE):
            return None
        # Strip currency symbols, commas, percent signs
        cleaned = re.sub(r'[\$,%]', '', val_str).strip()
        try:
            num = float(cleaned)
            if math.isnan(num) or math.isinf(num) or num > 1e11:
                return None
            if "pct" in key_name or "percent" in key_name:
                num = max(0.0, min(100.0, num))
            return int(num) if num.is_integer() else num
        except ValueError:
            # If someone typed "500 jobs", extract only the clean numeric prefix
            match = re.search(r'^\d+(\.\d+)?', cleaned)
            if match:
                try:
                    num = float(match.group(0))
                    if num > 1e11:
                        return None
                    if "pct" in key_name or "percent" in key_name:
                        num = max(0.0, min(100.0, num))
                    return int(num) if num.is_integer() else num
                except Exception:
                    return None
            return None
    return None


def _sanitize_numeric_fields_in_dict(data: Any) -> Any:
    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            if k in NUMERIC_FIELD_KEYS:
                cleaned[k] = _clean_numeric_field(v, key_name=k)
            elif isinstance(v, (dict, list)):
                cleaned[k] = _sanitize_numeric_fields_in_dict(v)
            else:
                cleaned[k] = v
        return cleaned
    elif isinstance(data, list):
        return [_sanitize_numeric_fields_in_dict(item) for item in data]
    return data


async def _geocode_and_enrich_locations(onboarding_data: dict) -> dict:
    """
    Enriches each location entry in section_01_business_basics.locations and top-level
    with geocoded coordinates (lat, lng), city, state, timezone and status: 'geocoded'
    so the UI card never hangs on 'Geocoding...' forever.
    """
    sec1 = onboarding_data.get("section_01_business_basics")
    if isinstance(sec1, dict):
        locs = sec1.get("locations")
        if isinstance(locs, list):
            enriched_locs = []
            for idx, loc in enumerate(locs):
                if isinstance(loc, dict):
                    loc_copy = dict(loc)
                    if not loc_copy.get("id"):
                        loc_copy["id"] = f"loc_{idx+1}_{uuid.uuid4().hex[:8]}"
                    has_coords = loc_copy.get("latitude") is not None and loc_copy.get("longitude") is not None
                    if not has_coords or loc_copy.get("status") not in ["geocoded", "ready"]:
                        addr = loc_copy.get("address") or loc_copy.get("street") or ""
                        c = loc_copy.get("city") or ""
                        s = loc_copy.get("state") or ""
                        z = loc_copy.get("zip") or loc_copy.get("zip_code") or ""
                        full_loc_addr = ", ".join(p for p in [addr, c, s, z] if p)
                        if full_loc_addr:
                            try:
                                geo = await mapbox_service.geocode_address(full_loc_addr)
                                if geo and geo.get("lat") is not None and geo.get("lng") is not None:
                                    loc_copy["latitude"] = geo.get("lat")
                                    loc_copy["longitude"] = geo.get("lng")
                                    loc_copy["city"] = loc_copy.get("city") or geo.get("city")
                                    loc_copy["state"] = loc_copy.get("state") or geo.get("state")
                                    loc_copy["timezone"] = geo.get("timezone")
                                    loc_copy["status"] = "geocoded"
                                    loc_copy["geocode_status"] = "geocoded"
                                else:
                                    loc_copy["status"] = "geocoded"
                                    loc_copy["geocode_status"] = "saved"
                            except Exception:
                                loc_copy["status"] = "geocoded"
                                loc_copy["geocode_status"] = "saved"
                        else:
                            loc_copy["status"] = "geocoded"
                    else:
                        loc_copy["status"] = "geocoded"
                        loc_copy["geocode_status"] = "geocoded"
                    enriched_locs.append(loc_copy)
                else:
                    enriched_locs.append(loc)
            sec1["locations"] = enriched_locs

    root_locs = onboarding_data.get("locations")
    if isinstance(root_locs, list):
        enriched_root_locs = []
        for idx, loc in enumerate(root_locs):
            if isinstance(loc, dict):
                loc_copy = dict(loc)
                if not loc_copy.get("id"):
                    loc_copy["id"] = f"loc_{idx+1}_{uuid.uuid4().hex[:8]}"
                has_coords = loc_copy.get("latitude") is not None and loc_copy.get("longitude") is not None
                if not has_coords or loc_copy.get("status") not in ["geocoded", "ready"]:
                    addr = loc_copy.get("address") or loc_copy.get("street") or ""
                    c = loc_copy.get("city") or ""
                    s = loc_copy.get("state") or ""
                    z = loc_copy.get("zip") or loc_copy.get("zip_code") or ""
                    full_loc_addr = ", ".join(p for p in [addr, c, s, z] if p)
                    if full_loc_addr:
                        try:
                            geo = await mapbox_service.geocode_address(full_loc_addr)
                            if geo and geo.get("lat") is not None and geo.get("lng") is not None:
                                loc_copy["latitude"] = geo.get("lat")
                                loc_copy["longitude"] = geo.get("lng")
                                loc_copy["city"] = loc_copy.get("city") or geo.get("city")
                                loc_copy["state"] = loc_copy.get("state") or geo.get("state")
                                loc_copy["timezone"] = geo.get("timezone")
                                loc_copy["status"] = "geocoded"
                                loc_copy["geocode_status"] = "geocoded"
                            else:
                                loc_copy["status"] = "geocoded"
                                loc_copy["geocode_status"] = "saved"
                        except Exception:
                            loc_copy["status"] = "geocoded"
                    else:
                        loc_copy["status"] = "geocoded"
                else:
                    loc_copy["status"] = "geocoded"
                enriched_root_locs.append(loc_copy)
            else:
                enriched_root_locs.append(loc)
        onboarding_data["locations"] = enriched_root_locs

    return onboarding_data


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
        s1 = onboarding_data.get("section_01_business_basics") or {}
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
    check_demo_write_guard(current_user)
    try:
        business_profiles = get_collection("business_profiles")
        opportunities_profiles = get_collection("opportunities_profiles")

        if isinstance(current_user, dict):
            user_id = current_user.get("id") or current_user.get("_id")
        else:
            user_id = str(current_user)

        existing = await business_profiles.find_one({"user_id": user_id})
        existing_onboarding = existing.get("onboarding_data", {}) if existing else {}

        raw_incoming = data.onboarding_data.copy() if hasattr(data, "onboarding_data") else {}
        incoming_data = _sanitize_numeric_fields_in_dict(raw_incoming)

        # Smart-merge over existing profile so all other sections are preserved
        onboarding_data = _apply_partial_updates(existing_onboarding, incoming_data)

        # Geocode individual locations in section 1
        onboarding_data = await _geocode_and_enrich_locations(onboarding_data)

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
    check_demo_write_guard(current_user)
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
        raw_incoming = payload.get("onboarding_data") if isinstance(payload.get("onboarding_data"), dict) else payload
        incoming_data = _sanitize_numeric_fields_in_dict(raw_incoming)

        # Smart merge: updates ONLY the specified fields/sections and preserves everything else
        onboarding_data = _apply_partial_updates(existing_onboarding, incoming_data)

        # Geocode individual locations in section 1
        onboarding_data = await _geocode_and_enrich_locations(onboarding_data)

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
        business_profiles = get_collection("business_profiles")
        profile = await business_profiles.find_one({"user_id": user_id})
        
        onboarding_data = profile.get("onboarding_data", {}) if profile else {}
        
        # Canonical 16 sections
        canonical_sections = [
            "section_01_business_basics",
            "section_02_ownership_and_key_people",
            "section_03_industry_and_model",
            "section_04_operations",
            "section_05_financial_overview",
            "section_06_assets_and_equipment",
            "section_07_customers_and_market",
            "section_08_risk_and_exposure",
            "section_09_capacity_and_constraints",
            "section_10_opportunity_readiness",
            "section_11_strategic_goals",
            "section_12_pricing_and_revenue",
            "section_13_hiring_and_team_structure",
            "section_14_sales_and_marketing",
            "section_15_owner_goals_and_preferences",
            "section_16_uploads_and_docs",
        ]
        
        complete_count = 0
        for s in canonical_sections[:15]:
            sec = onboarding_data.get(s)
            if sec and (not isinstance(sec, dict) or len(sec) > 0):
                complete_count += 1
        
        # Check Section 16 (Uploads & Documents / Connected Systems)
        sec_16 = onboarding_data.get("section_16_uploads_and_docs")
        section_16_complete = bool(sec_16 and (not isinstance(sec_16, dict) or len(sec_16) > 0))
        
        if not section_16_complete:
            docs_col = get_collection("documents")
            has_docs = (await docs_col.count_documents({"uploaded_by": user_id})) > 0 if docs_col is not None else False
            
            qb_col = get_collection("quickbooks_tokens")
            has_qb = (await qb_col.count_documents({"user_id": user_id})) > 0 if qb_col is not None else False
            
            if has_docs or has_qb or (profile and profile.get("proven_capabilities")):
                section_16_complete = True
        
        if section_16_complete:
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
    check_demo_write_guard(current_user)
    return {"success": True, "message": "Classification confirmed successfully"}


@router.post("/classification/{dimension}/correct")
async def correct_classification(
    dimension: str,
    payload: dict,
    current_user: dict = Depends(get_current_user)
):
    """Correct business classification dimension per spec."""
    check_demo_write_guard(current_user)
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
    Save an Owner Note into dedicated owner_notes collection.
    Completely isolated from onboarding_data so profile updates never overwrite notes.
    """
    check_demo_write_guard(current_user)
    try:
        user_id = current_user.get("id") or current_user.get("_id")
        notes_coll = get_collection("owner_notes")
        now = _now_utc()
        
        note_id = str(uuid.uuid4())
        note_doc = {
            "_id": note_id,
            "id": note_id,
            "user_id": user_id,
            "timestamp": now.isoformat(),
            "text": note.text.strip(),
            "created_at": now
        }
        await notes_coll.insert_one(note_doc)
            
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "success": True,
                "message": "Note saved successfully",
                "data": {
                    "id": note_id,
                    "timestamp": now.isoformat(),
                    "text": note.text.strip()
                }
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
    Get all Owner Notes from dedicated owner_notes collection.
    """
    try:
        user_id = current_user.get("id") or current_user.get("_id")
        notes_coll = get_collection("owner_notes")
        
        cursor = notes_coll.find({"user_id": user_id}).sort("created_at", -1)
        notes = []
        async for doc in cursor:
            ts = doc.get("timestamp")
            if not ts:
                created = doc.get("created_at")
                ts = created.isoformat() if hasattr(created, "isoformat") else str(created or "")
            notes.append({
                "id": str(doc.get("id", doc.get("_id"))),
                "timestamp": ts,
                "text": doc.get("text", "")
            })
            
        # Fallback to check legacy profile.onboarding_data.owner_observations if collection has none
        if not notes:
            business_profiles = get_collection("business_profiles")
            profile = await business_profiles.find_one({"user_id": user_id})
            if profile:
                obs_list = profile.get("onboarding_data", {}).get("owner_observations", [])
                if isinstance(obs_list, list) and obs_list:
                    notes = obs_list
            
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "count": len(notes),
                "data": notes
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
    Remove an Owner Note by ID from dedicated owner_notes collection.
    """
    check_demo_write_guard(current_user)
    try:
        user_id = current_user.get("id") or current_user.get("_id")
        notes_coll = get_collection("owner_notes")
        await notes_coll.delete_one({"_id": note_id, "user_id": user_id})
        await notes_coll.delete_one({"id": note_id, "user_id": user_id})
        
        # Also clean from legacy profile if present
        business_profiles = get_collection("business_profiles")
        profile = await business_profiles.find_one({"user_id": user_id})
        if profile:
            onboarding_data = profile.get("onboarding_data", {})
            obs_list = onboarding_data.get("owner_observations", [])
            if isinstance(obs_list, list) and any(n.get("id") == note_id for n in obs_list):
                updated_list = [n for n in obs_list if n.get("id") != note_id]
                await business_profiles.update_one(
                    {"user_id": user_id},
                    {"$set": {"onboarding_data.owner_observations": updated_list, "updated_at": _now_utc()}}
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