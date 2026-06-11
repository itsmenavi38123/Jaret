import os
from pymongo import MongoClient


class SyncMemoryService:

    def __init__(self):
        self.client = MongoClient(
            os.getenv("MONGO_URI")
        )

        self.db = self.client[
            os.getenv("MONGO_DB_NAME")
        ]

        self.collection = self.db[
            "customer_memory"
        ]

    def get_by_path(
        self,
        path: str
    ):
        return self.collection.find_one(
            {
                "path": path,
                "outdated": False
            }
        )

    def get_by_path_prefix(
        self,
        path_prefix: str,
        limit: int = 100
    ):
        return list(
            self.collection.find(
                {
                    "path": {
                        "$regex": f"^{path_prefix}"
                    },
                    "outdated": False
                }
            ).limit(limit)
        )

    def get_memory_by_id(
        self,
        memory_id
    ):
        return self.collection.find_one(
            {
                "_id": memory_id
            }
        )

    def path_exists(
        self,
        path: str
    ):
        return self.collection.find_one(
            {
                "path": path,
                "outdated": False
            }
        )

    def create_memory(
        self,
        data: dict
    ):
        return self.collection.insert_one(
            data
        )

    def update_memory(
        self,
        filter_data: dict,
        update_data: dict
    ):
        return self.collection.update_one(
            filter_data,
            update_data
        )

    def delete_memory(
        self,
        filter_data: dict
    ):
        return self.collection.update_one(
            filter_data,
            {
                "$set": {
                    "outdated": True
                }
            }
        )


sync_memory_service = SyncMemoryService()