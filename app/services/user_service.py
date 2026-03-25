from fastapi import HTTPException, status
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.schemas.users import UserCreate, UserUpdate


class UserService:
    def __init__(self, db) -> None:
        self.collection = db["users"]

    async def ensure_indexes(self) -> None:
        await self.collection.create_index("user_id", unique=True)

    async def create_user(self, payload: UserCreate) -> dict:
        document = payload.model_dump()
        try:
            await self.collection.insert_one(document)
        except DuplicateKeyError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists") from exc
        return document

    async def update_user(self, user_id: str, payload: UserUpdate) -> dict:
        update_doc = payload.model_dump(exclude_none=True)
        if not update_doc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided")

        document = await self.collection.find_one_and_update(
            {"user_id": user_id},
            {"$set": update_doc},
            return_document=ReturnDocument.AFTER,
        )
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        document.pop("_id", None)
        return document

    async def get_user(self, user_id: str) -> dict:
        document = await self.collection.find_one({"user_id": user_id}, {"_id": 0})
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return document

    async def validate_active_user(self, user_id: str) -> dict:
        document = await self.get_user(user_id)
        if document["status"] != "active":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is inactive")
        return document
