"""Settings of the backend. Nothing here connects to the database.

The database settings come only from DB_HOST, DB_PORT, DB_NAME, DB_USER and DB_PASSWORD:
environment variables first, then backend/.env.local (development only, never shipped),
then the defaults below, which match the backend VM. The password has no default.
"""
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, NamedTuple

from sqlalchemy.engine import URL

ENV_FILE = Path(__file__).resolve().parents[2] / ".env.local"
DEFAULTS = {
    "DB_HOST": "192.168.21.1",
    "DB_PORT": "5432",
    "DB_NAME": "platformops",
    "DB_USER": "platformops",
    "DB_PASSWORD": "",
}
CORS_ORIGINS: List[str] = [
    "http://192.168.21.134",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


class Settings(NamedTuple):
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str

    @property
    def database_url(self) -> URL:
        return URL.create("postgresql+psycopg2", self.db_user, self.db_password,
                          self.db_host, self.db_port, self.db_name)


def explicit_settings() -> Dict[str, str]:
    """The DB_* settings that are set in the environment or in .env.local."""
    values: Dict[str, str] = {}
    if ENV_FILE.is_file():
        for line in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
            name, separator, value = line.strip().partition("=")
            if separator and not name.startswith("#"):
                values[name.strip()] = value.strip()
    values.update(os.environ)
    return {name: values[name] for name in DEFAULTS if values.get(name)}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    values = dict(DEFAULTS)
    values.update(explicit_settings())
    return Settings(values["DB_HOST"], int(values["DB_PORT"]), values["DB_NAME"],
                    values["DB_USER"], values["DB_PASSWORD"])
