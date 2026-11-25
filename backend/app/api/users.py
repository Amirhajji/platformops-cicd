"""User management, admin only."""
from typing import Any, List

from fastapi import APIRouter, Depends, Path, Response
from sqlalchemy.orm import Session

from app.api.deps import MAX_INT, admin_user
from app.core.db import get_session
from app.db.models import User
from app.schemas.auth import UserCreate, UserOut
from app.services import users

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(admin_user)])


@router.get("", response_model=List[UserOut])
def get_users(session: Session = Depends(get_session)) -> Any:
    return users.list_users(session)


@router.post("", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, session: Session = Depends(get_session)) -> Any:
    return users.create_user(session, body.username, body.password, body.role)


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int = Path(..., ge=1, le=MAX_INT),
                current: User = Depends(admin_user),
                session: Session = Depends(get_session)) -> Response:
    users.delete_user(session, user_id, current)
    return Response(status_code=204)
