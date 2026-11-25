from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.db import get_session
from app.db.models import User
from app.schemas.auth import LoginRequest, LoginResponse, UserOut
from app.services import users

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, session: Session = Depends(get_session)) -> Any:
    token, role = users.login(session, body.username, body.password)
    return {"token": token, "role": role}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> Any:
    return user
