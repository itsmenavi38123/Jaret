import json
from datetime import datetime
from typing import Optional
from bson import ObjectId
from app.db import get_collection
from app.models.facebook.token import FacebookToken, FacebookTokenCreate, FacebookTokenUpdate

class FacebookTokenService:
    def __init__(self):
        self.collection = get_collection("facebook_tokens")

    async def create_token(self, token_data: FacebookTokenCreate) -> FacebookToken:
        """Create or update the Facebook token record for this user/page."""
        now = datetime.utcnow()
        token_payload = token_data.dict()

        existing = await self.collection.find_one(
            {"user_id": token_data.user_id, "page_id": token_data.page_id},
            sort=[("updated_at", -1)],
        )

        if existing:
            update_fields = {
                **token_payload,
                "updated_at": now,
                "is_active": True,
                "created_at": existing.get("created_at", now),
            }
            await self.collection.update_one({"_id": existing["_id"]}, {"$set": update_fields})
            # Remove duplicates
            await self.collection.delete_many({
                "user_id": token_data.user_id,
                "page_id": token_data.page_id,
                "_id": {"$ne": existing["_id"]},
            })
            refreshed = await self.collection.find_one({"_id": existing["_id"]})
            return FacebookToken(**refreshed)

        token_payload["_id"] = str(ObjectId())
        token_payload["created_at"] = now
        token_payload["updated_at"] = now
        token_payload["is_active"] = True

        await self.collection.insert_one(token_payload)
        return FacebookToken(**token_payload)

    async def get_token_by_user_and_page(self, user_id: str, page_id: str) -> Optional[FacebookToken]:
        """Get the active token for a user and page"""
        token_doc = await self.collection.find_one(
            {"user_id": user_id, "page_id": page_id, "is_active": True}
        )
        if token_doc:
            return FacebookToken(**token_doc)
        return None

    async def get_tokens_by_user(self, user_id: str) -> list[FacebookToken]:
        """Get all tokens for a user"""
        cursor = self.collection.find({"user_id": user_id}).sort("created_at", -1)
        tokens = []
        async for token_doc in cursor:
            tokens.append(FacebookToken(**token_doc))
        return tokens

    async def update_token(self, token_id: str, update_data: FacebookTokenUpdate) -> Optional[FacebookToken]:
        """Update an existing token"""
        update_dict = update_data.dict(exclude_unset=True)
        update_dict["updated_at"] = datetime.utcnow()
        
        result = await self.collection.update_one(
            {"_id": token_id},
            {"$set": update_dict}
        )
        
        if result.modified_count > 0:
            updated_token = await self.collection.find_one({"_id": token_id})
            return FacebookToken(**updated_token)
        return None

    async def deactivate_token(self, token_id: str) -> bool:
        """Deactivate a token"""
        result = await self.collection.update_one(
            {"_id": token_id},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0

    async def delete_token(self, token_id: str) -> bool:
        """Permanently delete a Facebook token by ID."""
        result = await self.collection.delete_one({"_id": token_id})
        return result.deleted_count > 0

    async def delete_tokens_by_user(self, user_id: str) -> bool:
        """Permanently delete all Facebook tokens for a user."""
        result = await self.collection.delete_many({"user_id": user_id})
        return result.deleted_count > 0

    async def disconnect_and_delete_tokens_by_user(self, user_id: str) -> bool:
        """Revoke permissions on Facebook and permanently delete user's Facebook tokens from MongoDB."""
        from app.services.facebook_service import facebook_service
        
        tokens = await self.get_tokens_by_user(user_id)
        active_tokens = [token for token in tokens if token.is_active]
        
        for token in active_tokens:
            try:
                await facebook_service.revoke_permissions(token.access_token)
            except Exception as ex:
                print(f"Failed to revoke Facebook token programmatically: {ex}")
                
        result = await self.collection.delete_many({"user_id": user_id})
        return result.deleted_count > 0

facebook_token_service = FacebookTokenService()
