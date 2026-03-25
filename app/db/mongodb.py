from collections.abc import AsyncIterator

from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import PyMongoError

from app.core.config import get_settings

_client: AsyncIOMotorClient | None = None


def get_database() -> AsyncIOMotorDatabase:
    global _client
    settings = get_settings()
    if _client is None:
        _client = AsyncIOMotorClient(
            settings.mongodb_uri,
            connectTimeoutMS=settings.mongodb_server_selection_timeout_ms,
            socketTimeoutMS=settings.mongodb_server_selection_timeout_ms,
            serverSelectionTimeoutMS=settings.mongodb_server_selection_timeout_ms,
        )
    return _client[settings.mongodb_database]


async def verify_database_connection(db: AsyncIOMotorDatabase | None = None) -> AsyncIOMotorDatabase:
    database = db or get_database()
    try:
        await database.command("ping")
    except PyMongoError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from exc
    return database


async def close_database() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


async def database_lifespan() -> AsyncIterator[None]:
    get_database()
    try:
        yield
    finally:
        await close_database()
