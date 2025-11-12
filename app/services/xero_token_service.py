from datetime import datetime
from typing import Optional

from bson import ObjectId

from app.db import get_collection
from app.models.xero.token import XeroToken, XeroTokenCreate, XeroTokenUpdate


class XeroTokenService:
    def __init__(self) -> None:
        self.collection = get_collection("xero_tokens")

    async def create_token(self, token_data: XeroTokenCreate) -> XeroToken:
        now = datetime.utcnow()
        payload = token_data.dict()
        payload["_id"] = str(ObjectId())
        payload["created_at"] = now
        payload["updated_at"] = now
        payload["is_active"] = True

        await self.collection.update_many(
            {"user_id": token_data.user_id, "tenant_id": token_data.tenant_id},
            {"$set": {"is_active": False}}
        )

        await self.collection.insert_one(payload)
        return XeroToken(**payload)

    async def get_token_by_user_and_tenant(self, user_id: str, tenant_id: str) -> Optional[XeroToken]:
        doc = await self.collection.find_one({
            "user_id": user_id,
            "tenant_id": tenant_id,
            "is_active": True,
        })
        return XeroToken(**doc) if doc else None

    async def get_tokens_by_user(self, user_id: str) -> list[XeroToken]:
        cursor = self.collection.find({"user_id": user_id}).sort("created_at", -1)
        tokens: list[XeroToken] = []
        async for doc in cursor:
            tokens.append(XeroToken(**doc))
        return tokens

    async def update_token(self, token_id: str, update: XeroTokenUpdate) -> Optional[XeroToken]:
        update_dict = update.dict(exclude_unset=True)
        result = await self.collection.update_one({"_id": token_id}, {"$set": update_dict})
        if result.modified_count:
            doc = await self.collection.find_one({"_id": token_id})
            return XeroToken(**doc)
        return None

    async def deactivate_token(self, token_id: str) -> bool:
        result = await self.collection.update_one(
            {"_id": token_id},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0


xero_token_service = XeroTokenService()
