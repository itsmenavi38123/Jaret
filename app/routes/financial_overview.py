from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.routes.auth.auth import get_current_user
from app.services.quickbooks_financial_service import quickbooks_financial_service

router = APIRouter(prefix="/api", tags=["financial-overview"])


@router.get("/financial-overview")
async def get_financial_overview(
    realm_id: str = Query(..., description="QuickBooks realm/company identifier"),
    force_refresh: bool = Query(False, description="Force a token refresh before fetching data"),
    current_user: dict = Depends(get_current_user),
):
    """
    Aggregate a financial overview for the authenticated user's connected QuickBooks company.
    """
    try:
        overview = await quickbooks_financial_service.get_financial_overview(
            user_id=current_user["id"],
            realm_id=realm_id,
            force_refresh=force_refresh,
        )
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build financial overview: {exc}",
        ) from exc

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({"success": True, "data": overview}),
    )

