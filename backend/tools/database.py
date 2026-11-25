"""Database access of the Windows tools (migrations and loader)."""
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

from app.core.config import ENV_FILE, explicit_settings, get_settings


def target_engine() -> Engine:
    """Engine of the target database. These tools change or erase data, so the target
    must be chosen explicitly: the defaults point to the deployed database."""
    if "DB_NAME" not in explicit_settings():
        raise SystemExit(f"DB_NAME is not set: set it in the environment or in {ENV_FILE}")
    settings = get_settings()
    print(f"Database: {settings.db_name} on {settings.db_host}:{settings.db_port} "
          f"(user {settings.db_user})")
    return create_engine(settings.database_url, poolclass=NullPool)
