"""Accounts and login."""
import os
from functools import lru_cache
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ApiError, bad_request, not_found, unauthorized
from app.core.security import (TokenUser, create_token, hash_password, read_token,
                               verify_password)
from app.db.models import AuthSecret, User


@lru_cache(maxsize=1)
def _unknown_user_hash() -> str:
    return hash_password("unknown user")


def token_secret(session: Session) -> bytes:
    """SECRET_KEY if it is set, else the random secret that the loader created."""
    value = os.environ.get("SECRET_KEY") or session.scalar(select(AuthSecret.value))
    if not value:
        raise ApiError(503, "Login is not configured: run the loader to create the secret")
    return value.encode()


def login(session: Session, username: str, password: str) -> Tuple[str, str]:
    """(token, role). The answer and its duration do not tell whether the user exists."""
    user = session.scalars(select(User).where(User.username == username)).first()
    stored = _unknown_user_hash() if user is None else user.password_hash
    if not verify_password(password, stored) or user is None:
        raise unauthorized("Wrong username or password")
    token = create_token(TokenUser(user.id, user.username), token_secret(session))
    return token, user.role


def user_of_token(session: Session, token: Optional[str]) -> User:
    """The role always comes from the database, so changes apply at once."""
    claimed = read_token(token, token_secret(session)) if token else None
    user = session.get(User, claimed.id) if claimed else None
    if claimed is None or user is None or user.username != claimed.username:
        raise unauthorized("Missing, invalid or expired token")
    return user


def list_users(session: Session) -> List[User]:
    return list(session.scalars(select(User).order_by(User.id)))


def create_user(session: Session, username: str, password: str, role: str) -> User:
    user = User(username=username, password_hash=hash_password(password), role=role)
    session.add(user)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise bad_request(f"username: {username} already exists")
    return user


def delete_user(session: Session, user_id: int, current: User) -> None:
    if user_id == current.id:
        raise bad_request("You cannot delete yourself")
    user = session.get(User, user_id)
    if user is None:
        raise not_found("user", user_id)
    session.delete(user)
    session.commit()
