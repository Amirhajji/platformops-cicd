# PlatformOPS V1: reference for backend and frontend

Data comes from the simulator (`simulator/SPEC.md`, spec v1.2). Deployment rules are in
`CLAUDE.md`. This file defines the features, the database, the rules and the load.

## 1. Features

1. **Global overview**: global score Z, the 8 components with their own status, timeline.
2. **Component page**: KPIs with value, health and G/B thresholds, metric charts.
3. **Metric explorer**: search the 504 metrics, compare several on one chart.
4. **Alerts and incidents**: lists, details, comparison with the simulated incidents.
5. **Login** with two roles: `admin` and `viewer`.

**Time** is a range picker inside the 7 simulated days (2026-11-01T00:00:00Z to
2026-11-07T23:59:00Z, 10,080 ticks of 60 s). There is no fake live mode.

## 2. Schema

Owned by one Alembic migration (`backend/alembic/versions/`). Models:
`backend/app/db/models.py`. Timestamps are not stored per point:
`ts = start_utc + tick * tick_seconds`.

| Table | Columns | Rows |
|---|---|---|
| `simulation_run` | id, spec_version, seed, start_utc, tick_seconds, ticks, loaded_at, manifest_sha256 | 1 |
| `components` | id (`C1`..`C8`), name, namespace | 8 |
| `metrics` | id, component_id, level, resource, metric_id, name, unit, range_min, range_max (nullable), period_min, decimals, column_name (unique) | 504 |
| `metric_points` | metric_id, tick, value. PK (metric_id, tick) | 5,080,320 |
| `kpis` | id, component_id, name, signal, type, level, input, good, bad, better | 33 |
| `kpi_points` | kpi_id, tick, value, health. PK (kpi_id, tick) | 332,640 |
| `kqi_points` | scope, tick, z, status. PK (scope, tick) | 90,720 |
| `simulated_incidents` | id, component_id, start_tick, end_tick, description | 24 |
| `alerts` | id, kpi_id, component_id, start_tick, end_tick, min_health | computed |
| `incidents` | id, component_id, start_tick, end_tick, alert_count, min_z | computed |
| `users` | id, username (unique), password_hash, role, created_at | accounts |

- `metrics`: one row per resource and metric. `column_name` is
  `<component>.<resource>.<metric_id>`, for example `C1.node1.dws010_cpu_usage`. Resource
  names can contain dots, so use the columns and do not split this name.
- `kpis.input`: the metric id, or JSON for a list of metrics or a ratio (`part`, `total`).
- `kqi_points.scope`: `C1`..`C8` or `GLOBAL`. `components.namespace`: all the namespaces
  of its metrics, joined with ` + `.
- `simulated_incidents` = `labels.csv`, the ground truth. It is never used to detect.
- All `end_tick` values are included in the interval.
- `users.role` is `admin` or `viewer`. `password_hash` is
  `pbkdf2_sha256$<iterations>$<salt hex>$<hash hex>` (`hashlib.pbkdf2_hmac`, stdlib).

## 3. Rules

**Status**, for every scope, from `status_bands` of `simulator/config/kpis.yaml`:

| z | Status |
|---|---|
| z >= 80 | `healthy` |
| 50 <= z < 80 | `degraded` |
| z < 50 | `critical` |

**Alert**, per KPI: opens at the first tick with health < 50 and closes at the last tick
before health >= 50 again (or at the last tick of the run). `min_health` is the lowest
health in the interval.

**Incident**, per component: alerts whose intervals overlap, or that are at most 5 ticks
apart (`next start - current end <= 5`), are merged. `alert_count` is the number of merged
alerts. `min_z` is the lowest z of the component in the interval.

Metrics with a 4, 5 or 30-minute period keep their value until the next update. A detected
incident can therefore end later than the simulated one, by less than one period.

**Match**: a detected incident matches a simulated one when they belong to the same
component and their intervals overlap. Each simulated incident must match exactly one
detected incident.

These rules are computed once, by the loader. The API only reads the tables.

## 4. Load procedure (Windows, never deployed)

From `backend/`, with the Python 3.8 venv:

```powershell
py -3.8 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m alembic upgrade head
.venv\Scripts\python tools\load_simulation.py
.venv\Scripts\python tools\load_simulation.py --admin-password <password>   # + admin user
```

Generate the data first: `python -m simulator run` and `validate` (`simulator/README.md`).

The target database comes from `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`:
environment variables first, then `backend/.env.local` (git-ignored), then the defaults of
the VM. Alembic and the loader refuse to start when `DB_NAME` is not set explicitly, so
that the deployed database is never changed by accident.

The loader, in one transaction (an error leaves the database as it was):

1. checks the sha256 and row count of every file in `manifest.json`, that the manifest
   matches `run.yaml`, and that the metrics match the in-scope catalog;
2. truncates every table except `users`, and reloads them (COPY for the points);
3. computes statuses, alerts and incidents, and checks the global status against
   `z_kqis.csv`;
4. checks the row count of every table, then commits and prints the detected incidents
   next to the simulated ones.

## 5. Backend layout

Shipped by Jenkins: `backend/app/` and `backend/requirements.txt` only.

| Path | Role |
|---|---|
| `app/main.py` | FastAPI app, CORS, `GET /health` (no database) |
| `app/core/config.py` | settings, never connects at import |
| `app/db/models.py` | SQLAlchemy models |
| `alembic/`, `alembic.ini`, `tools/`, `tests/`, `requirements-dev.txt` | not shipped |
