# backend/app/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.db import create_indexes, close_client
import asyncio
from contextlib import suppress
from datetime import datetime
load_dotenv()

from app.services.scout_scheduler_service import ScoutSchedulerService
from app.services.dreaming_scheduler_service import DreamingSchedulerService

# import routers
from app.routes.auth.auth import router as auth_router
from app.routes.quickbooks.auth import router as quickbooks_router
from app.routes.xero.auth import router as xero_auth_router
from app.routes.xero.accounts import router as xero_accounts_router
from app.routes.financial_overview import router as financial_overview_router
from app.routes.dashboard import router as dashboard_router
from app.routes.tax_calendar import router as tax_calendar_router
from app.routes.business_profile.profile import router as business_profile_router
from app.routes.opportunities_profile import router as opportunities_profile_router
from app.routes.opportunities import router as opportunities_router
from app.routes.ai_opportunities import router as ai_opportunities_router
from app.routes.ai_scenarios import router as ai_scenarios_router
from app.routes.ai_health import router as ai_health_router
from app.services.new_demand_forecast import router as demand_forecast_router
from app.routes.asset_management import router as asset_management_router
from app.routes.preparation import router as preparation_router
from app.routes.admin import router as admin_router
from app.routes.integrations import router as integrations_router
from app.routes.documents import router as documents_router
from app.routes.notification_settings import router as notification_settings_router

scout_scheduler = ScoutSchedulerService()
dreaming_scheduler = DreamingSchedulerService()
scheduler_task = None

app = FastAPI(
    title=os.getenv("APP_NAME", "FastAPI Backend"),
    description="A FastAPI backend project",
    version=os.getenv("APP_VERSION", "1.0.0"),
)

# CORS
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

# ROUTER REGISTRATIONS
app.include_router(auth_router, prefix="/auth")
app.include_router(quickbooks_router, prefix="/quickbooks")
app.include_router(xero_auth_router, prefix="/xero/auth")
app.include_router(xero_accounts_router, prefix="/xero")
app.include_router(financial_overview_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(tax_calendar_router, prefix="/api")
app.include_router(business_profile_router, prefix="/business-profile")
app.include_router(opportunities_profile_router, prefix="/opportunities-profile")
app.include_router(opportunities_router, prefix="/api/opportunities")
app.include_router(ai_opportunities_router, prefix="/api/ai/opportunities")
app.include_router(ai_scenarios_router, prefix="/api/ai/scenarios")
app.include_router(ai_health_router, prefix="/api/ai/health")
app.include_router(demand_forecast_router, prefix="/api")
app.include_router(asset_management_router, prefix="/api")
app.include_router(preparation_router, prefix="/api")
app.include_router(integrations_router, prefix="/api")
app.include_router(admin_router)
app.include_router(documents_router, prefix="/documents")
app.include_router(notification_settings_router, prefix="/api/notification-settings")

@app.on_event("startup")
async def on_startup():
    global scheduler_task
    await create_indexes()
    try:
        from app.services.dia_orchestrator import DIAOrchestrator
        migrated = await DIAOrchestrator.migrate_profiles()
        print(f"Startup: Migrated {migrated} business profiles to the new DIA persistence schema.")
    except Exception as e:
        print(f"Startup: Error running business profile migration: {e}")
    async def scheduler_loop():
        while True:
            now = datetime.utcnow()
            if now.hour == 2 and now.minute == 0:
                try:
                    await scout_scheduler.run_daily_scout_pipeline()
                except Exception as e:
                    print(f"Scout scheduler error: {e}")
                await asyncio.sleep(60)
            if now.hour == 3 and now.minute == 0:
                try:
                    await scout_scheduler.run_daily_opportunity_rescore()
                except Exception as e:
                    print(f"Opportunity rescore error: {e}")
                await asyncio.sleep(60)
            if now.hour == 4 and now.minute == 0:
                try:
                    await dreaming_scheduler.run_daily_dreaming_pass()
                except Exception as e:
                    print(f"Dreaming scheduler error: {e}")
                await asyncio.sleep(60)
            await asyncio.sleep(20)
    print("Scheduler started")
    scheduler_task = asyncio.create_task(scheduler_loop())

@app.on_event("shutdown")
async def on_shutdown():
    global scheduler_task
    if scheduler_task:
        scheduler_task.cancel()
        with suppress(asyncio.CancelledError):
            await scheduler_task
    close_client()

@app.get("/")
async def root():
    return {
        "message": "Welcome to FastAPI Backend",
        "status": "running",
        "version": os.getenv("APP_VERSION", "1.0.0"),
    }
