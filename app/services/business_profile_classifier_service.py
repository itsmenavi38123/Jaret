from typing import Dict, Any, Optional, List
import json
from app.services.claude_service import claude_service
from app.services.classifier_prompt import get_classifier_prompt
from app.services.tagging_service import tagging_service


class BusinessProfileClassifierService:
    """
    Business Profile Classifier Service powered by Canonical LightSignal Classifier V4.1.
    Performs full 10-dimension business classification and emits rich contextual metadata.
    """

    async def classify_business_async(
        self,
        business_profile: Dict[str, Any],
        opportunities_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute full AI classification using Canonical Classifier V4.1 prompt.
        """
        system_prompt = get_classifier_prompt()
        
        try:
            result = await claude_service.json_completion(
                system_prompt=system_prompt,
                user_content={
                    "business_profile": business_profile,
                    "opportunities_profile": opportunities_profile,
                },
                temperature=0.1,
                max_tokens=4000,
            )
            
            # Ensure backwards compatibility keys exist
            tags = result.get("tags", [])
            classifications = []
            if result.get("operational_format"):
                classifications.append(result["operational_format"])
            if result.get("business_stage"):
                classifications.append(result["business_stage"])
            if result.get("audience_type"):
                classifications.append(result["audience_type"])
                
            result.setdefault("business_classifications", classifications)
            result.setdefault("business_tags", tags)
            result.setdefault("proven_capabilities", tags)
            
            return result
        except Exception as e:
            print(f"Classifier V4.1 AI completion failed: {e}")
            return self._heuristic_fallback(business_profile.get("onboarding_data", business_profile))

    def classify_business(
        self,
        onboarding: Dict[str, Any],
        opportunities_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Synchronous classification method with rich heuristics and tag extraction.
        """
        return self._heuristic_fallback(onboarding)

    def _heuristic_fallback(self, onboarding: Dict[str, Any]) -> Dict[str, Any]:
        classifications = []
        proven_capabilities = []

        industry = (onboarding.get("industry_description", "") or onboarding.get("industry", "") or "").lower()
        naics = str(onboarding.get("naics_code", "") or "")
        main_products = (onboarding.get("main_products", "") or "").lower()

        staff_count = onboarding.get("full_time_employees") or onboarding.get("staff_count")

        try:
            staff_count = int(staff_count)
        except (TypeError, ValueError):
            staff_count = None

        if staff_count is not None:
            if staff_count <= 2:
                classifications.append("solo_operator")
            elif 3 <= staff_count <= 10:
                classifications.append("small_team")
            elif staff_count >= 10:
                classifications.append("established_smb")

        if "food" in industry or "cafe" in industry or "restaurant" in industry or naics.startswith("722") or naics.startswith("311"):
            classifications.append("food_hospitality")

        if naics.startswith("236") or naics.startswith("237") or naics.startswith("238"):
            classifications.append("trades_contractor")

        if naics.startswith("541") or naics.startswith("561"):
            classifications.append("professional_services")

        if naics.startswith("621") or naics.startswith("713") or naics.startswith("812"):
            classifications.append("health_wellness")

        product_keywords = ["product", "retail", "packaged", "manufacturing", "goods", "coffee", "beverage", "food"]
        is_product_business = any(keyword in main_products for keyword in product_keywords)

        if is_product_business:
            classifications.append("product_business")
        else:
            classifications.append("service_business")

        business_tags = tagging_service.extract_business_tags(onboarding)
        proven_capabilities.extend(business_tags)

        city = onboarding.get("city", "")
        state = onboarding.get("state", "")

        return {
            "operational_format": classifications[0] if classifications else "general_business",
            "audience_type": "b2c" if "food_hospitality" in classifications or is_product_business else "b2b",
            "business_stage": "established_smb" if "established_smb" in classifications else "growth",
            "competitive_position": "local_differentiator",
            "geographic_context": {
                "neighborhood": onboarding.get("neighborhood"),
                "city": city,
                "state": state,
                "lat": onboarding.get("latitude", 0),
                "lng": onboarding.get("longitude", 0),
            },
            "revenue_model": "direct_sales" if is_product_business else "service_fee",
            "supply_chain_distinctives": [],
            "key_constraints": ["capacity"],
            "price_position": "mid_market",
            "service_pattern": "recurring",
            "tier_b_signals_active": ["food_cost_variance"] if "food_hospitality" in classifications else ["utilization_rate"],
            "peer_pool": f"{city} {industry} peer pool",
            "tensions": [],
            "tags": business_tags,
            "multi_output": None,
            "business_classifications": list(set(classifications)),
            "business_tags": business_tags,
            "proven_capabilities": list(set(proven_capabilities)),
        }


business_profile_classifier_service = BusinessProfileClassifierService()