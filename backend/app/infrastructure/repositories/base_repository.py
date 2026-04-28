"""
infrastructure/repositories/base_repository.py — Base repository class.
"""

from typing import TypeVar, Generic, List, Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Abstract base repository for MongoDB CRUD operations.
    Implements common async patterns.
    """

    def __init__(self, collection: AsyncIOMotorCollection, model_class: type = None):
        self.collection = collection
        self.model_class = model_class

    async def create(self, document: Dict[str, Any]) -> str:
        """Insert one document, return inserted ID."""
        result = await self.collection.insert_one(document)
        return str(result.inserted_id)

    async def create_many(self, documents: List[Dict[str, Any]]) -> List[str]:
        """Insert multiple documents, return inserted IDs."""
        result = await self.collection.insert_many(documents)
        return [str(id_) for id_ in result.inserted_ids]

    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find single document matching query — _id excluded."""
        return await self.collection.find_one(query, {"_id": 0})

    async def find_many(self, query: Dict[str, Any], limit: int = 100, skip: int = 0) -> List[Dict[str, Any]]:
        """Find multiple documents matching query — _id excluded."""
        cursor = self.collection.find(query, {"_id": 0}).limit(limit).skip(skip)
        return await cursor.to_list(length=limit)

    async def find_all(self) -> List[Dict[str, Any]]:
        """Find all documents — _id excluded."""
        cursor = self.collection.find({}, {"_id": 0})
        return await cursor.to_list(length=None)

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False) -> int:
        """Update single document, return matched count."""
        result = await self.collection.update_one(query, {"$set": update}, upsert=upsert)
        return result.matched_count

    async def update_many(self, query: Dict[str, Any], update: Dict[str, Any]) -> int:
        """Update multiple documents, return matched count."""
        result = await self.collection.update_many(query, {"$set": update})
        return result.matched_count

    async def delete_one(self, query: Dict[str, Any]) -> int:
        """Delete single document, return deleted count."""
        result = await self.collection.delete_one(query)
        return result.deleted_count

    async def delete_many(self, query: Dict[str, Any]) -> int:
        """Delete multiple documents, return deleted count."""
        result = await self.collection.delete_many(query)
        return result.deleted_count

    async def count(self, query: Dict[str, Any] = None) -> int:
        """Count documents matching query."""
        if query is None:
            query = {}
        return await self.collection.count_documents(query)

    async def exists(self, query: Dict[str, Any]) -> bool:
        """Check if document exists."""
        result = await self.collection.find_one(query, projection={"_id": 1})
        return result is not None
