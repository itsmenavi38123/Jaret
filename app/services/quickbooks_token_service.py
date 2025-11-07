import json
from datetime import datetime
from typing import Optional
from bson import ObjectId
from app.db import get_collection
from app.models.quickbooks.token import QuickBooksToken, QuickBooksTokenCreate, QuickBooksTokenUpdate

class QuickBooksTokenService:
    def __init__(self):
        self.collection = get_collection("quickbooks_tokens")

    async def create_token(self, token_data: QuickBooksTokenCreate) -> QuickBooksToken:
        """Create a new QuickBooks token record"""
        now = datetime.utcnow()
        token_dict = token_data.dict()
        token_dict["_id"] = str(ObjectId())
        token_dict["created_at"] = now
        token_dict["updated_at"] = now
        token_dict["is_active"] = True
        
        # Deactivate any existing tokens for this user and realm
        await self.collection.update_many(
            {"user_id": token_data.user_id, "realm_id": token_data.realm_id},
            {"$set": {"is_active": False}}
        )
        
        await self.collection.insert_one(token_dict)
        return QuickBooksToken(**token_dict)

    async def get_token_by_user_and_realm(self, user_id: str, realm_id: str) -> Optional[QuickBooksToken]:
        """Get the active token for a user and realm"""
        token_doc = await self.collection.find_one(
            {"user_id": user_id, "realm_id": realm_id, "is_active": True}
        )
        if token_doc:
            return QuickBooksToken(**token_doc)
        return None

    async def get_tokens_by_user(self, user_id: str) -> list[QuickBooksToken]:
        """Get all tokens for a user"""
        cursor = self.collection.find({"user_id": user_id}).sort("created_at", -1)
        tokens = []
        async for token_doc in cursor:
            tokens.append(QuickBooksToken(**token_doc))
        return tokens

    async def update_token(self, token_id: str, update_data: QuickBooksTokenUpdate) -> Optional[QuickBooksToken]:
        """Update an existing token"""
        update_dict = update_data.dict(exclude_unset=True)
        update_dict["updated_at"] = datetime.utcnow()
        
        result = await self.collection.update_one(
            {"_id": token_id},
            {"$set": update_dict}
        )
        
        if result.modified_count > 0:
            updated_token = await self.collection.find_one({"_id": token_id})
            return QuickBooksToken(**updated_token)
        return None

    async def deactivate_token(self, token_id: str) -> bool:
        """Deactivate a token"""
        result = await self.collection.update_one(
            {"_id": token_id},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0

    async def extract_user_from_id_token(self, id_token: str) -> Optional[str]:
        """Extract user information from JWT id_token"""
        try:
            # JWT tokens have 3 parts separated by dots
            parts = id_token.split('.')
            if len(parts) != 3:
                return None
            
            # Decode the payload (second part)
            import base64
            payload = parts[1]
            # Add padding if needed
            payload += '=' * (4 - len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload)
            token_data = json.loads(decoded)
            
            # Extract subject (user ID) from token
            return token_data.get('sub')
        except Exception:
            return None

# Create a singleton instance
quickbooks_token_service = QuickBooksTokenService()