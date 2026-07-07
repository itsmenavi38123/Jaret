# backend/app/models/waitlist.py
from pydantic import BaseModel, EmailStr

class WaitlistSignupRequest(BaseModel):
    email: EmailStr
