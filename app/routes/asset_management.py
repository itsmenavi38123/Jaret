from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.db import get_collection
from app.routes.auth.auth import get_current_user
from app.services.asset_management_service import (
    compute_asset_insights,
    get_asset_management_overview,
)

router = APIRouter(tags=["Asset Management"])


class AssetInput(BaseModel):
    asset_id: str
    category: Optional[str] = None
    type: Optional[str] = None
    purchase_price: float = Field(..., ge=0)
    purchase_date: Optional[date] = None
    in_service_date: Optional[date] = None
    salvage_value: float = Field(0, ge=0)
    useful_life_months: int = Field(60, gt=0)
    depreciation_method: str = Field("SL", pattern="^(?i)(SL|DDB|MACRS)$")
    replacement_value: Optional[float] = None
    utilization_pct: Optional[float] = Field(default=75, ge=0, le=100)
    availability_pct: Optional[float] = Field(default=95, ge=0, le=100)
    downtime_hours_30d: Optional[float] = Field(default=0, ge=0)
    faults_last_30d: Optional[int] = Field(default=0, ge=0)
    maintenance_compliance_pct: Optional[float] = Field(default=90, ge=0, le=100)
    next_service_date: Optional[date] = None
    warranty_expiration: Optional[date] = None
    insurance_expiration: Optional[date] = None
    book_value: Optional[float] = None
    replacement_value_currency: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "asset_id": "VEH-1001",
                "category": "Vehicles",
                "type": "Reefer Truck",
                "purchase_price": 165000,
                "purchase_date": "2021-03-15",
                "in_service_date": "2021-04-01",
                "salvage_value": 35000,
                "useful_life_months": 84,
                "depreciation_method": "SL",
                "replacement_value": 178000,
                "utilization_pct": 82,
                "availability_pct": 96,
                "downtime_hours_30d": 6,
                "faults_last_30d": 1,
                "maintenance_compliance_pct": 94,
                "next_service_date": "2025-01-15",
                "warranty_expiration": "2026-04-01",
                "insurance_expiration": "2025-08-01",
            }
        }


class AssetComputeRequest(BaseModel):
    assets: Optional[List[AssetInput]] = None
    as_of: Optional[date] = Field(
        default=None,
        description="Computation reference date. Defaults to today when omitted.",
    )


@router.get("/assets", summary="List assets for the current tenant")
async def list_assets(current_user: dict = Depends(get_current_user)):
    """
    Return the asset registry for the authenticated user.

    Data is sourced from the `assets` collection only – no static/demo assets.
    """
    user_id = current_user["id"]
    assets_collection = get_collection("assets")

    docs = await assets_collection.find({"user_id": user_id}).to_list(length=None)
    # Convert MongoDB ObjectId to string if present
    for doc in docs:
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])

    return {"assets": docs}


@router.post("/assets/compute", summary="Compute depreciation and health KPIs")
async def compute_assets(
    payload: AssetComputeRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Compute depreciation, health, and KPI summaries.

    - If `assets` is provided in the payload, those records are used directly.
    - If omitted, the computation is performed on the caller's stored assets.
    """
    assets: Optional[list] = None

    if payload.assets:
        assets = [asset.dict() for asset in payload.assets]
    else:
        assets_collection = get_collection("assets")
        user_id = current_user["id"]
        docs = await assets_collection.find({"user_id": user_id}).to_list(length=None)
        if not docs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No assets found for this user to compute.",
            )
        assets = docs

    return compute_asset_insights(assets=assets, reference_date=payload.as_of)

