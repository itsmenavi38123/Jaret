from app.db import get_collection
from app.models.peer_teaser import PeerTeaser
from app.services.claude_service import claude_service
from datetime import datetime, timezone
import uuid
from typing import Optional

class PeerTeaserGenerationService:
    def __init__(self):
        self.playbook_col = get_collection("org_playbook")
        self.memory_col = get_collection("customer_memory")
        self.teaser_col = get_collection("peer_teasers")

    async def generate_teasers_from_playbook(self, proposed_by_name: str = "dreaming pass") -> int:
        """
        Scans active cross-customer patterns from the Org Playbook and generates
        anonymized Peer Teasers in 'review' status, tracing back to a real customer.
        """
        # Fetch active playbooks
        cursor = self.playbook_col.find({"outdated": False})
        playbooks = await cursor.to_list(length=None)
        
        created_count = 0
        
        for playbook in playbooks:
            path = playbook.get("path")
            if not path:
                continue
                
            # Check if we already have a teaser for this playbook path
            existing = await self.teaser_col.find_one({"supporting_data.source_playbook_path": path})
            if existing:
                continue
                
            # Retrieve source memories to trace back to a real customer
            consolidated_from = playbook.get("consolidated_from", [])
            if not consolidated_from:
                continue
                
            # Find the first contributing memory to identify the source customer
            first_memory_id = consolidated_from[0]
            memory_doc = await self.memory_col.find_one({"_id": first_memory_id})
            if not memory_doc:
                continue
                
            source_user_id = memory_doc.get("user_id")
            if not source_user_id:
                continue
                
            # Call Claude to anonymize and format the insight
            system_prompt = """
You are the LightSignal Dreaming Engine.

Your task is to generate a Peer Teaser from a cross-customer business playbook insight.
A Peer Teaser is a short, anonymized, one-sentence motivator shown to new owners during onboarding to encourage them to complete their profiles.

Rules:
1. ANTI-HALLUCINATION: The teaser must be a genuinely anonymized version of the provided insight. Never invent false details not implied by the insight.
2. ANONYMIZATION: Make it completely anonymous. Use general phrases like "A restaurant near you...", "A business near you...", "A shop like yours...", or "A cafe near you...". Never include real business names or specific identifying details.
3. FORMAT: Keep it to a single, compelling, active sentence. For example:
   - "A restaurant near you found $3,200/mo in an overpaid produce vendor."
   - "A shop like yours spotted a slow-paying account worth $1,900 before it went bad."
   - "A cafe near you found its Tuesdays were quietly its best margin day."
4. CATEGORY: Classify the teaser into one of these onboarding sections: "Expenses", "Financials".
   - Choose "Expenses" if the insight relates to vendors, bills, expenses, subscriptions, or direct costs.
   - Choose "Financials" for margins, revenue, sales, scheduling, accounts receivable, bookkeeping, or general metrics.

Return STRICT JSON ONLY matching this format:
{
  "teaser_text": "Single teaser sentence here",
  "onboarding_section": "Expenses|Financials"
}
"""
            try:
                result = await claude_service.json_completion(
                    system_prompt=system_prompt,
                    user_content={"playbook_insight": playbook.get("content")},
                    temperature=0.2,
                    max_tokens=500
                )
                
                teaser_text = result.get("teaser_text")
                onboarding_section = result.get("onboarding_section", "Financials")
                
                if not teaser_text:
                    continue
                    
                # Create and insert the Peer Teaser
                teaser_doc = PeerTeaser(
                    source_customer_id=source_user_id,
                    verified_anonymized=True,
                    status="review",
                    teaser_text=teaser_text,
                    onboarding_section=onboarding_section,
                    proposed_by=proposed_by_name,
                )
                
                # Attach source metadata
                insert_data = teaser_doc.model_dump(by_alias=True)
                insert_data["supporting_data"] = {
                    "source_playbook_path": path,
                    "source_playbook_id": playbook.get("_id") or playbook.get("id")
                }
                
                await self.teaser_col.insert_one(insert_data)
                created_count += 1
                
            except Exception as e:
                print(f"[Teaser Generation] Error generating teaser for playbook {path}: {e}")
                
        return created_count
