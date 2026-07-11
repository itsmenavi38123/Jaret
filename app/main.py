# backend/app/main.py
import os
from fastapi import FastAPI, Request
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
from app.routes.auth.auth import router as auth_router, api_router as auth_api_router
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
from app.routes.admin_auth import router as admin_auth_router
from app.routes.integrations import router as integrations_router
from app.routes.documents import router as documents_router
from app.routes.notification_settings import router as notification_settings_router
from app.routes.waitlist import router as waitlist_router
from app.routes.settings import router as settings_router

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

# Middleware to log API and Webhook errors to system_health_logs
@app.middleware("http")
async def db_health_logging_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        if response.status_code >= 500:
            from app.services.system_health_logs_service import system_health_logs_service
            from app.models.system_health_logs import SystemHealthLogCreate
            log_type = "webhook_failure" if "webhook" in str(request.url.path).lower() else "api_error"
            with suppress(Exception):
                await system_health_logs_service.log_error(SystemHealthLogCreate(
                    log_type=log_type,
                    service="api",
                    endpoint=str(request.url.path),
                    error_message=f"HTTP status {response.status_code}",
                    status_code=response.status_code
                ))
        return response
    except Exception as e:
        from app.services.system_health_logs_service import system_health_logs_service
        from app.models.system_health_logs import SystemHealthLogCreate
        log_type = "webhook_failure" if "webhook" in str(request.url.path).lower() else "api_error"
        with suppress(Exception):
            await system_health_logs_service.log_error(SystemHealthLogCreate(
                log_type=log_type,
                service="api",
                endpoint=str(request.url.path),
                error_message=str(e),
                status_code=500
            ))
        raise e

# ROUTER REGISTRATIONS
app.include_router(auth_router, prefix="/auth")
app.include_router(auth_api_router, prefix="/api")
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
app.include_router(admin_auth_router)
app.include_router(documents_router, prefix="/documents")
app.include_router(notification_settings_router, prefix="/api/notification-settings")
app.include_router(waitlist_router, prefix="/api")
app.include_router(settings_router, prefix="/api")

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
            if now.hour == 5 and now.minute == 0:
                try:
                    from app.db import get_collection
                    from app.services.email_service import send_email
                    from datetime import timedelta, timezone
                    
                    users_col = get_collection("users")
                    now_time = datetime.now(timezone.utc)
                    min_trial_end = now_time + timedelta(days=2)
                    max_trial_end = now_time + timedelta(days=3)
                    
                    cursor = users_col.find({
                        "trial_ends_at": {
                            "$gte": min_trial_end,
                            "$lte": max_trial_end
                        },
                        "trial_warning_sent": {"$ne": True},
                        "is_paused": False,
                        "is_beta": False
                    })
                    
                    # Load template
                    import os
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    template_path = os.path.join(base_dir, "utils", "templates", "trial_ending.html")
                    
                    if not os.path.exists(template_path):
                        print(f"Trial ending template not found at {template_path}. Skipping warning emails.")
                    else:
                        with open(template_path, "r", encoding="utf-8") as f:
                            html_template = f.read()

                        async for user in cursor:
                            trial_end_str = user["trial_ends_at"].strftime("%B %d, %Y")
                            manage_subscription_url = "https://lightsignal.app/settings"
                            
                            html_content = html_template.format(
                                first_name=user.get("full_name", "there"),
                                trial_end_date=trial_end_str,
                                manage_subscription_url=manage_subscription_url
                            )
                            
                            try:
                                send_email(
                                    to_email=user["email"],
                                    subject="Your LightSignal trial ends in 2 days",
                                    html_content=html_content,
                                    from_email="hello@lightsignal.app"
                                )
                                await users_col.update_one(
                                    {"_id": user["_id"]},
                                    {"$set": {"trial_warning_sent": True}}
                                )
                            except Exception as email_err:
                                print(f"Error sending trial warning email to {user['email']}: {email_err}")
                except Exception as scheduler_err:
                    print(f"Trial warning scheduler error: {scheduler_err}")
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
