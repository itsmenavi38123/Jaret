import os
import time
import uuid
import json
from fastapi import APIRouter
from google import genai as genai_video

# ===================== CONFIG =====================
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
VEO_MODEL = "veo-3.1-generate-preview"
MEDIA_ROOT = "media"

os.makedirs(MEDIA_ROOT, exist_ok=True)

# ===================== ROUTER =====================
router = APIRouter()

# ===================== GEMINI CLIENT =====================
veo_client = genai_video.Client(api_key=GOOGLE_API_KEY)

# ===================== VIDEO GENERATION =====================
def generate_8s_walkthrough_video(opportunity: dict) -> str:
    """
    Generates ONE 8-second video per opportunity.
    4 scenes compressed, ~2 seconds each.
    """

    prompt = f"""
Create a SINGLE 8-second business walkthrough video.

OPPORTUNITY DATA:
{json.dumps(opportunity, indent=2)}

The video must include EXACTLY 4 very short scenes,
each lasting about 2 seconds:

Scene 1 – Introduction (2s)
- What this opportunity is and why it matters

Scene 2 – Preparation (2s)
- What early preparation you should focus on

Scene 3 – Execution (2s)
- How execution impacts results

Scene 4 – Risks & Tips (2s)
- Key risks and one helpful response

NARRATION RULES:
- Generate narration internally
- Speak directly to the business owner ("you", "your")
- Very concise, punchy sentences
- No bullet points
- No pauses or long transitions

VISUAL RULES:
- Fast, clean transitions
- Subtle animated overlays
- Clear visual separation between scenes
- Feels like ONE continuous video

IMPORTANT:
- TOTAL VIDEO LENGTH MUST BE ~8 SECONDS
"""

    operation = veo_client.models.generate_videos(
        model=VEO_MODEL,
        prompt=prompt
    )

    while not operation.done:
        time.sleep(5)
        operation = veo_client.operations.get(operation)

    video_obj = operation.response.generated_videos[0]

    filename = f"walkthrough_8s_{uuid.uuid4().hex}.mp4"
    filepath = os.path.join(MEDIA_ROOT, filename)

    veo_client.files.download(file=video_obj.video)
    video_obj.video.save(filepath)

    return filename

# ===================== API =====================
@router.post("/generate-walkthrough-video")
async def generate_walkthrough_video(payload: dict):
    """
    Accepts:
    - single opportunity
    - OR multiple opportunities

    Returns:
    - ONE 8-second video per opportunity
    """

    # Normalize input
    if "opportunities" in payload:
        opportunities = payload["opportunities"]
    else:
        opportunities = [payload]

    results = []

    for opp in opportunities:
        video_file = generate_8s_walkthrough_video(opp)

        results.append({
            "title": opp.get("title"),
            "video_url": f"/media/{video_file}",
            "duration_seconds": 8
        })

    return {
        "status": "success",
        "total_videos": len(results),
        "videos": results
    }
