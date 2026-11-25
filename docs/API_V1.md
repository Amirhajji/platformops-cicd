# PlatformOPS API V1: contract for the frontend

Base URL: `http://192.168.21.133:8000`. Bodies and responses are JSON. The formulas behind
the values are in `PLATFORM_V1.md` (alerts, incidents, status) and `simulator/SPEC.md`
(KPIs, health, KQIs). Examples are real responses; `...` marks shortened lists.

## Common rules

**Token.** Every `/api` route except `POST /api/auth/login` needs
`Authorization: Bearer <token>`. A token is valid for 8 hours and stops working when its
user is deleted. On a 401, go back to the login page.

**Roles.** `viewer`: every GET except `/api/users`. `admin`: the same, plus `/api/users`.

**Time.** `from`, `to` and `at` are ISO UTC timestamps inside the run, for example
`2026-11-01T05:00:00Z`. `from` and `to` are included; without them the range is the whole
run. `at` defaults to the end of the run. A timestamp between two ticks is rounded down to
its tick: `tick = floor((ts - start_utc) / tick_seconds)`. Outside the run: 400.

**Buckets.** A series has at most 1000 points. Ticks are grouped into equal buckets of
`bucket_ticks` ticks (1 = exact values; the last bucket can be shorter). `ts` is the first
tick of each bucket. Metric and KPI values are the **average** of the bucket; `health` and
`z` are the **minimum**, so incidents stay visible. `status` is the status at the lowest z.

**Intervals.** `end_ts` is the last tick of an alert or incident (included).
`duration_seconds` counts that tick. Lists contain every interval that overlaps the range,
oldest first.

**Status** is `healthy`, `degraded` or `critical`. **Scopes** are `GLOBAL`, `C1` ... `C8`.

**Errors** always have this shape:

```json
{"error": {"code": "not_found", "message": "Unknown component: C9"}}
```

| HTTP | `code` | When |
|---|---|---|
| 400 | `bad_request` | invalid or missing parameter or body |
| 401 | `unauthorized` | missing, invalid or expired token, wrong login |
| 403 | `forbidden` | a viewer calls an admin route |
| 404 | `not_found` | unknown id or route |
| 405 | `method_not_allowed` | wrong HTTP method |
| 500 | `error` | unexpected error |
| 503 | `unavailable` | database not reachable, no simulation loaded, or no token secret |

## Health (no token)

`GET /health` → `{"status": "ok"}`. It does not use the database.

## Authentication

### POST /api/auth/login

```json
{"username": "admin", "password": "..."}
```
→ 200
```json
{"token": "eyJzdWIi...", "role": "admin"}
```

### GET /api/auth/me

```json
{"id": 1, "username": "admin", "role": "admin", "created_at": "2026-11-24T23:28:04Z"}
```

## Run and scores

### GET /api/run

```json
{"spec_version": "1.2", "seed": 42, "start_utc": "2026-11-01T00:00:00Z",
 "end_utc": "2026-11-07T23:59:00Z", "tick_seconds": 60, "ticks": 10080}
```
`end_utc` is the last tick: the limits of the range picker are `start_utc` and `end_utc`.

### GET /api/overview?from&to

`z` and `status` are the values at `to`; `min_z`, `alerts` and `incidents` cover the range.
Always 9 scopes, `GLOBAL` first.

`GET /api/overview?from=2026-11-01T05:00:00Z&to=2026-11-01T05:10:00Z`
```json
{"from_ts": "2026-11-01T05:00:00Z", "to_ts": "2026-11-01T05:10:00Z",
 "scopes": [
   {"scope": "GLOBAL", "name": "Global", "z": 87.88, "status": "healthy",
    "min_z": 86.82, "alerts": 5, "incidents": 1},
   {"scope": "C1", "name": "GaussDB(DWS)", "z": 5.75, "status": "critical",
    "min_z": 0.0, "alerts": 5, "incidents": 1},
   ...]}
```

### GET /api/kqi/series?scope&from&to

`scope` is required.

`GET /api/kqi/series?scope=C1&from=2026-11-01T04:59:00Z&to=2026-11-01T05:00:00Z`
```json
{"scope": "C1", "bucket_ticks": 1,
 "ts": ["2026-11-01T04:59:00Z", "2026-11-01T05:00:00Z"],
 "z": [100.0, 0.0], "status": ["healthy", "critical"]}
```

## Components and KPIs

### GET /api/components

```json
[{"id": "C1", "name": "GaussDB(DWS)", "namespace": "SYS.DWS"},
 {"id": "C2", "name": "DMS for Kafka", "namespace": "SYS.DMS"}, ...]
```

### GET /api/components/{id}?at

The component, its z and status, and its KPIs at that time. `better` is `lower` or
`higher`; `type` is `value`, `average`, `maximum` or `ratio`.

`GET /api/components/C1?at=2026-11-01T05:10:00Z`
```json
{"id": "C1", "name": "GaussDB(DWS)", "namespace": "SYS.DWS",
 "at": "2026-11-01T05:10:00Z", "z": 5.75, "status": "critical",
 "kpis": [
   {"id": "dws_cache", "name": "Cache efficiency", "signal": "latency", "type": "value",
    "value": 84.31, "health": 28.73, "good": 95.0, "bad": 80.0, "better": "higher"},
   {"id": "dws_cpu", "name": "CPU load", "signal": "saturation", "type": "average",
    "value": 93.96666666666665, "health": 0.0, "good": 60.0, "bad": 90.0,
    "better": "lower"},
   ...]}
```

### GET /api/kpis/{id}/series?from&to

`GET /api/kpis/dws_cpu/series?from=2026-11-01T04:59:00Z&to=2026-11-01T05:00:00Z`
```json
{"id": "dws_cpu", "component_id": "C1", "name": "CPU load",
 "good": 60.0, "bad": 90.0, "better": "lower", "bucket_ticks": 1,
 "ts": ["2026-11-01T04:59:00Z", "2026-11-01T05:00:00Z"],
 "value": [48.29, 95.47666666666667], "health": [100.0, 0.0]}
```

## Metrics

### GET /api/metrics?component&q

Catalog search, at most 504 rows. `q` is split into words; every word must be in the
column name or the name (upper and lower case are the same). `range_max` can be `null`.

`GET /api/metrics?component=C1&q=cpu`
```json
[{"id": 10, "component_id": "C1", "column_name": "C1.node1.dws010_cpu_usage",
  "metric_id": "dws010_cpu_usage", "name": "CPU Usage", "unit": "%",
  "resource": "node1", "level": "node", "period_min": 1,
  "range_min": 0.0, "range_max": 100.0}, ...]
```

### GET /api/metrics/series?ids&from&to

`ids`: 1 to 6 metric ids, separated by commas. All series share `ts`, in the order of `ids`.

`GET /api/metrics/series?ids=10,11&from=2026-11-01T04:59:00Z&to=2026-11-01T05:00:00Z`
```json
{"bucket_ticks": 1,
 "ts": ["2026-11-01T04:59:00Z", "2026-11-01T05:00:00Z"],
 "series": [
   {"id": 10, "column_name": "C1.node1.dws010_cpu_usage", "name": "CPU Usage",
    "unit": "%", "values": [48.07, 97.73]},
   {"id": 11, "column_name": "C1.node2.dws010_cpu_usage", "name": "CPU Usage",
    "unit": "%", "values": [42.66, 95.74]}]}
```

## Alerts and incidents

### GET /api/alerts?component&from&to

`GET /api/alerts?component=C1&to=2026-11-01T06:00:00Z`
```json
[{"id": 1, "start_ts": "2026-11-01T05:00:00Z", "end_ts": "2026-11-01T05:29:00Z",
  "duration_seconds": 1800, "kpi_id": "dws_cpu", "kpi_name": "CPU load",
  "component_id": "C1", "min_health": 0.0}, ...]
```

### GET /api/incidents?component&from&to

`GET /api/incidents?component=C1`
```json
[{"id": 1, "start_ts": "2026-11-01T05:00:00Z", "end_ts": "2026-11-01T05:31:00Z",
  "duration_seconds": 1920, "component_id": "C1", "alert_count": 5, "min_z": 0.0}, ...]
```

### GET /api/incidents/{id}

The incident, its alerts, and the simulated incident (ground truth) whose interval
overlaps it on the same component, or `null`.

`GET /api/incidents/1`
```json
{"id": 1, "start_ts": "2026-11-01T05:00:00Z", "end_ts": "2026-11-01T05:31:00Z",
 "duration_seconds": 1920, "component_id": "C1", "alert_count": 5, "min_z": 0.0,
 "alerts": [
   {"id": 1, "start_ts": "2026-11-01T05:00:00Z", "end_ts": "2026-11-01T05:29:00Z",
    "duration_seconds": 1800, "kpi_id": "dws_cpu", "kpi_name": "CPU load",
    "component_id": "C1", "min_health": 0.0}, ...],
 "simulated_incident": {
   "id": 1, "start_ts": "2026-11-01T05:00:00Z", "end_ts": "2026-11-01T05:29:00Z",
   "duration_seconds": 1800, "description": "GaussDB(DWS) bad period 1 of 3"}}
```

## Users (admin only)

### GET /api/users

```json
[{"id": 1, "username": "admin", "role": "admin", "created_at": "2026-11-24T23:28:04Z"}]
```

### POST /api/users

`username`: 3 to 64 characters among letters, digits, `.`, `_`, `-`. `password`: 8 to 128
characters. `role`: `admin` or `viewer`. An existing username is a 400.
```json
{"username": "operator", "password": "long-enough", "role": "viewer"}
```
→ 201
```json
{"id": 2, "username": "operator", "role": "viewer", "created_at": "2026-11-24T23:30:00Z"}
```

### DELETE /api/users/{id}

→ 204 without a body. Deleting yourself is a 400.
