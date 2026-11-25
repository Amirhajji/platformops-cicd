"""Create or update one account. The password is asked, never shown.

Run from backend/: .venv\\Scripts\\python tools\\create_user.py --username admin --role admin
"""
import argparse
import getpass
import sys
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy.dialects.postgresql import insert as upsert
from sqlalchemy.engine import Connection

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password  # noqa: E402
from app.db.models import User  # noqa: E402
from app.schemas.auth import UserCreate  # noqa: E402
from tools.database import target_engine  # noqa: E402


class AccountError(Exception):
    """The account does not follow the rules. The message never holds the password."""


def check_account(username: str, password: str, role: str) -> None:
    """The same rules as POST /api/users."""
    try:
        UserCreate(username=username, password=password, role=role)
    except ValidationError as error:
        # Not str(error): it would show the rejected value.
        raise AccountError("; ".join(f"{item['loc'][0]}: {item['msg']}"
                                     for item in error.errors())) from None


def save_user(connection: Connection, username: str, password: str, role: str) -> None:
    check_account(username, password, role)
    hashed = hash_password(password)
    connection.execute(
        upsert(User)
        .values(username=username, password_hash=hashed, role=role)
        .on_conflict_do_update(index_elements=["username"],
                               set_={"password_hash": hashed, "role": role}))


def ask_password() -> str:
    password = getpass.getpass("Password: ")
    if getpass.getpass("Password again: ") != password:
        raise AccountError("the two passwords are different")
    return password


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--username", required=True)
    parser.add_argument("--role", required=True, choices=["admin", "viewer"])
    arguments = parser.parse_args()
    engine = target_engine()
    try:
        password = ask_password()
        with engine.begin() as connection:
            save_user(connection, arguments.username, password, arguments.role)
    except AccountError as error:
        print(f"Nothing was changed: {error}")
        return 1
    print(f"User {arguments.username} saved with role {arguments.role}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
