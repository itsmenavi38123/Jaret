# backend/app/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.db import create_indexes, close_client

# load .env (install python-dotenv if you don't have it: pip install python-dotenv)
load_dotenv()

# import routers (make sure backend/app/routes/auth/auth.py exposes `router`)
from app.routes.auth.auth import router as auth_router
from app.routes.quickbooks.auth import router as quickbooks_router
from app.routes.xero.auth import router as xero_auth_router
from app.routes.xero.accounts import router as xero_accounts_router
from app.routes.financial_overview import router as financial_overview_router
from app.routes.business_profile.profile import router as business_profile_router
from app.routes.opportunities_profile import router as opportunities_profile_router
from app.routes.ai_opportunities import router as ai_opportunities_router

app = FastAPI(
    title=os.getenv("APP_NAME", "FastAPI Backend"),
    description="A FastAPI backend project",
    version=os.getenv("APP_VERSION", "1.0.0"),
)

# CORS - tighten in production
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
if allowed_origins == "*":
    cors_origins = ["*"]
else:
    cors_origins = [o.strip() for o in allowed_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth")
app.include_router(quickbooks_router, prefix="/quickbooks")
app.include_router(xero_auth_router, prefix="/xero/auth")
app.include_router(xero_accounts_router, prefix="/xero")
app.include_router(financial_overview_router, prefix="/api")
app.include_router(business_profile_router, prefix="/business-profile")
app.include_router(opportunities_profile_router, prefix="/opportunities-profile")
app.include_router(ai_opportunities_router, prefix="/api/ai/opportunities")


@app.on_event("startup")
async def on_startup():
    await create_indexes()


@app.on_event("shutdown")
async def on_shutdown():
    close_client()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to FastAPI Backend",
        "status": "running",
        "version": os.getenv("APP_VERSION", "1.0.0"),
    }
