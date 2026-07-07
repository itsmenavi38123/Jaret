from pydantic import BaseModel
from typing import Literal

class LandingModeUpdateRequest(BaseModel):
    landing_mode: Literal["waitlist", "trial"]
