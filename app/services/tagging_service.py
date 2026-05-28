from typing import Dict, Any, List, Set


class TaggingService:

    def __init__(self):

        self.group_tag_mapping = {
            "food_truck": "food_beverage",
            "fine_dining": "food_beverage",
            "restaurant": "food_beverage",
            "fast_casual": "food_beverage",
            "casual_dining": "food_beverage",
            "bakery": "food_beverage",
            "coffee_shop": "food_beverage",
            "catering": "food_beverage",
            "food_producer": "food_beverage",
            "brewery": "food_beverage",
            "winery": "food_beverage",

            "boutique_clothing": "retail",
            "jewelry": "retail",
            "gift_shop": "retail",
            "sporting_goods": "retail",
            "home_goods": "retail",

            "marketing_agency": "professional_services",
            "accounting": "professional_services",
            "legal": "professional_services",
            "IT_services": "professional_services",
            "consulting": "professional_services",
            "staffing": "professional_services",
            "graphic_design": "professional_services",

            "photography": "creative",
            "videography": "creative",
            "event_planning": "creative",
            "music": "creative",
            "arts_crafts": "creative",

            "personal_trainer": "health_wellness",
            "yoga_studio": "health_wellness",
            "salon": "health_wellness",
            "spa": "health_wellness",
            "massage_therapy": "health_wellness",
            "physical_therapy": "health_wellness",

            "plumbing": "trades",
            "electrical": "trades",
            "hvac": "trades",
            "painting": "trades",
            "roofing": "trades",
            "landscaping": "trades",
            "cleaning_service": "trades",
            "general_contractor": "trades",

            "woodworking": "manufacturing",
            "custom_fabrication": "manufacturing",
            "apparel_production": "manufacturing",
            "food_manufacturing": "manufacturing",
        }

        self.naics_tag_mapping = {
            "722330": ["food_truck", "food_beverage"],
            "722513": ["fast_casual", "food_beverage"],
            "722515": ["coffee_shop", "bakery", "food_beverage"],
            "311811": ["bakery", "food_producer", "food_beverage"],
            "722310": ["catering", "food_beverage"],
            "312120": ["brewery", "food_beverage"],
            "312130": ["winery", "food_beverage"],
            "445230": ["food_producer", "food_beverage"],

            "448110": ["boutique_clothing", "retail"],
            "448120": ["boutique_clothing", "retail"],
            "448140": ["boutique_clothing", "retail"],
            "448310": ["jewelry", "retail"],
            "451110": ["sporting_goods", "retail"],
            "453220": ["gift_shop", "retail"],
            "444110": ["home_goods", "retail"],
            "442110": ["home_goods", "retail"],

            "236110": ["general_contractor", "trades"],
            "238210": ["electrical", "trades", "general_contractor"],
            "238220": ["plumbing", "hvac", "trades"],
            "238320": ["painting", "trades", "general_contractor"],
            "561720": ["cleaning_service", "trades"],
            "561730": ["landscaping", "trades"],

            "541110": ["legal", "professional_services"],
            "541211": ["accounting", "professional_services"],
            "541430": ["graphic_design", "creative"],
            "541511": ["IT_services", "professional_services"],
            "541613": ["marketing_agency", "professional_services"],
            "541810": ["marketing_agency", "professional_services"],

            "541921": ["photography", "creative"],
            "512110": ["videography", "creative"],
            "561920": ["event_planning", "professional_services"],

            "621340": ["physical_therapy", "health_wellness"],
            "713940": ["personal_trainer", "yoga_studio", "health_wellness"],
            "812111": ["salon", "health_wellness"],
            "812112": ["salon", "health_wellness"],
            "812199": ["spa", "massage_therapy", "health_wellness"],

            "321999": ["woodworking", "custom_fabrication", "manufacturing"],
            "339910": ["jewelry", "custom_fabrication", "manufacturing"],
            "315990": ["apparel_production", "manufacturing"],
        }

        self.opportunity_keyword_mapping = {
            "food_truck": ["food truck", "truck rally", "food truck festival"],
            "food_beverage": ["food festival", "food fair", "taste of", "culinary", "food expo", "restaurant week"],
            "fine_dining": ["fine dining", "gourmet", "tasting menu", "chef", "prix fixe"],
            "arts_crafts": ["art fair", "craft fair", "maker fair", "artisan market", "handmade", "maker market"],
            "jewelry": ["jewelry show", "gem show", "bead show", "jeweler"],
            "boutique_clothing": ["fashion show", "boutique", "clothing expo", "style expo"],
            "health_wellness": ["health fair", "wellness expo", "fitness expo", "yoga", "spa"],
            "home_goods": ["home show", "interior design", "furniture fair", "home improvement show"],
            "general_market": ["farmers market", "flea market", "vendor market", "community market", "swap meet"],
            "professional_services": ["business expo", "b2b conference", "professional development", "entrepreneur"],
            "event_planning": ["wedding expo", "event industry", "hospitality show", "bridal show"],
            "technology": ["tech expo", "startup", "innovation summit", "software", "digital"],
            "trades": ["contractor expo", "construction trade show", "home improvement expo"],
            "food_producer": ["local food", "farm to table", "producer network", "agriculture", "usda"],
            "creative": ["arts grant", "creative grant", "cultural arts", "arts council"],
        }

        self.adjacency_map = {
            "food_truck": ["fast_casual", "catering", "food_beverage", "general_market"],
            "fine_dining": ["catering", "food_beverage", "event_planning"],
            "catering": ["food_truck", "fine_dining", "fast_casual", "event_planning", "food_beverage"],
            "bakery": ["food_producer", "catering", "food_beverage", "general_market"],
            "coffee_shop": ["bakery", "food_beverage", "general_market"],
            "food_producer": ["bakery", "catering", "food_beverage", "general_market"],
            "brewery": ["food_beverage", "general_market", "food_truck"],

            "jewelry": ["arts_crafts", "boutique_clothing", "gift_shop", "home_goods"],
            "boutique_clothing": ["jewelry", "arts_crafts", "gift_shop", "home_goods"],
            "gift_shop": ["arts_crafts", "boutique_clothing", "jewelry"],

            "photography": ["videography", "event_planning", "creative"],
            "videography": ["photography", "event_planning", "creative", "marketing_agency"],
            "event_planning": ["photography", "videography", "catering", "marketing_agency"],
            "marketing_agency": ["professional_services", "graphic_design", "event_planning"],
            "graphic_design": ["marketing_agency", "creative", "photography"],
            "IT_services": ["professional_services", "technology"],

            "yoga_studio": ["personal_trainer", "health_wellness", "spa"],
            "personal_trainer": ["yoga_studio", "health_wellness"],
            "salon": ["spa", "massage_therapy", "health_wellness"],

            "plumbing": ["hvac", "electrical", "general_contractor", "trades"],
            "electrical": ["plumbing", "hvac", "general_contractor", "trades"],
            "landscaping": ["general_contractor", "cleaning_service"],

            "woodworking": ["custom_fabrication", "home_goods"],
            "apparel_production": ["boutique_clothing", "arts_crafts"],
        }

        self.service_model_mapping = {
            "fine_dining": "fine_dining",
            "restaurant": "service_in_person",
            "fast_casual": "fast_casual",
            "food_truck": "takeout",
            "coffee_shop": "takeout",
            "bakery": "retail_brick",
            "catering": "service_in_person",
            "brewery": "retail_brick",
            "winery": "retail_brick",
            "boutique_clothing": "retail_brick",
            "gift_shop": "retail_brick",
            "jewelry": "retail_brick",
            "sporting_goods": "retail_brick",
            "home_goods": "retail_brick",
            "marketing_agency": "service_remote",
            "accounting": "service_remote",
            "legal": "service_in_person",
            "IT_services": "service_remote",
            "consulting": "service_remote",
            "staffing": "service_in_person",
            "graphic_design": "service_remote",
            "photography": "service_in_person",
            "videography": "service_in_person",
            "event_planning": "service_in_person",
            "personal_trainer": "service_in_person",
            "yoga_studio": "service_in_person",
            "salon": "service_in_person",
            "spa": "service_in_person",
            "massage_therapy": "service_in_person",
            "woodworking": "manufacturing",
            "custom_fabrication": "manufacturing",
            "apparel_production": "manufacturing",
            "food_manufacturing": "manufacturing",
        }

        self.price_tier_mapping = {
            "fine_dining": "luxury",
            "restaurant": "mid",
            "fast_casual": "mid",
            "food_truck": "budget",
            "coffee_shop": "budget",
            "bakery": "mid",
            "catering": "premium",
            "brewery": "premium",
            "winery": "premium",
            "boutique_clothing": "premium",
            "gift_shop": "mid",
            "jewelry": "luxury",
            "marketing_agency": "premium",
            "consulting": "premium",
            "legal": "premium",
            "accounting": "mid",
            "IT_services": "premium",
            "spa": "premium",
            "salon": "mid",
        }

        self.customer_context_mapping = {
            "marketing_agency": "B2B",
            "consulting": "B2B",
            "legal": "B2B",
            "accounting": "B2B",
            "IT_services": "B2B",
            "staffing": "B2B",
            "food_truck": "B2C",
            "restaurant": "B2C",
            "coffee_shop": "B2C",
            "bakery": "B2C",
            "boutique_clothing": "B2C",
            "jewelry": "B2C",
            "catering": "hybrid",
            "event_planning": "hybrid",
            "photography": "hybrid",
            "videography": "hybrid",
        }

    def _normalize_text(self, text: str) -> str:

        if not text:
            return ""
        return text.lower().strip()
    
    def extract_opportunity_tags(
        self,
        title: str = "",
        notes: str = "",
        opportunity_type: str = "",
    ) -> List[str]:

        combined_text = self._normalize_text(
            f"{title} {notes} {opportunity_type}"
        )
        matched_tags = set()

        for tag, keywords in self.opportunity_keyword_mapping.items():
            for keyword in keywords:
                if keyword.lower() in combined_text:
                    matched_tags.add(tag)

        if not matched_tags:

            opp_type = self._normalize_text(opportunity_type)
            if opp_type == "rfp":
                matched_tags.add("professional_services")
            elif opp_type == "event":
                matched_tags.add("general_market")
            elif opp_type == "accelerator":
                matched_tags.add("professional_services")

        final_tags = list(matched_tags)

        service_metadata = self.extract_service_model_tags(
            final_tags
        )

        return {
            "tags": final_tags,
            "service_models": service_metadata["service_models"],
            "price_tiers": service_metadata["price_tiers"],
            "customer_contexts": service_metadata["customer_contexts"],
        }
    
    def extract_business_tags(self, onboarding: Dict[str, Any]) -> List[str]:

        matched_tags = set()
        naics = str(onboarding.get("naics_code", "") or "")

        keyword_fields = [
            onboarding.get("business_description", ""),
            onboarding.get("industry_description", ""),
            onboarding.get("main_products", ""),
        ]

        combined_text = self._normalize_text(" ".join(keyword_fields))

        # ----------------------------------------
        # SPECIAL CASE — 722511
        # ----------------------------------------

        if naics == "722511":

            avg_transaction_value = float(
                onboarding.get("avg_transaction_value", 0) or 0
            )

            upscale_keywords = [
                "fine dining",
                "upscale",
                "tasting",
                "prix fixe",
                "michelin",
                "white tablecloth",
            ]

            is_fine_dining = (
                avg_transaction_value > 50
                and any(
                    keyword in combined_text
                    for keyword in upscale_keywords
                )
            )

            if is_fine_dining:
                matched_tags.update([
                    "fine_dining",
                    "food_beverage",
                ])
            else:
                matched_tags.update([
                    "restaurant",
                    "food_beverage",
                ])

        # ----------------------------------------
        # DIRECT NAICS MATCH
        # ----------------------------------------

        elif naics in self.naics_tag_mapping:

            matched_tags.update(
                self.naics_tag_mapping[naics]
            )

        # ----------------------------------------
        # 3-DIGIT FALLBACK
        # ----------------------------------------

        elif len(naics) >= 3:

            naics_3 = naics[:3]

            if naics_3 == "722":
                matched_tags.add("food_beverage")

            elif naics_3 in ["236", "237", "238"]:
                matched_tags.add("trades")

            elif naics_3 == "541":
                matched_tags.add(
                    "professional_services"
                )

            elif naics_3 == "621":
                matched_tags.add(
                    "health_wellness"
                )

        # ----------------------------------------
        # 2-DIGIT FALLBACK
        # ----------------------------------------

        elif len(naics) >= 2:

            naics_2 = naics[:2]

            if naics_2 == "72":
                matched_tags.add("food_beverage")

            elif naics_2 == "54":
                matched_tags.add(
                    "professional_services"
                )

            elif naics_2 == "62":
                matched_tags.add(
                    "health_wellness"
                )

            elif naics_2 == "23":
                matched_tags.add("trades")

            elif naics_2 == "31":
                matched_tags.add("manufacturing")

        # ----------------------------------------
        # KEYWORD EXTRACTION
        # ----------------------------------------

        keyword_mapping = {
            "catering": "catering",
            "food truck": "food_truck",
            "coffee": "coffee_shop",
            "bakery": "bakery",
            "craft beer": "brewery",
            "wine": "winery",
            "photography": "photography",
            "video": "videography",
            "marketing": "marketing_agency",
            "graphic design": "graphic_design",
            "personal training": "personal_trainer",
            "yoga": "yoga_studio",
            "spa": "spa",
            "massage": "massage_therapy",
            "electrical": "electrical",
            "plumbing": "plumbing",
            "hvac": "hvac",
            "roofing": "roofing",
            "landscaping": "landscaping",
            "woodworking": "woodworking",
            "custom furniture": "woodworking",
            "jewelry": "jewelry",
            "boutique": "boutique_clothing",
        }

        for keyword, tag in keyword_mapping.items():

            if keyword in combined_text:
                matched_tags.add(tag)

        # ----------------------------------------
        # QB CATEGORY EXTRACTION
        # ----------------------------------------

        qb_categories = onboarding.get(
            "qb_product_service_categories",
            [],
        )

        for category in qb_categories:

            normalized_category = self._normalize_text(
                str(category)
            )

            for keyword, tag in keyword_mapping.items():

                if keyword in normalized_category:
                    matched_tags.add(tag)

        # ----------------------------------------
        # REVENUE LINE ITEM EXTRACTION
        # ----------------------------------------

        revenue_items = onboarding.get(
            "revenue_line_items",
            [],
        )

        for item in revenue_items:

            normalized_item = self._normalize_text(
                str(item)
            )

            for keyword, tag in keyword_mapping.items():

                if keyword in normalized_item:
                    matched_tags.add(tag)

        # ----------------------------------------
        # PAST EVENT EXTRACTION
        # ----------------------------------------

        past_events = onboarding.get(
            "past_events_participated",
            [],
        )

        for event in past_events:
            normalized_event = self._normalize_text(
                str(event)
            )
            if "food truck" in normalized_event:
                matched_tags.add("food_truck")

            if "craft fair" in normalized_event:
                matched_tags.add("arts_crafts")

            if "farmers market" in normalized_event:
                matched_tags.add("general_market")

        # ----------------------------------------
        # GROUP TAG DERIVATION
        # ----------------------------------------

        group_tags = set()

        for tag in matched_tags:
            group_tag = self.group_tag_mapping.get(tag)
            if group_tag:
                group_tags.add(group_tag)

        matched_tags.update(group_tags)

        return list(matched_tags)
    

    def extract_event_prestige_tier(self, text: str) -> str:

        normalized = self._normalize_text(text)

        luxury_keywords = ["black tie", "gala", "vip", "exclusive", "by invitation", "luxury", "couture", "fine dining showcase", "wine dinner", "tasting menu", "michelin"]
        premium_keywords = ["premium", "artisan", "curated", "specialty", "upscale", "craft", "boutique", "designer"]
        mid_keywords = ["community", "local", "neighborhood", "family-friendly", "street fair", "farmers market"]
        budget_keywords = ["discount", "dollar", "value", "swap meet", "flea market"]

        for keyword in luxury_keywords:
            if keyword in normalized:
                return "luxury"

        for keyword in premium_keywords:
            if keyword in normalized:
                return "premium"

        for keyword in mid_keywords:
            if keyword in normalized:
                return "mid"

        if "free admission" not in normalized:
            for keyword in budget_keywords:
                if keyword in normalized:
                    return "budget"

        return "unknown"
    
    def extract_event_audience(self, text: str) -> str:
        normalized = self._normalize_text(text)
        b2b_keywords = ["b2b", "trade show", "trade expo", "industry conference", "supplier", "wholesale buyer", "procurement", "corporate buyer", "industry professionals only"]
        b2c_keywords = ["public welcome", "family", "community", "consumer", "ticketed event", "open to the public"]
        has_b2b = any(keyword in normalized for keyword in b2b_keywords)
        has_b2c = any(keyword in normalized for keyword in b2c_keywords)

        if "open to both" in normalized or "industry and public" in normalized:
            return "hybrid"

        if has_b2b and has_b2c:
            return "hybrid"

        if has_b2b:
            return "b2b"

        if has_b2c:
            return "b2c"

        return "unknown"
    
    def extract_event_service_fit(self, text: str) -> List[str]:

        normalized = self._normalize_text(text)

        service_fit_mapping = {
            "fine dining": ["fine_dining", "catering"],
            "wine dinner": ["fine_dining", "catering"],
            "tasting": ["fine_dining", "catering"],
            "chef-driven": ["fine_dining", "catering"],
            "prix fixe": ["fine_dining", "catering"],

            "restaurant week": ["casual_dining", "fine_dining", "catering"],
            "chef showcase": ["casual_dining", "fine_dining", "catering"],
            "restaurant showcase": ["casual_dining", "fine_dining", "catering"],
            "dining event": ["casual_dining", "fine_dining", "catering"],

            "food truck": ["food_truck", "fast_casual"],
            "truck rally": ["food_truck", "fast_casual"],
            "mobile food": ["food_truck", "fast_casual"],

            "catering showcase": ["catering"],
            "corporate catering": ["catering"],
            "event catering": ["catering"],

            "farmers market": ["food_truck", "fast_casual", "casual_dining", "catering", "bakery_retail", "coffee_shop_retail", "brewery_taproom"],
            "street fair": ["food_truck", "fast_casual", "casual_dining", "catering", "bakery_retail", "coffee_shop_retail", "brewery_taproom"],
            "community event": ["food_truck", "fast_casual", "casual_dining", "catering", "bakery_retail", "coffee_shop_retail", "brewery_taproom"],
            "festival": ["food_truck", "fast_casual", "casual_dining", "catering", "bakery_retail", "coffee_shop_retail", "brewery_taproom"],
            "food festival": ["food_truck", "fast_casual", "casual_dining", "catering", "bakery_retail", "coffee_shop_retail", "brewery_taproom"],
            "taste of": ["food_truck", "fast_casual", "casual_dining", "catering", "bakery_retail", "coffee_shop_retail", "brewery_taproom"],

            "beer festival": ["brewery_taproom", "fast_casual"],
            "tap takeover": ["brewery_taproom", "fast_casual"],
            "brewery event": ["brewery_taproom", "fast_casual"],

            "wine festival": ["winery_tasting_room"],
            "vineyard tour": ["winery_tasting_room"],
            "wine tasting event": ["winery_tasting_room"],

            "retail showcase": ["sit_down_retail", "hybrid_retail"],
            "pop-up shop": ["sit_down_retail", "hybrid_retail"],
            "shopping event": ["sit_down_retail", "hybrid_retail"],
            "vendor market": ["sit_down_retail", "hybrid_retail"],

            "trade show": ["wholesale", "in_person_service", "manufacturing_direct"],
            "industry expo": ["wholesale", "in_person_service", "manufacturing_direct"],
            "b2b conference": ["wholesale", "in_person_service", "manufacturing_direct"],

            "wellness expo": ["in_person_service"],
            "fitness event": ["in_person_service"],
            "yoga festival": ["in_person_service"],

            "tech conference": ["remote_service", "in_person_service"],
            "innovation summit": ["remote_service", "in_person_service"],
            "developer meetup": ["remote_service", "in_person_service"],

            "maker fair": ["creative_hybrid", "sit_down_retail"],
            "artisan market": ["creative_hybrid", "sit_down_retail"],
            "craft fair": ["creative_hybrid", "sit_down_retail"],
        }

        matched = set()

        for keyword, tags in service_fit_mapping.items():

            if keyword in normalized:
                matched.update(tags)

        return list(matched)

    def calculate_jaccard_similarity(
        self,
        business_tags: List[str],
        opportunity_tags: List[str],
    ) -> float:

        business_set = set(business_tags)
        opportunity_set = set(opportunity_tags)

        union = business_set.union(opportunity_set)

        if not union:
            return 0.0

        intersection = business_set.intersection(opportunity_set)
        return round(len(intersection) / len(union),4)
    
    def has_adjacent_match(self, business_tags: List[str], opportunity_tags: List[str]) -> bool:

        business_set = set(business_tags)
        opportunity_set = set(opportunity_tags)

        for business_tag in business_set:
            adjacent_tags = self.adjacency_map.get(business_tag, [])

            for adjacent in adjacent_tags:
                if adjacent in opportunity_set:
                    return True

        for opportunity_tag in opportunity_set:
            adjacent_tags = self.adjacency_map.get(opportunity_tag, [])

            for adjacent in adjacent_tags:
                if adjacent in business_set:
                    return True

        return False
    

    def derive_group_tags(self, tags: List[str]) -> List[str]:

        derived = set(tags)

        for tag in tags:
            parent = self.group_tag_mapping.get(tag)

            if parent:
                derived.add(parent)

        return list(derived)

    def extract_service_model_tags(
        self,
        business_tags: List[str],
    ) -> Dict[str, Any]:

        service_models = set()
        price_tiers = set()
        customer_contexts = set()

        for tag in business_tags:

            service_model = self.service_model_mapping.get(tag)

            if service_model:
                service_models.add(service_model)

            price_tier = self.price_tier_mapping.get(tag)

            if price_tier:
                price_tiers.add(price_tier)

            customer_context = self.customer_context_mapping.get(tag)

            if customer_context:
                customer_contexts.add(customer_context)

        return {
            "service_models": sorted(list(service_models)),
            "price_tiers": sorted(list(price_tiers)),
            "customer_contexts": sorted(list(customer_contexts)),
        }

    def extract_full_opportunity_metadata(
        self,
        title: str = "",
        notes: str = "",
        opportunity_type: str = "",
    ) -> Dict[str, Any]:

        combined_text = f"{title} {notes} {opportunity_type}"

        opportunity_tags = self.extract_opportunity_tags(
            title=title,
            notes=notes,
            opportunity_type=opportunity_type,
        )

        opportunity_tags = self.derive_group_tags(
            opportunity_tags
        )

        return {
            "opportunity_tags": opportunity_tags,
            "event_prestige_tier": self.extract_event_prestige_tier(combined_text),
            "event_audience": self.extract_event_audience(combined_text),
            "event_service_fit": self.extract_event_service_fit(combined_text),
        }


tagging_service = TaggingService()