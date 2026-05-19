from typing import Dict, Any
from app.services.tagging_service import tagging_service


class BusinessProfileClassifierService:

    def classify_business(
        self,
        onboarding: Dict[str, Any],
        opportunities_profile: Dict[str, Any] = None,
    ) -> Dict[str, Any]:

        classifications = []
        proven_capabilities = []

        industry = (onboarding.get("industry_description", "") or "").lower()
        naics = str(onboarding.get("naics_code", "") or "")
        main_products = (onboarding.get("main_products", "") or "").lower()

        staff_count = onboarding.get("full_time_employees")

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

        if "food" in industry or "cafe" in industry or naics.startswith("722") or naics.startswith("311"):
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

        return {
            "business_classifications": list(set(classifications)),
            "business_tags": business_tags,
            "proven_capabilities": list(set(proven_capabilities)),
        }


business_profile_classifier_service = BusinessProfileClassifierService()