from typing import Dict, Any, Optional, List
from app.services.claude_service import claude_service
from app.services.google_places_service import google_places_service
from app.services.storefront_data_service import storefront_data_service
from app.services.storefront_prompt import STOREFRONT_AGENT_PROMPT
from app.services.storefront_skill import STOREFRONT_SKILL
from app.db import get_collection

class StorefrontAgentService:
    def __init__(self):
        self.claude = claude_service

    def _build_runtime_prompt(self) -> str:
        """
        Build runtime prompt exactly as specified:
        System Prompt + Skill loaded inline.
        """
        return f"{STOREFRONT_AGENT_PROMPT}\n\n{STOREFRONT_SKILL}"

    async def analyze_location(
        self,
        business_name: str,
        address: str,
        user_id: str,
        location_id: str | None = None,
    ) -> Dict[str, Any]:
        """
        Main entry point for Storefront Agent.
        
        Flow:
        1. Query Google Places to retrieve place_id and location (lat/lng).
        2. Pull classifier output and positioning anchor from the business profile.
        3. Collect storefront data (images + POI spatial vitality) using storefront_data_service.
        4. Pass 1: Vision (Fable 5) to describe images thoroughly.
        5. Pass 2: Reasoning (Opus) to evaluate fit against positioning.
        6. Return unified structured analysis.
        """
        
        # 1. Verify Place details and get coordinates
        google_place = await google_places_service.find_business(
            business_name=business_name,
            address=address
        )
        
        if not google_place:
            return {
                "location_id": location_id,
                "result": "insufficient_coverage",
                "reason": "Could not locate business via Google Places."
            }

        place_id = google_place.get("id")
        loc_coords = google_place.get("location", {})
        lat = loc_coords.get("latitude")
        lng = loc_coords.get("longitude")

        if not lat or not lng:
            return {
                "location_id": location_id,
                "result": "insufficient_coverage",
                "reason": "Could not resolve geographic coordinates for the business address."
            }

        # 2. Retrieve business profile for positioning anchor & classifications
        business_profile = await get_collection("business_profiles").find_one({"user_id": user_id})
        onboarding_data = business_profile.get("onboarding_data", {}) if business_profile else {}
        
        stated_positioning = None
        if onboarding_data:
            stated_positioning = (
                onboarding_data.get("stated_positioning")
                or onboarding_data.get("price_tier")
                or onboarding_data.get("positioning")
                or onboarding_data.get("pricing_strategy")
            )
            if isinstance(stated_positioning, dict) and "value" in stated_positioning:
                stated_positioning = stated_positioning["value"]

        inferred_classifications = business_profile.get("business_classifications", []) if business_profile else []
        density_tier = onboarding_data.get("urban_density", "urban")
        if isinstance(density_tier, dict) and "value" in density_tier:
            density_tier = density_tier["value"]
            
        operational_model = onboarding_data.get("operational_model", "retail")
        if isinstance(operational_model, dict) and "value" in operational_model:
            operational_model = operational_model["value"]

        positioning_anchor = {
            "source": "owner_stated" if stated_positioning else "classifier_inferred",
            "value": stated_positioning or (", ".join(inferred_classifications) if inferred_classifications else "standard retail / B2C positioning")
        }

        # 3. Collect storefront data
        website_url = onboarding_data.get("website_url")
        if isinstance(website_url, dict) and "value" in website_url:
            website_url = website_url["value"]

        data_payload = await storefront_data_service.collect_storefront_data(
            user_id=user_id,
            business_name=business_name,
            address=address,
            lat=lat,
            lng=lng,
            website_url=website_url,
            density_tier=density_tier
        )

        images = data_payload.get("images", [])
        print(
            f"[Storefront] Cost log | user={user_id} location={location_id or place_id} "
            f"images_sent_to_fable={len(images)} fable_pass_will_run={bool(images)}"
        )

        # 4. Pass 1 — Vision (Fable 5)
        pass1_description = {
            "exterior": "not_assessed — no imagery available",
            "interior": "not_assessed — no interior image available"
        }
        
        if images:
            fable_system_prompt = (
                "You are the LightSignal Storefront & Location Vision Agent.\n"
                "Your only job is to see storefront / location photos thoroughly and report structured descriptions zone by zone.\n"
                "Do NOT grade, evaluate fit, or advice. Just report attributes (wear, condition, legibility, materials, colors) for each visible zone.\n\n"
                "Zones to sweep:\n"
                "- signage (size, condition, legibility, lit/unlit)\n"
                "- windows/glass (cleanliness, cracking, tint, displays)\n"
                "- entrance/door (accessibility, condition)\n"
                "- facade/walls (paint, upkeep, materials, cracks)\n"
                "- lighting (presence of fixtures)\n"
                "- ground/sidewalk (cleanliness, frontage usage)\n"
                "- interior (if interior image exists: fixtures, clutter, dating)\n"
                "- neighboring context (vacancies, adjacent shops)\n\n"
                "Return STRICT JSON matching this format:\n"
                "{\n"
                "  \"exterior\": {\n"
                "    \"signage\": \"...\",\n"
                "    \"windows_glass\": \"...\",\n"
                "    \"entrance\": \"...\",\n"
                "    \"facade_walls\": \"...\",\n"
                "    \"lighting\": \"...\",\n"
                "    \"ground_frontage\": \"...\",\n"
                "    \"neighboring_context\": \"...\",\n"
                "    \"coverage_note\": \"...\"\n"
                "  },\n"
                "  \"interior\": \"...\"\n"
                "}"
            )

            # Build Anthropic visual blocks. Each image is preceded by its source +
            # capture date (when known) so the model can honor the staleness rule
            # (skill §2, §4.1c) instead of describing a photo with no age context.
            user_content = []
            user_content.append({
                "type": "text",
                "text": "Examine the attached images of the storefront/interior and provide the structured visual descriptions."
            })
            for idx, img in enumerate(images, start=1):
                capture_date = img.get("capture_date") or "unknown"
                user_content.append({
                    "type": "text",
                    "text": f"Image {idx} — source: {img.get('source', 'unknown')}, capture_date: {capture_date}"
                })
                user_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": img["base64"]
                    }
                })

            try:
                # Call Fable model via vision completion wrapper (dual-backend:
                # Fable sees, Opus reasons — see FABLE_MODEL in .env)
                pass1_res = await self.claude.vision_json_completion(
                    system_prompt=fable_system_prompt,
                    user_content=user_content,
                    temperature=0.1,
                    model_override=self.claude.fable_model
                )
                if pass1_res and isinstance(pass1_res, dict):
                    pass1_description = pass1_res
            except Exception as ex:
                print(f"Vision analysis Pass 1 failed: {ex}")
                pass1_description = {
                    "exterior": "Assessment failed during visual analysis processing.",
                    "interior": "Assessment failed during visual analysis processing."
                }

        # 5. Pass 2 — Reasoning & Fit (Opus 4.8)
        opus_system_prompt = self._build_runtime_prompt()
        opus_user_content = {
            "location_id": location_id or place_id,
            "positioning_anchor": positioning_anchor,
            "pass1_visual_descriptions": pass1_description,
            "geographic_vitality_data": data_payload.get("geographic_vitality", {}),
            "classifier_output": {
                "urban_density": density_tier,
                "operational_model": operational_model
            }
        }

        try:
            analysis_res = await self.claude.json_completion(
                system_prompt=opus_system_prompt,
                user_content=opus_user_content,
                temperature=0.2
            )
            return analysis_res
        except Exception as ex:
            print(f"Reasoning analysis Pass 2 failed: {ex}")
            return {
                "location_id": location_id or place_id,
                "result": "insufficient_coverage",
                "reason": f"Reasoning pass failed: {str(ex)}"
            }

storefront_agent_service = StorefrontAgentService()