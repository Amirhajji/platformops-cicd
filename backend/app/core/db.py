"""Database sessions. The engine is created on first use, never at import time."""
from functools import lru_cache
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True,
                         connect_args={"connect_timeout": 5})


def get_session() -> Iterator[Session]:
    """One session per request. Services that write must commit."""
    with Session(get_engine()) as session:
        yield session
