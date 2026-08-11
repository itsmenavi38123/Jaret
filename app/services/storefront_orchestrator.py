import re
from datetime import datetime
import uuid
from app.db import get_collection
from app.services.storefront_agent_service import storefront_agent_service
from app.models.customer_memory import CustomerMemory
from app.services.customer_memory_service import CustomerMemoryService


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "location"


def get_active_locations(profile: dict) -> list[dict]:
    """
    Reads a business profile's locations[] array (per multi_location_handling.md),
    checking onboarding_data first then the top-level field (both patterns exist
    elsewhere in this codebase, e.g. dia_orchestrator.py reads the top-level form).
    Returns one dict per active location: {location_id, business_name, address}.
    Falls back to the single business_name/address pair (as a single implicit
    location) when locations[] is absent/empty, preserving prior single-location
    behavior.
    """
    onboarding = profile.get("onboarding_data", {}) or {}
    raw_locations = onboarding.get("locations") or profile.get("locations") or []

    active = [
        loc for loc in raw_locations
        if isinstance(loc, dict) and loc.get("status", "active") == "active"
    ]

    if not active:
        business_name = onboarding.get("business_name") or onboarding.get("company_name")
        address = onboarding.get("address")
        if business_name and address:
            return [{
                "location_id": "primary",
                "business_name": business_name,
                "address": address,
            }]
        return []

    locations = []
    for loc in active:
        name = loc.get("name") or onboarding.get("business_name") or onboarding.get("company_name")
        address = loc.get("address")
        if not name or not address:
            continue
        location_id = loc.get("id") or loc.get("location_id") or _slugify(f"{name}_{address}")
        locations.append({
            "location_id": location_id,
            "business_name": name,
            "address": address,
        })
    return locations


class StorefrontOrchestrator:
    def __init__(self):
        self.agent = storefront_agent_service
        self.memory_service = CustomerMemoryService()

    async def run_for_location(
        self,
        user_id: str,
        business_name: str,
        address: str,
        location_id: str,
    ):
        """
        Runs the Storefront Agent analysis for a specific location, 
        supersedes old reads, and writes the new analysis findings 
        as learnings into MongoDB customer memory.
        """
        analysis = await self.agent.analyze_location(
            business_name=business_name,
            address=address,
            user_id=user_id,
            location_id=location_id,
        )

        if analysis and analysis.get("result") != "insufficient_coverage":
            # Write findings to MongoDB Customer Memory
            await self.write_learnings(
                user_id=user_id,
                location_id=location_id,
                analysis=analysis
            )

        return analysis

    async def write_learnings(
        self,
        user_id: str,
        location_id: str,
        analysis: dict,
    ) -> str:
        """
        Saves the structured analysis output to customer_memory.
        """
        path = f"/memories/customer_{user_id}/storefront_location_learnings/{location_id}"
        memory_id = str(uuid.uuid4())
        
        # Extract confidence rating from result
        confidence = "medium"
        if "module_1_presentation" in analysis:
            flags = analysis["module_1_presentation"].get("pass2_fit_flags", [])
            if flags:
                confidence = flags[0].get("confidence", "medium")
        elif "module_2_vitality" in analysis:
            confidence = analysis["module_2_vitality"].get("confidence", "medium")
            
        memory = CustomerMemory(
            id=memory_id,
            user_id=user_id,
            path=path,
            observation_type="pattern",
            content=f"Storefront and location assessment for location: {location_id}.",
            agent_name="storefront_agent",
            session_id=str(uuid.uuid4()),
            supporting_data=analysis,
            confidence=confidence,
            tags=["storefront", "location_vitality"],
            pinned=False,
            outdated=False,
            authority="storefront_agent",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Mark previous reads for this location as superseded
        await self.supersede_previous_reads(user_id, location_id, memory_id)
        
        # Create/Save the new learning record
        await self.memory_service.create_memory(memory)
        return memory_id

    async def supersede_previous_reads(
        self,
        user_id: str,
        location_id: str,
        new_memory_id: str
    ):
        """
        Queries and updates existing active location reads to mark them outdated.
        """
        path = f"/memories/customer_{user_id}/storefront_location_learnings/{location_id}"
        collection = get_collection("customer_memory")
        
        # Find active records
        cursor = collection.find({
            "user_id": user_id,
            "path": path,
            "outdated": False
        })
        
        async for doc in cursor:
            old_id = doc["_id"]
            await collection.update_one(
                {"_id": old_id},
                {
                    "$set": {
                        "outdated": True,
                        "date_marked_outdated": datetime.utcnow(),
                        "superseded_by": new_memory_id,
                        "updated_at": datetime.utcnow()
                    }
                }
            )

storefront_orchestrator = StorefrontOrchestrator()

async def handle_profile_classified_event(payload: dict):
    """
    Subscribes to business.profile_classified event.
    Automatically triggers storefront & location analysis.
    """
    business_id = payload.get("business_id")
    if not business_id:
        return
        
    try:
        profile = await get_collection("business_profiles").find_one({"user_id": business_id})
        if profile:
            # One job per active location (multi_location_handling.md / acceptance criteria B8)
            for location in get_active_locations(profile):
                await storefront_orchestrator.run_for_location(
                    user_id=business_id,
                    business_name=location["business_name"],
                    address=location["address"],
                    location_id=location["location_id"]
                )
    except Exception as ex:
        print(f"Storefront orchestrator auto-trigger failed: {ex}")

from app.services.internal_event_bus import internal_event_bus
internal_event_bus.subscribe(
    "business.profile_classified",
    handle_profile_classified_event
)