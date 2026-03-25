from fastapi import HTTPException, status

from app.schemas.iot import IoTDataIn


class IoTService:
    def __init__(self, db) -> None:
        self.collection = db["iot_data"]

    async def ensure_indexes(self) -> None:
        await self.collection.create_index([("user_id", 1), ("timestamp", -1)])

    async def ingest(self, payload: IoTDataIn) -> dict:
        document = payload.model_dump()
        await self.collection.insert_one(document)
        return document

    async def latest(self, user_id: str) -> dict:
        document = await self.collection.find_one(
            {"user_id": user_id},
            projection={"_id": 0},
            sort=[("timestamp", -1)],
        )
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No IoT data found")
        return document

    async def history(self, user_id: str, limit: int) -> list[dict]:
        cursor = self.collection.find({"user_id": user_id}, {"_id": 0}).sort("timestamp", -1).limit(limit)
        return [item async for item in cursor]
