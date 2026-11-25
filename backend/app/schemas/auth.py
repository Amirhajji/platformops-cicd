from datetime import datetime

from pydantic import BaseModel, Field, field_serializer
from typing_extensions import Literal

from app.services.timeline import iso

Role = Literal["admin", "viewer"]
NO_NUL = r"^[^\x00]+$"  # PostgreSQL text cannot contain NUL


class LoginRequest(BaseModel):
    username: str = Field(max_length=64, pattern=NO_NUL)
    password: str = Field(max_length=128)


class LoginResponse(BaseModel):
    token: str
    role: Role


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    password: str = Field(min_length=8, max_length=128)
    role: Role


class UserOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    username: str
    role: Role
    created_at: datetime

    @field_serializer("created_at")
    def _created_at(self, value: datetime) -> str:
        return iso(value)
