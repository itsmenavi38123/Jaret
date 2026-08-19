# backend/app/services/dashboard_ask_service.py
"""
Dashboard Ask AI Advisor Service
Powers the whole-business advisor chatbot on the Dashboard dock.
Integrates Claude via claude_service and persists chat transcripts to MongoDB.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4
import re

from app.db import get_collection
from app.services.claude_service import claude_service
from app.services.quickbooks_financial_service import quickbooks_financial_service


class DashboardAskService:
    """
    Whole-business Ask AI Advisor.
    Acts as a $500/hr, 30-year-tenured business advisor with full platform knowledge.
    """

    def __init__(self):
        self.chats_collection_name = "dashboard_ask_chats"

    def _get_chats_collection(self):
        return get_collection(self.chats_collection_name)

    async def ask_advisor(
        self,
        user_id: str,
        question: str,
        surface: str = "dashboard_ask",
        chat_id: Optional[str] = None,
        chat_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Processes a user question with Claude, incorporates financial context,
        and saves the turn to MongoDB.
        """
        # Fetch baseline financial metrics for context
        try:
            kpis_data = await quickbooks_financial_service.get_dashboard_kpis(user_id)
        except Exception as e:
            kpis_data = {}

        # Fetch business profile context if available
        business_profiles = get_collection("business_profiles")
        profile_doc = await business_profiles.find_one({"user_id": user_id}) or {}
        onboarding_data = profile_doc.get("onboarding_data", {})
        business_name = onboarding_data.get("company_name") or onboarding_data.get("business_name") or "Your Business"
        industry = onboarding_data.get("industry") or onboarding_data.get("industry_description") or "General Business"

        # System prompt following Dashboard Ask AI spec
        system_prompt = f"""You are LightSignal's Ask AI Advisor — a $500/hr, 30-year-tenured advisor who has known this owner's business ({business_name}, Industry: {industry}) for decades.

BUSINESS REALITY & FINANCIAL CONTEXT (Grounded data):
- Revenue MTD: ${kpis_data.get('revenue_mtd', 0):,.2f}
- Net Margin: {kpis_data.get('net_margin_pct', 0) * 100:.1f}%
- Cash Balance: ${kpis_data.get('cash', 0):,.2f}
- Cash Runway: {kpis_data.get('runway_months', 0):.1f} months

CORE ADVISOR RULES:
1. Whole-Business Perspective: Answer questions through a practical business owner lens. Synthesize financial, operational, demand, and risk factors into ONE clear, advisor-grade answer.
2. Complete & Anticipatory: Provide who/what/when/why/how-much in your response. Never leave the owner guessing.
3. Concise & Glance-Appropriate: Keep responses short-to-medium (2-4 clear paragraphs/bullets maximum). Concise full answer, not a shallow one.
4. Relevance Guard: If a question is completely unrelated to business operations ("should I use wipes today?"), respond briefly: "How does that relate to your business?"
5. Grounded & Anti-Hallucination: Use the business context provided. Do not fabricate facts or numbers.
6. Optional Explore Pointer: When relevant, end with one optional closing line inviting them to explore ongoing tracking (e.g. "For the ongoing view on this, check the Financial Overview tab.").
"""

        # Format user message content including conversation history if available
        formatted_messages = []
        if chat_history:
            for item in chat_history[-6:]:  # Keep last 6 turns for context
                role = item.get("role") or item.get("sender")
                text = item.get("text") or item.get("content") or ""
                if role in ["q", "user"]:
                    formatted_messages.append(f"Owner: {text}")
                elif role in ["a", "assistant", "advisor"]:
                    formatted_messages.append(f"Advisor: {text}")

        formatted_messages.append(f"Owner: {question}")
        conversation_prompt = "\n\n".join(formatted_messages)

        # Call Claude
        answer = await claude_service.text_completion(
            system_prompt=system_prompt,
            user_content=conversation_prompt,
            temperature=0.3,
            max_tokens=800,
        )

        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        chats_col = self._get_chats_collection()

        # Check if updating an existing chat thread or creating a new one
        existing_chat = None
        if chat_id:
            existing_chat = await chats_col.find_one({"_id": chat_id, "user_id": user_id})

        if existing_chat:
            target_chat_id = existing_chat["_id"]
            new_messages = existing_chat.get("messages", [])
            new_messages.append({"role": "q", "text": question, "ts": now_iso})
            new_messages.append({"role": "a", "text": str(answer), "ts": now_iso})

            await chats_col.update_one(
                {"_id": target_chat_id},
                {
                    "$set": {
                        "messages": new_messages,
                        "updated_at": now,
                    }
                },
            )
        else:
            target_chat_id = str(uuid4())
            title = question[:60] + "..." if len(question) > 60 else question
            new_messages = [
                {"role": "q", "text": question, "ts": now_iso},
                {"role": "a", "text": str(answer), "ts": now_iso},
            ]
            doc = {
                "_id": target_chat_id,
                "user_id": user_id,
                "title": title,
                "surface": surface,
                "messages": new_messages,
                "created_at": now,
                "updated_at": now,
            }
            await chats_col.insert_one(doc)

        return {
            "chat_id": target_chat_id,
            "title": existing_chat["title"] if existing_chat else title,
            "question": question,
            "answer": str(answer),
            "created_at": now_iso,
        }

    async def list_chats(
        self,
        user_id: str,
        query: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        List a user's past chat conversations.
        Supports content keyword search across title and message text.
        """
        chats_col = self._get_chats_collection()
        filter_doc: Dict[str, Any] = {"user_id": user_id}

        if query and query.strip():
            keyword_regex = re.compile(re.escape(query.strip()), re.IGNORECASE)
            filter_doc["$or"] = [
                {"title": keyword_regex},
                {"messages.text": keyword_regex},
            ]

        cursor = chats_col.find(filter_doc).sort("updated_at", -1).limit(limit)
        chat_docs = await cursor.to_list(length=limit)

        result = []
        for doc in chat_docs:
            created_at = doc.get("created_at")
            created_at_str = created_at.isoformat() if isinstance(created_at, datetime) else str(created_at)
            
            updated_at = doc.get("updated_at") or created_at
            updated_at_str = updated_at.isoformat() if isinstance(updated_at, datetime) else str(updated_at)

            messages = doc.get("messages", [])
            last_message = messages[-1]["text"] if messages else ""

            result.append(
                {
                    "id": doc["_id"],
                    "title": doc.get("title", "Untitled Chat"),
                    "created_at": created_at_str,
                    "updated_at": updated_at_str,
                    "message_count": len(messages),
                    "last_message": last_message,
                }
            )

        return result

    async def get_chat_thread(self, user_id: str, chat_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve full message transcript for a specific chat ID.
        """
        chats_col = self._get_chats_collection()
        doc = await chats_col.find_one({"_id": chat_id, "user_id": user_id})
        if not doc:
            return None

        created_at = doc.get("created_at")
        created_at_str = created_at.isoformat() if isinstance(created_at, datetime) else str(created_at)

        return {
            "id": doc["_id"],
            "title": doc.get("title", "Untitled Chat"),
            "surface": doc.get("surface", "dashboard_ask"),
            "created_at": created_at_str,
            "messages": doc.get("messages", []),
        }


# Singleton instance
dashboard_ask_service = DashboardAskService()
