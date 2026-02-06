# app/db/session.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings

CI_MODE = os.getenv("CI") == "true"

# --------------------------------------------------
# Engine / Session creation
# --------------------------------------------------
if not CI_MODE:
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        future=True,
    )

    SessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        future=True,
    )
else:
    # CI mode: no DB initialization
    engine = None
    SessionLocal = None


# --------------------------------------------------
# Dependency
# --------------------------------------------------
def get_db():
    if SessionLocal is None:
        raise RuntimeError("Database not available in CI mode")

    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
