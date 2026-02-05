# app/schemas/auth.py
from pydantic import BaseModel
from typing import List


class SignupRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    id: str
    username: str
    roles: List[str]
    is_active: bool = False
