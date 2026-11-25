"""Every endpoint, against platformops_dev (see conftest.py)."""
import hashlib
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.core.config import get_settings
from app.core.db import get_session
from app.core.errors import ApiError
from app.core.security import TokenUser, create_token
from app.db.models import AuthSecret
from app.main import app
from app.services.users import token_secret
from tests.conftest import ADMIN, PASSWORD, VIEWER
from tools.load_simulation import create_secret

START, END = "2026-11-01T00:00:00Z", "2026-11-07T23:59:00Z"
# First incident of C1: ticks 300 to 329, detected until 331.
BAD_FROM, BAD_AT, BAD_TO = ("2026-11-01T05:00:00Z", "2026-11-01T05:10:00Z",
                            "2026-11-01T05:29:00Z")


def routes():
    return [(method, route.path) for route in app.routes
            for method in getattr(route, "methods", ())
            if route.path.startswith("/api/")]


def is_error(response, status, code):
    return (response.status_code == status and set(response.json()) == {"error"}
            and set(response.json()["error"]) == {"code", "message"}
            and response.json()["error"]["code"] == code)


# --- without a database ------------------------------------------------------

def test_health_needs_no_database():
    assert TestClient(app).get("/health").json() == {"status": "ok"}


def test_database_failure_is_a_503():
    def broken():
        raise OperationalError("select", {}, Exception("down"))
    app.dependency_overrides[get_session] = broken
    try:
        client = TestClient(app)
        assert is_error(client.get("/api/run"), 503, "unavailable")
        assert client.get("/health").status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_unexpected_error_is_a_500_without_details():
    def broken():
        raise RuntimeError("internal detail")
    app.dependency_overrides[get_session] = broken
    try:
        response = TestClient(app, raise_server_exceptions=False).get("/api/run")
        assert is_error(response, 500, "error")
        assert "internal detail" not in response.text
    finally:
        app.dependency_overrides.clear()


def test_cors_allows_the_frontend():
    response = TestClient(app).options("/api/run", headers={
        "Origin": "http://192.168.21.134", "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Authorization"})
    assert response.headers["access-control-allow-origin"] == "http://192.168.21.134"
    other = TestClient(app).get("/health", headers={"Origin": "http://example.com"})
    assert "access-control-allow-origin" not in other.headers


# --- authentication and roles ------------------------------------------------

@pytest.mark.parametrize("method, path", [
    route for route in routes() if route != ("POST", "/api/auth/login")])
@pytest.mark.parametrize("headers", [
    {}, {"Authorization": "Bearer wrong.token"}, {"Authorization": "Basic YTpi"}])
def test_every_route_needs_a_valid_token(client, method, path, headers):
    url = path.replace("{user_id}", "1").replace("{incident_id}", "1")
    response = client.request(method, url, headers=headers)
    assert is_error(response, 401, "unauthorized")


def test_there_are_16_routes():
    assert len(routes()) == 16


def test_login(client):
    response = client.post("/api/auth/login",
                           json={"username": VIEWER, "password": PASSWORD})
    assert response.json()["role"] == "viewer"


@pytest.mark.parametrize("username, password", [
    (VIEWER, "wrong"), ("nobody", PASSWORD), (VIEWER, "")])
def test_wrong_login_gives_the_same_401(client, username, password):
    response = client.post("/api/auth/login",
                           json={"username": username, "password": password})
    assert is_error(response, 401, "unauthorized")
    assert response.json()["error"]["message"] == "Wrong username or password"


@pytest.mark.parametrize("body", [
    {}, {"username": VIEWER}, {"username": "a\x00b", "password": "x"},
    {"username": "\ud800", "password": "x"}, {"username": VIEWER, "password": 12}, []])
def test_invalid_login_body_is_a_400(client, body):
    response = client.post("/api/auth/login", content=json.dumps(body),
                           headers={"Content-Type": "application/json"})
    assert is_error(response, 400, "bad_request")


def test_rejected_password_is_not_echoed(client):
    response = client.post("/api/auth/login",
                           json={"username": VIEWER, "password": "S3cret" * 50})
    assert response.status_code == 400 and "S3cret" not in response.text


def test_me(client, admin, viewer):
    assert client.get("/api/auth/me", headers=admin).json()["role"] == "admin"
    assert client.get("/api/auth/me", headers=viewer).json()["username"] == VIEWER


@pytest.mark.parametrize("method, path", [
    ("GET", "/api/users"), ("POST", "/api/users"), ("DELETE", "/api/users/1")])
def test_viewer_cannot_manage_users(client, viewer, method, path):
    assert is_error(client.request(method, path, headers=viewer), 403, "forbidden")


def test_admin_can_also_read(client, admin):
    assert client.get("/api/overview", headers=admin).status_code == 200


def test_user_management(client, admin):
    body = {"username": "test-new", "password": "long-enough", "role": "viewer"}
    created = client.post("/api/users", json=body, headers=admin)
    assert created.status_code == 201
    assert set(created.json()) == {"id", "username", "role", "created_at"}
    assert is_error(client.post("/api/users", json=body, headers=admin),
                    400, "bad_request")
    names = [user["username"] for user in client.get("/api/users", headers=admin).json()]
    assert {ADMIN, VIEWER, "test-new"} <= set(names)

    token = client.post("/api/auth/login", json={
        "username": "test-new", "password": "long-enough"}).json()["token"]
    headers = {"Authorization": "Bearer " + token}
    assert client.get("/api/run", headers=headers).status_code == 200

    url = f"/api/users/{created.json()['id']}"
    assert client.delete(url, headers=admin).status_code == 204
    assert is_error(client.delete(url, headers=admin), 404, "not_found")
    # The token of a deleted user no longer works.
    assert is_error(client.get("/api/run", headers=headers), 401, "unauthorized")


def test_admin_cannot_delete_itself(client, admin):
    me = client.get("/api/auth/me", headers=admin).json()["id"]
    assert is_error(client.delete(f"/api/users/{me}", headers=admin), 400, "bad_request")


@pytest.mark.parametrize("change", [
    {"role": "root"}, {"password": "short"}, {"username": "a b c"}, {"username": "ab"}])
def test_invalid_user_is_a_400(client, admin, change):
    body = dict({"username": "test-bad", "password": "long-enough", "role": "viewer"},
                **change)
    assert is_error(client.post("/api/users", json=body, headers=admin),
                    400, "bad_request")


# --- token secret ------------------------------------------------------------

def test_secret_comes_from_the_database_or_from_secret_key(session, monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    assert token_secret(session) == session.get(AuthSecret, 1).value.encode()
    monkeypatch.setenv("SECRET_KEY", "from-env")
    assert token_secret(session) == b"from-env"


def test_token_derived_from_the_database_password_is_refused(client, session):
    admin_id = session.execute(text("select id from users where username = :name"),
                               {"name": ADMIN}).scalar_one()
    key = hashlib.sha256(
        f"platformops-auth|{get_settings().db_password}".encode()).digest()
    forged = create_token(TokenUser(admin_id, ADMIN), key)
    response = client.get("/api/users", headers={"Authorization": "Bearer " + forged})
    assert is_error(response, 401, "unauthorized")


def test_without_any_secret_login_is_a_503(client, session, monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    savepoint = session.begin_nested()
    session.execute(text("delete from auth_secret"))
    with pytest.raises(ApiError) as error:
        token_secret(session)
    assert error.value.status == 503
    response = client.post("/api/auth/login",
                           json={"username": ADMIN, "password": PASSWORD})
    assert is_error(response, 503, "unavailable")
    savepoint.rollback()


def test_loader_creates_the_secret_only_once(session):
    savepoint = session.begin_nested()
    session.execute(text("delete from auth_secret"))
    read = text("select value from auth_secret")
    create_secret(session.connection())
    first = session.execute(read).scalars().all()
    create_secret(session.connection())
    assert session.execute(read).scalars().all() == first
    assert len(first) == 1 and len(bytes.fromhex(first[0])) == 32
    savepoint.rollback()


# --- run, overview, KQIs -----------------------------------------------------

def test_run(get):
    assert get("/run") == {"spec_version": "1.2", "seed": 42, "start_utc": START,
                           "end_utc": END, "tick_seconds": 60, "ticks": 10080}


def scope_of(overview, scope):
    return next(row for row in overview["scopes"] if row["scope"] == scope)


def test_overview_of_the_whole_run(get):
    overview = get("/overview")
    assert [row["scope"] for row in overview["scopes"]] == [
        "GLOBAL", "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"]
    assert (overview["from_ts"], overview["to_ts"]) == (START, END)
    total = scope_of(overview, "GLOBAL")
    assert (total["alerts"], total["incidents"], total["min_z"]) == (99, 24, 86.39)
    assert all(row["incidents"] == 3 for row in overview["scopes"][1:])


def test_overview_c1_is_critical_inside_its_first_incident(get):
    overview = get("/overview", from_=BAD_FROM, to=BAD_AT)
    c1 = scope_of(overview, "C1")
    assert c1["status"] == "critical" and c1["z"] < 50
    assert (c1["alerts"], c1["incidents"]) == (5, 1)
    assert all(row["status"] == "healthy" for row in overview["scopes"]
               if row["scope"] != "C1")


@pytest.mark.parametrize("first, last", [
    (START, "2026-11-01T04:59:00Z"), ("2026-11-01T05:40:00Z", "2026-11-01T06:00:00Z")])
def test_overview_c1_is_healthy_outside(get, first, last):
    c1 = scope_of(get("/overview", from_=first, to=last), "C1")
    assert c1["status"] == "healthy" and c1["min_z"] >= 80
    assert (c1["alerts"], c1["incidents"]) == (0, 0)


def test_kqi_series_keeps_the_minimum(get, session):
    series = get("/kqi/series", scope="C1")
    assert series["bucket_ticks"] == 11
    assert len(series["ts"]) == len(series["z"]) == len(series["status"]) == 917
    expected = session.execute(text(
        "select min(z) from kqi_points where scope = 'C1' group by tick / 11 "
        "order by tick / 11")).scalars().all()
    assert series["z"] == expected
    # tick 300 is in bucket 27: the incident stays visible
    assert series["z"][27] < 50 and series["status"][27] == "critical"


def test_kqi_series_of_a_short_range_is_exact(get, session):
    series = get("/kqi/series", scope="GLOBAL", from_=BAD_FROM, to=BAD_TO)
    assert series["bucket_ticks"] == 1
    assert (series["ts"][0], series["ts"][-1]) == (BAD_FROM, BAD_TO)
    assert series["z"] == session.execute(text(
        "select z from kqi_points where scope = 'GLOBAL' and tick between 300 and 329 "
        "order by tick")).scalars().all()


# --- components and KPIs -----------------------------------------------------

def test_components(get):
    components = get("/components")
    assert [c["id"] for c in components] == [f"C{n}" for n in range(1, 9)]
    assert components[0] == {"id": "C1", "name": "GaussDB(DWS)", "namespace": "SYS.DWS"}


def test_component_at_a_time(get):
    good, bad = get("/components/C1", at=START), get("/components/C1", at=BAD_AT)
    assert [kpi["id"] for kpi in good["kpis"]] == [
        "dws_cache", "dws_cpu", "dws_disk", "dws_io_wait", "dws_mem"]
    assert (good["at"], good["status"]) == (START, "healthy")
    assert bad["status"] == "critical"
    assert all(kpi["health"] < 50 for kpi in bad["kpis"])
    cpu = good["kpis"][1]
    assert (cpu["good"], cpu["bad"], cpu["better"], cpu["type"]) == (
        60, 90, "lower", "average")
    assert get("/components/C1")["at"] == END


def test_kpi_series_averages_values_and_keeps_minimum_health(get, session):
    series = get("/kpis/dws_cpu/series")
    assert (series["bucket_ticks"], len(series["ts"])) == (11, 917)
    rows = session.execute(text(
        "select avg(value), min(health) from kpi_points where kpi_id = 'dws_cpu' "
        "group by tick / 11 order by tick / 11")).all()
    assert series["value"] == pytest.approx([row[0] for row in rows])
    assert series["health"] == [row[1] for row in rows]


# --- metrics -----------------------------------------------------------------

def test_metric_catalog(get):
    everything = get("/metrics")
    assert len(everything) == 504
    assert len(get("/metrics", component="C8")) == 131
    cpu = get("/metrics", component="C1", q="CPU")
    assert [m["column_name"] for m in cpu] == [
        f"C1.node{n}.dws010_cpu_usage" for n in (1, 2, 3)]
    assert cpu[0]["unit"] == "%" and cpu[0]["period_min"] == 1
    assert (cpu[0]["range_min"], cpu[0]["range_max"]) == (0, 100)
    assert [m["resource"] for m in get("/metrics", q="node2 cpu usage", component="C1")
            ] == ["node2"]


@pytest.mark.parametrize("q, count", [("%", None), ("no such metric", 0), ("'; --", 0)])
def test_metric_search_takes_special_characters_literally(get, q, count):
    found = get("/metrics", q=q)
    assert len(found) == (0 if count is None else count)


def test_metric_series(get, session):
    ids = [metric["id"] for metric in get("/metrics", component="C1")[:6]]
    result = get("/metrics/series", ids=",".join(str(i) for i in reversed(ids)))
    assert (result["bucket_ticks"], len(result["ts"])) == (11, 917)
    assert [series["id"] for series in result["series"]] == list(reversed(ids))
    for series in result["series"]:
        assert series["values"] == pytest.approx(session.execute(text(
            "select avg(value) from metric_points where metric_id = :id "
            "group by tick / 11 order by tick / 11"),
            {"id": series["id"]}).scalars().all())


def test_metric_series_of_a_short_range_is_exact(get, session):
    metric = get("/metrics", q="C1.node1.dws010_cpu_usage")[0]["id"]
    result = get("/metrics/series", ids=str(metric), from_=BAD_FROM, to=BAD_TO)
    assert result["bucket_ticks"] == 1
    assert result["series"][0]["values"] == session.execute(text(
        "select value from metric_points where metric_id = :id and "
        "tick between 300 and 329 order by tick"), {"id": metric}).scalars().all()


# --- alerts and incidents ----------------------------------------------------

def test_alerts(get):
    assert len(get("/alerts")) == 99
    alerts = get("/alerts", component="C1", from_=BAD_FROM, to=BAD_TO)
    assert len(alerts) == 5
    cpu = next(alert for alert in alerts if alert["kpi_id"] == "dws_cpu")
    assert (cpu["start_ts"], cpu["end_ts"]) == (BAD_FROM, BAD_TO)
    assert (cpu["duration_seconds"], cpu["kpi_name"]) == (1800, "CPU load")


def test_incidents(get):
    incidents = get("/incidents")
    assert len(incidents) == 24
    assert incidents == sorted(incidents, key=lambda i: i["start_ts"])
    assert len(get("/incidents", component="C7")) == 3
    assert get("/incidents", to="2026-11-01T04:59:00Z") == []


def test_incident_detail(get):
    first = get("/incidents", component="C1")[0]
    detail = get(f"/incidents/{first['id']}")
    assert {key: detail[key] for key in first} == first
    assert len(detail["alerts"]) == detail["alert_count"] == 5
    simulated = detail["simulated_incident"]
    assert (simulated["start_ts"], simulated["end_ts"]) == (BAD_FROM, BAD_TO)


def test_every_incident_has_its_alerts_and_a_simulated_incident(get):
    matched = set()
    for incident in get("/incidents"):
        detail = get(f"/incidents/{incident['id']}")
        assert len(detail["alerts"]) == incident["alert_count"]
        matched.add(detail["simulated_incident"]["id"])
    assert len(matched) == 24


# --- errors ------------------------------------------------------------------

@pytest.mark.parametrize("path, params", [
    ("/overview", {"from_": "yesterday"}),
    ("/overview", {"to": "2027-01-01T00:00:00Z"}),
    ("/overview", {"from_": END, "to": START}),
    ("/kqi/series", {}),
    ("/kqi/series", {"scope": "C1", "from_": "2026-10-01T00:00:00Z"}),
    ("/components/C1", {"at": "x"}),
    ("/components/C1;drop", {}),
    ("/components/%00", {}),
    ("/metrics", {"component": "a b"}),
    ("/metrics", {"q": "a\x00"}),
    ("/metrics/series", {}),
    ("/metrics/series", {"ids": ""}),
    ("/metrics/series", {"ids": "1,x"}),
    ("/metrics/series", {"ids": "1,,2"}),
    ("/metrics/series", {"ids": "-1"}),
    ("/metrics/series", {"ids": "99999999999"}),
    ("/metrics/series", {"ids": "1,2,3,4,5,6,7"}),
    ("/incidents/x", {}),
    ("/incidents/99999999999", {}),
])
def test_bad_parameters_are_400(get, path, params):
    assert get(path, 400, **params)["error"]["code"] == "bad_request"


@pytest.mark.parametrize("path, params", [
    ("/kqi/series", {"scope": "C9"}),
    ("/components/C9", {}),
    ("/kpis/unknown/series", {}),
    ("/metrics", {"component": "C9"}),
    ("/metrics/series", {"ids": "1,999999"}),
    ("/alerts", {"component": "C9"}),
    ("/incidents", {"component": "C9"}),
    ("/incidents/999999", {}),
    ("/nothing", {}),
])
def test_unknown_ids_are_404(get, path, params):
    assert get(path, 404, **params)["error"]["code"] == "not_found"


def test_wrong_method_has_the_same_error_shape(client, viewer):
    response = client.post("/api/run", headers=viewer)
    assert is_error(response, 405, "method_not_allowed")
