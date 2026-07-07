from uuid import uuid4
from fastapi import APIRouter, status, BackgroundTasks
from fastapi.responses import JSONResponse

from app.db import get_collection
from app.config import _now_utc
from app.models.waitlist import WaitlistSignupRequest
from app.services.email_service import send_email

router = APIRouter(tags=["waitlist"])

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(BASE_DIR, "utils", "templates", "waitlist.html")

def send_waitlist_email(email: str):
    try:
        html_content = ""
        if os.path.exists(TEMPLATE_PATH):
            with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
                html_content = f.read()
        else:
            print(f"Waitlist template not found at {TEMPLATE_PATH}")
            return
            
        send_email(
            to_email=email,
            subject="You're on the list",
            html_content=html_content,
            from_email="hello@lightsignal.app",
            from_name="LightSignal"
        )
    except Exception as e:
        print(f"Error sending waitlist confirmation email: {e}")

@router.post("/waitlist")
async def join_waitlist(payload: WaitlistSignupRequest, background_tasks: BackgroundTasks):
    email = payload.email.strip().lower()
    waitlist_col = get_collection("waitlist")
    
    existing = await waitlist_col.find_one({"email": email})
    if existing:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error": "You're already on the list! We'll be in touch as soon as your spot opens."
            }
        )

    await waitlist_col.insert_one({
        "_id": str(uuid4()),
        "email": email,
        "created_at": _now_utc()
    })

    background_tasks.add_task(send_waitlist_email, email)
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": "Successfully joined waitlist"
        }
    )
