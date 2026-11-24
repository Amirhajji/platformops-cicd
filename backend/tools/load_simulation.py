"""Load the simulator output into the database (docs/PLATFORM_V1.md, sections 3 and 4).

Run from backend/: .venv\\Scripts\\python tools\\load_simulation.py [--admin-password X]
Everything is loaded in one transaction: an error leaves the database as it was.
"""
import argparse
import csv
import hashlib
import io
import json
import re
import secrets
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Tuple

import yaml
from sqlalchemy import func, insert, select, text
from sqlalchemy.dialects.postgresql import insert as upsert
from sqlalchemy.engine import Connection

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.db import models  # noqa: E402
from tools.database import target_engine  # noqa: E402

SIMULATOR = BACKEND.parent / "simulator"
OUTPUT = SIMULATOR / "output"
CONFIG = SIMULATOR / "config"
CATALOG = SIMULATOR / "catalog" / "huawei_metrics_catalog.csv"
SPEC = SIMULATOR / "SPEC.md"

ALERT_HEALTH = 50  # an alert is open while health < ALERT_HEALTH
MERGE_GAP = 5  # alerts at most this many ticks apart belong to the same incident
PBKDF2_ITERATIONS = 600000

# Every table except users, which holds accounts and is never truncated.
LOADED = [models.SimulationRun, models.Component, models.Metric, models.MetricPoint,
          models.Kpi, models.KpiPoint, models.KqiPoint, models.SimulatedIncident,
          models.Alert, models.Incident]


class LoadError(Exception):
    """The simulator files are not consistent."""


class Alert(NamedTuple):
    kpi_id: str
    component_id: str
    start_tick: int
    end_tick: int
    min_health: float


class Incident(NamedTuple):
    component_id: str
    start_tick: int
    end_tick: int
    alert_count: int
    min_z: float


# --- rules: alerts, incidents, status, passwords ---------------------------

def find_alerts(kpi_id: str, component_id: str, health: List[float]) -> List[Alert]:
    """One alert per run of consecutive ticks with health < 50."""
    alerts = []
    start: Optional[int] = None
    for tick, value in enumerate(health + [float(ALERT_HEALTH)]):  # closes at the end
        if value < ALERT_HEALTH and start is None:
            start = tick
        elif value >= ALERT_HEALTH and start is not None:
            alerts.append(Alert(kpi_id, component_id, start, tick - 1,
                                min(health[start:tick])))
            start = None
    return alerts


def merge_alerts(component_id: str, alerts: List[Alert], z: List[float]) -> List[Incident]:
    """Merge the alerts of one component that overlap or are <= 5 ticks apart."""
    groups: List[List[int]] = []  # [start, end, alert count]
    for alert in sorted(alerts, key=lambda a: a.start_tick):
        if groups and alert.start_tick - groups[-1][1] <= MERGE_GAP:
            groups[-1][1] = max(groups[-1][1], alert.end_tick)
            groups[-1][2] += 1
        else:
            groups.append([alert.start_tick, alert.end_tick, 1])
    return [Incident(component_id, start, end, count, min(z[start:end + 1]))
            for start, end, count in groups]


def status_of(z: float, bands: Dict[str, List[float]]) -> str:
    """The band with the highest lower bound that z reaches."""
    return max((low, name) for name, (low, _) in bands.items() if z >= low)[1]


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


# --- reading the simulator files -------------------------------------------

def read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> Tuple[List[str], List[List[str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    return rows[0], rows[1:]


def check_manifest(run: Dict[str, Any]) -> str:
    """Check every output file against manifest.json. Returns its sha256."""
    content = (OUTPUT / "manifest.json").read_bytes()
    manifest = json.loads(content)
    if (manifest["seed"], manifest["start"], manifest["ticks"]) != (
            run["seed"], run["start_utc"], run["ticks"]):
        raise LoadError("manifest.json does not match run.yaml")
    expected = {f"x/{Path(name).stem}.csv" for name in run["components"]}
    expected |= {"y_kpis.csv", "z_kqis.csv", "labels.csv"}
    if set(manifest["files"]) != expected:
        raise LoadError(f"manifest.json lists {sorted(manifest['files'])}")
    for name, entry in manifest["files"].items():
        data = (OUTPUT / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise LoadError(f"{name}: sha256 differs from manifest.json")
        if data.count(b"\n") - 1 != entry["rows"]:
            raise LoadError(f"{name}: row count differs from manifest.json")
    return hashlib.sha256(content).hexdigest()


def check_catalog(components: List[Dict[str, Any]]) -> None:
    """The configured metrics are exactly the in-scope metrics of the catalog."""
    with CATALOG.open(encoding="utf-8", newline="") as handle:
        catalog = {(row["component"].split()[0], row["metric_id"], row["unit"])
                   for row in csv.DictReader(handle) if row["in_scope"] == "yes"}
    configured = {(component["id"], metric["id"], metric["unit"])
                  for component in components for metric in component["metrics"]}
    if catalog != configured:
        raise LoadError(f"config and catalog differ: {sorted(catalog ^ configured)[:5]}")


def spec_version() -> str:
    match = re.search(r"frozen v(\d+(?:\.\d+)+)", SPEC.read_text(encoding="utf-8"))
    if match is None:
        raise LoadError("no version in SPEC.md")
    return match.group(1)


# --- loading ---------------------------------------------------------------

def copy_rows(connection: Connection, table: str, columns: str,
              lines: Iterable[str]) -> None:
    """COPY tab-separated lines, inside the current transaction."""
    cursor = connection.connection.cursor()
    cursor.copy_expert(f"COPY {table} ({columns}) FROM STDIN", io.StringIO("".join(lines)))


def insert_rows(connection: Connection, model: Any, rows: List[Dict[str, Any]]) -> None:
    if rows:
        connection.execute(insert(model), rows)


def load_run(connection: Connection, run: Dict[str, Any], manifest_sha256: str) -> None:
    insert_rows(connection, models.SimulationRun, [{
        "spec_version": spec_version(), "seed": run["seed"],
        "start_utc": run["start_utc"], "tick_seconds": run["tick_seconds"],
        "ticks": run["ticks"], "manifest_sha256": manifest_sha256}])


def load_metrics(connection: Connection, component: Dict[str, Any], x_path: Path,
                 ticks: int) -> None:
    """The component, its metrics and their points."""
    namespaces = dict.fromkeys(metric["namespace"] for metric in component["metrics"])
    insert_rows(connection, models.Component, [{
        "id": component["id"], "name": component["name"],
        "namespace": " + ".join(namespaces)}])
    columns: Dict[str, str] = {}  # column of the x file -> metrics.column_name
    rows = []
    for metric in component["metrics"]:
        for resource in component["resources"][metric["level"]]:
            x_name = f"{resource}.{metric['id']}"
            columns[x_name] = f"{component['id']}.{x_name}"
            rows.append({
                "component_id": component["id"], "level": metric["level"],
                "resource": resource, "metric_id": metric["id"], "name": metric["name"],
                "unit": metric["unit"], "range_min": metric["official_range"][0],
                "range_max": metric["official_range"][1],
                "period_min": metric["period_min"], "decimals": metric["decimals"],
                "column_name": columns[x_name]})
    insert_rows(connection, models.Metric, rows)
    ids = {name: metric_id for metric_id, name in connection.execute(
        select(models.Metric.id, models.Metric.column_name))}

    header, body = read_csv(x_path)
    if sorted(header[2:]) != sorted(columns) or len(body) != ticks:
        raise LoadError(f"{x_path.name} does not match the configuration")
    for index, x_name in enumerate(header[2:], start=2):
        metric_id = ids[columns[x_name]]
        copy_rows(connection, "metric_points", "metric_id, tick, value",
                  (f"{metric_id}\t{row[0]}\t{row[index]}\n" for row in body))


def load_kpis(connection: Connection,
              kpis: List[Dict[str, Any]]) -> Dict[str, List[float]]:
    """The KPIs and their points. Returns the health of each KPI, by tick."""
    insert_rows(connection, models.Kpi, [{
        "id": kpi["id"], "component_id": kpi["component"], "name": kpi["name"],
        "signal": kpi["signal"], "type": kpi["type"], "level": kpi["level"],
        "input": (kpi["input"] if isinstance(kpi["input"], str)
                  else json.dumps(kpi["input"])),
        "good": kpi["good"], "bad": kpi["bad"], "better": kpi["better"]}
        for kpi in kpis])
    _, body = read_csv(OUTPUT / "y_kpis.csv")
    copy_rows(connection, "kpi_points", "kpi_id, tick, value, health",
              (f"{kpi_id}\t{tick}\t{value}\t{health}\n"
               for tick, _, _, kpi_id, value, health in body))
    health_of: Dict[str, List[float]] = {kpi["id"]: [] for kpi in kpis}
    for tick, _, _, kpi_id, _, health in body:
        if int(tick) != len(health_of[kpi_id]):
            raise LoadError(f"y_kpis.csv: {kpi_id} tick {tick} is not in order")
        health_of[kpi_id].append(float(health))
    return health_of


def load_kqis(connection: Connection, component_ids: List[str],
              bands: Dict[str, List[float]]) -> Dict[str, List[float]]:
    """The KQI points of every scope. Returns z of each scope, by tick."""
    header, body = read_csv(OUTPUT / "z_kqis.csv")
    if header != ["tick", "timestamp_utc"] + component_ids + ["global", "status"]:
        raise LoadError(f"z_kqis.csv: header {header}")
    z_of: Dict[str, List[float]] = {}
    lines = []
    for index, name in enumerate(component_ids + ["global"], start=2):
        scope = "GLOBAL" if name == "global" else name
        z_of[scope] = [float(row[index]) for row in body]
        for row, z in zip(body, z_of[scope]):
            status = status_of(z, bands)
            if scope == "GLOBAL" and status != row[-1]:
                raise LoadError(f"z_kqis.csv tick {row[0]}: status {row[-1]}")
            lines.append(f"{scope}\t{row[0]}\t{row[index]}\t{status}\n")
    copy_rows(connection, "kqi_points", "scope, tick, z, status", lines)
    return z_of


def load_labels(connection: Connection) -> None:
    _, body = read_csv(OUTPUT / "labels.csv")
    insert_rows(connection, models.SimulatedIncident, [
        {"component_id": component_id, "start_tick": int(start), "end_tick": int(end),
         "description": description}
        for component_id, start, end, _, _, description in body])


def load_detections(connection: Connection, kpis: List[Dict[str, Any]],
                    component_ids: List[str], health_of: Dict[str, List[float]],
                    z_of: Dict[str, List[float]]) -> None:
    alerts = [alert for kpi in kpis
              for alert in find_alerts(kpi["id"], kpi["component"], health_of[kpi["id"]])]
    incidents = [incident for component_id in component_ids
                 for incident in merge_alerts(
                     component_id, [a for a in alerts if a.component_id == component_id],
                     z_of[component_id])]
    insert_rows(connection, models.Alert, [alert._asdict() for alert in alerts])
    insert_rows(connection, models.Incident, [i._asdict() for i in incidents])


def save_admin(connection: Connection, password: str) -> None:
    values = {"username": "admin", "password_hash": hash_password(password),
              "role": "admin"}
    connection.execute(upsert(models.User).values(values).on_conflict_do_update(
        index_elements=["username"],
        set_={"password_hash": values["password_hash"], "role": "admin"}))


def load_all(connection: Connection, admin_password: Optional[str]) -> None:
    run = read_yaml(CONFIG / "run.yaml")
    manifest_sha256 = check_manifest(run)
    components = [read_yaml(CONFIG / name) for name in run["components"]]
    check_catalog(components)
    kpi_config = read_yaml(CONFIG / "kpis.yaml")
    kpis, component_ids = kpi_config["kpis"], [c["id"] for c in components]

    tables = ", ".join(model.__tablename__ for model in LOADED)
    connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY"))
    load_run(connection, run, manifest_sha256)
    for component, name in zip(components, run["components"]):
        load_metrics(connection, component, OUTPUT / "x" / f"{Path(name).stem}.csv",
                     run["ticks"])
    health_of = load_kpis(connection, kpis)
    z_of = load_kqis(connection, component_ids, kpi_config["status_bands"])
    load_labels(connection)
    load_detections(connection, kpis, component_ids, health_of, z_of)
    if admin_password is not None:
        save_admin(connection, admin_password)

    metric_count = sum(len(component["resources"][metric["level"]])
                       for component in components for metric in component["metrics"])
    check_counts(connection, {
        models.SimulationRun: 1,
        models.Component: len(components),
        models.Metric: metric_count,
        models.MetricPoint: metric_count * run["ticks"],
        models.Kpi: len(kpis),
        models.KpiPoint: len(kpis) * run["ticks"],
        models.KqiPoint: (len(components) + 1) * run["ticks"],
        models.SimulatedIncident: sum(len(i) for i in run["incidents"].values()),
    })


def count(connection: Connection, model: Any) -> int:
    return connection.execute(select(func.count()).select_from(model)).scalar_one()


def check_counts(connection: Connection, expected: Dict[Any, int]) -> None:
    for model, rows in expected.items():
        if count(connection, model) != rows:
            raise LoadError(f"{model.__tablename__}: {count(connection, model)} rows, "
                            f"expected {rows}")


# --- report ----------------------------------------------------------------

def report(connection: Connection) -> bool:
    """Print row counts and incidents. True if every simulated incident matches
    exactly one detected incident and nothing else was detected."""
    for model in LOADED + [models.User]:
        print(f"{model.__tablename__:<20} {count(connection, model):>9,} rows")
    detected = connection.execute(select(models.Incident.__table__).order_by(
        models.Incident.component_id, models.Incident.start_tick)).all()
    simulated = connection.execute(select(models.SimulatedIncident.__table__).order_by(
        models.SimulatedIncident.component_id,
        models.SimulatedIncident.start_tick)).all()

    print("\ncomp  simulated    detected     alerts  min_z  match")
    used, ok = set(), True
    for label in simulated:
        found = [i for i in detected if i.component_id == label.component_id
                 and i.start_tick <= label.end_tick and label.start_tick <= i.end_tick]
        unique = len(found) == 1 and found[0].id not in used
        ok = ok and unique
        used.update(i.id for i in found)
        shown = "  ".join(f"{i.start_tick:>4}-{i.end_tick:<4}    {i.alert_count:>6} "
                          f"{i.min_z:>6.2f}" for i in found) or "none"
        print(f"{label.component_id:<5} {label.start_tick:>4}-{label.end_tick:<4}    "
              f"{shown}  {'one' if unique else 'PROBLEM'}")
    extra = [i for i in detected if i.id not in used]
    for incident in extra:
        print(f"EXTRA {incident.component_id} {incident.start_tick}-{incident.end_tick}")
    print(f"{len(simulated)} simulated, {len(detected)} detected, {len(extra)} extra")
    return ok and not extra


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--admin-password",
                        help="create or update the user admin (role admin)")
    arguments = parser.parse_args()
    started = time.perf_counter()
    engine = target_engine()
    try:
        with engine.begin() as connection:
            load_all(connection, arguments.admin_password)
    except LoadError as error:
        print(f"Nothing was loaded: {error}")
        return 1
    print(f"Load time: {time.perf_counter() - started:.1f} s\n")
    with engine.connect() as connection:
        return 0 if report(connection) else 1


if __name__ == "__main__":
    sys.exit(main())
