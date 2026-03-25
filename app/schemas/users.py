from typing import Literal

from pydantic import BaseModel, Field

UserStatus = Literal["active", "inactive"]


class UserBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    status: UserStatus


class UserCreate(UserBase):
    user_id: str = Field(min_length=1, max_length=50)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    status: UserStatus | None = None


class UserResponse(UserCreate):
    pass
