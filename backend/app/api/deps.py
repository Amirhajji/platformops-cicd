"""Shared dependencies of the routers: user, run, time window, component filter."""
from typing import Optional

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.core.errors import ApiError
from app.db.models import User
from app.services import scores, timeline, users

ID_PATTERN = r"^[A-Za-z0-9_]{1,64}$"
MAX_INT = 2 ** 31 - 1  # PostgreSQL integer

bearer = HTTPBearer(auto_error=False)


def current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
                 session: Session = Depends(get_session)) -> User:
    return users.user_of_token(session, credentials.credentials if credentials else None)


def admin_user(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise ApiError(403, "This needs the admin role")
    return user


def current_run(session: Session = Depends(get_session)) -> timeline.Run:
    return timeline.get_run(session)


def time_window(from_: Optional[str] = Query(None, alias="from"),
                to: Optional[str] = Query(None),
                run: timeline.Run = Depends(current_run)) -> timeline.Window:
    return timeline.make_window(run, from_, to)


def component_filter(component: Optional[str] = Query(None, pattern=ID_PATTERN),
                     session: Session = Depends(get_session)) -> Optional[str]:
    if component is not None:
        scores.require_component(session, component)
    return component
