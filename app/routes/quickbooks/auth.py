from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse
from app.services import quickbooks_service
from app.services.quickbooks_token_service import quickbooks_token_service
from app.models.quickbooks.token import QuickBooksTokenCreate
from app.routes.auth.auth import get_current_user
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from datetime import datetime, timedelta
from jose import jwt
from app.config import JWT_SECRET, JWT_ALGORITHM


router = APIRouter()

@router.get("/login")
async def login(
    current_user: dict = Depends(get_current_user),
    redirect_uri: str = None
):
    """
    Redirects the user to the QuickBooks authorization URL.
    Optionally accepts a custom redirect_uri parameter to override the configured one.
    """
    state_data = {
        "user_id": current_user["id"], 
        "exp": datetime.utcnow() + timedelta(minutes=10)
    }
    
    if redirect_uri:
        state_data["redirect_uri"] = redirect_uri
    
    state = jwt.encode(
        state_data,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )
    auth_url = quickbooks_service.get_authorization_url(state=state, redirect_uri=redirect_uri)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({
            "success": True,
            "data": {
                "auth_url": auth_url,
            }
        })
    )

@router.get("/tokens")
async def get_tokens(current_user: dict = Depends(get_current_user)):
    """
    Retrieves all QuickBooks tokens for the authenticated user.
    """
    user_id = current_user["id"]
    tokens = await quickbooks_token_service.get_tokens_by_user(user_id)
    
    public_tokens = []
    for token in tokens:
        public_tokens.append({
            "id": token.id,
            "realm_id": token.realm_id,
            "token_type": token.token_type,
            "expires_in": token.expires_in,
            "x_refresh_token_expires_in": token.x_refresh_token_expires_in,
            "created_at": token.created_at,
            "updated_at": token.updated_at,
            "is_active": token.is_active
        })
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({
            "success": True,
            "data": {
                "tokens": public_tokens,
                "count": len(public_tokens)
            }
        })
    )

@router.get("/tokens/{realm_id}")
async def get_token_by_realm(realm_id: str, current_user: dict = Depends(get_current_user)):
    """
    Retrieves the active QuickBooks token for a specific realm/company.
    """
    user_id = current_user["id"]
    token = await quickbooks_token_service.get_token_by_user_and_realm(user_id, realm_id)
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active token found for realm {realm_id}"
        )
    
    # Return token data (excluding sensitive information)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({
            "success": True,
            "data": {
                "token": {
                    "id": token.id,
                    "realm_id": token.realm_id,
                    "token_type": token.token_type,
                    "expires_in": token.expires_in,
                    "x_refresh_token_expires_in": token.x_refresh_token_expires_in,
                    "created_at": token.created_at,
                    "updated_at": token.updated_at,
                    "is_active": token.is_active
                }
            }
        })
    )

@router.get("/callback")
async def callback(request: Request):
    """
    Handles the callback from QuickBooks after the user authorizes the application.
    Stores the tokens in the database for the authenticated user.
    """
    code = request.query_params.get("code")
    realm_id = request.query_params.get("realmId")
    state = request.query_params.get("state")
    
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Authorization code not found in callback.")
    
    if not realm_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Realm ID not found in callback.")
        
    if not state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="State parameter not found in callback.")
        
    try:
        # Verify and decode the state parameter to get the user ID and redirect URI
        state_data = jwt.decode(state, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = state_data["user_id"]
        redirect_uri = state_data.get("redirect_uri")  # Optional redirect URI
    except jwt.JWTError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state parameter.")

    tokens = await quickbooks_service.exchange_code_for_tokens(code, redirect_uri)
    
    token_create = QuickBooksTokenCreate(
        user_id=user_id,
        realm_id=realm_id,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        id_token=tokens.get("id_token"),
        token_type=tokens.get("token_type", "bearer"),
        expires_in=tokens["expires_in"],
        x_refresh_token_expires_in=tokens["x_refresh_token_expires_in"]
    )
    
    stored_token = await quickbooks_token_service.create_token(token_create)
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({
            "success": True,
            "data": {
                "message": "QuickBooks tokens stored successfully",
                "realm_id": realm_id,
                "token_id": stored_token.id,
                "tokens": {
                    "token_type": tokens["token_type"],
                    "expires_in": tokens["expires_in"],
                    "x_refresh_token_expires_in": tokens["x_refresh_token_expires_in"],
                    # Note: We don't return the actual tokens for security
                }
            }
        })
    )
