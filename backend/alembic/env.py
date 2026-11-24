from logging.config import fileConfig

from alembic import context

from app.db.models import Base
from tools.database import target_engine

fileConfig(context.config.config_file_name)


def run_migrations() -> None:
    if context.is_offline_mode():
        raise SystemExit("offline mode is not supported")
    with target_engine().connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations()
