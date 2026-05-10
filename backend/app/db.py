"""
db.py — Motor async MongoDB connection pool.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings

# Global database instance
_db: AsyncIOMotorDatabase = None


async def connect_to_mongo() -> None:
    """Initialize MongoDB connection on app startup."""
    global _db
    client = AsyncIOMotorClient(settings.mongodb_url)
    _db = client[settings.mongodb_db]
    print(f"Connected to MongoDB: {settings.mongodb_db}")


async def close_mongo_connection() -> None:
    """Close MongoDB connection on app shutdown."""
    global _db
    if _db is not None:
        _db.client.close()
        print("Closed MongoDB connection")


async def get_db() -> AsyncIOMotorDatabase:
    """Dependency for getting DB instance in routes."""
    return _db


def get_database() -> AsyncIOMotorDatabase:
    """Return the shared MongoDB database instance for internal services."""
    return _db
