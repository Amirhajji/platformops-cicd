"""Fixtures of the integration tests.

They run against platformops_dev and are skipped if it cannot be reached. Every request
uses one connection whose transaction is rolled back at the end: the accounts created by
the tests never reach the database, and the other tables are only read.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import explicit_settings  # noqa: E402
from app.core.db import get_engine, get_session  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.models import AuthSecret, User  # noqa: E402
from app.main import app  # noqa: E402

ADMIN, VIEWER, PASSWORD = "test-admin", "test-viewer", "test-password"


@pytest.fixture(scope="module")
def session():
    if explicit_settings().get("DB_NAME") != "platformops_dev":
        pytest.skip("DB_NAME is not platformops_dev")
    try:
        connection = get_engine().connect()
    except OperationalError:
        pytest.skip("platformops_dev cannot be reached")
    transaction = connection.begin()
    # Commits inside the session only release savepoints of the outer transaction.
    with Session(connection, join_transaction_mode="create_savepoint",
                 expire_on_commit=False) as test_session:
        hashed = hash_password(PASSWORD)
        test_session.add_all([User(username=ADMIN, password_hash=hashed, role="admin"),
                              User(username=VIEWER, password_hash=hashed, role="viewer")])
        if test_session.get(AuthSecret, 1) is None:
            test_session.add(AuthSecret(id=1, value="test-secret"))
        test_session.commit()
        yield test_session
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="module")
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


def _headers(client, username):
    response = client.post("/api/auth/login",
                           json={"username": username, "password": PASSWORD})
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["token"]}


@pytest.fixture(scope="module")
def admin(client):
    return _headers(client, ADMIN)


@pytest.fixture(scope="module")
def viewer(client):
    return _headers(client, VIEWER)


@pytest.fixture(scope="module")
def get(client, viewer):
    """GET as a viewer, and check the status code."""
    def _get(path, status=200, **params):
        # "from" is a Python keyword: tests write from_.
        params = {name.rstrip("_"): value for name, value in params.items()}
        response = client.get("/api" + path, params=params, headers=viewer)
        assert response.status_code == status, response.text
        return response.json()
    return _get
