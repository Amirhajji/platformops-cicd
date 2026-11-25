"""The create_user tool. Database writes are rolled back (see conftest.py)."""
import contextlib
import sys

import pytest
from sqlalchemy import text

from app.core.security import verify_password
from tools import create_user, database

GOOD = "long-enough-1"


class FakeEngine:
    def __init__(self, session):
        self._session = session

    @contextlib.contextmanager
    def begin(self):
        yield self._session.connection()


@pytest.fixture
def run(session, monkeypatch, capsys):
    def _run(username, role, *answers):
        replies = iter(answers)
        monkeypatch.setattr(create_user.getpass, "getpass", lambda prompt: next(replies))
        monkeypatch.setattr(create_user, "target_engine", lambda: FakeEngine(session))
        monkeypatch.setattr(sys, "argv", ["create_user.py", "--username", username,
                                          "--role", role])
        code = create_user.main()
        printed = capsys.readouterr()
        for answer in answers:
            assert answer not in printed.out + printed.err
        return code, printed.out
    return _run


def stored(session, username):
    return session.execute(text("select password_hash, role from users "
                                "where username = :name"), {"name": username}).all()


def test_creates_then_updates_the_user(run, session, client):
    assert run("test-tool", "viewer", GOOD, GOOD)[0] == 0
    (row,) = stored(session, "test-tool")
    assert row.role == "viewer" and verify_password(GOOD, row.password_hash)

    assert run("test-tool", "admin", "another-pass", "another-pass")[0] == 0
    (row,) = stored(session, "test-tool")
    assert row.role == "admin" and verify_password("another-pass", row.password_hash)

    login = client.post("/api/auth/login", json={"username": "test-tool",
                                                 "password": "another-pass"})
    assert login.status_code == 200 and login.json()["role"] == "admin"


@pytest.mark.parametrize("username, answers, message", [
    ("test-no", (GOOD, GOOD + "x"), "different"),
    ("test-no", ("short#1", "short#1"), "password"),
    ("a b", (GOOD, GOOD), "username"),
])
def test_invalid_account_changes_nothing(run, session, username, answers, message):
    code, printed = run(username, "viewer", *answers)
    assert code == 1 and message in printed
    assert stored(session, username) == []


def test_refuses_without_db_name(monkeypatch):
    monkeypatch.setattr(database, "explicit_settings", lambda: {"DB_HOST": "localhost"})
    monkeypatch.setattr(create_user.getpass, "getpass",
                        lambda prompt: pytest.fail("the password must not be asked"))
    monkeypatch.setattr(sys, "argv", ["create_user.py", "--username", "test-no",
                                      "--role", "admin"])
    with pytest.raises(SystemExit, match="DB_NAME is not set"):
        create_user.main()


def test_unknown_role_is_refused(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["create_user.py", "--username", "test-no",
                                      "--role", "root"])
    with pytest.raises(SystemExit) as error:
        create_user.main()
    assert error.value.code == 2
