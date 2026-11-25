# PlatformOPS simulator

Generates 7 days of Huawei Cloud monitoring data: metrics (x), KPIs (y), health (h)
and KQIs (z). Same config and seed, same files, byte for byte. Rules: `SPEC.md` and
`docs/PlatformOPS_Simulator_Specification.pdf`. `config/` and `catalog/` are frozen.

Runs on Windows only and is never deployed. All commands run from `simulator/`.

## Setup (once, Python 3.12)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install pyyaml==6.0.4 pytest==9.2.0
```

## Commands

```powershell
.venv\Scripts\python -m simulator run        # writes output/ (about 20 s)
.venv\Scripts\python -m simulator validate   # checks output/, exit code 1 on failure
.venv\Scripts\python -m pytest -q            # tests, in temp folders only
```

`run` and `validate` accept `--output <folder>`.

## Output files (`output/`, not in git)

| File | Content |
|---|---|
| `x/C1_dws.csv` ... `x/C8_cce.csv` | 10,080 rows each, 504 metric columns in total: `tick, timestamp_utc, <resource>.<metric_id> ...` |
| `y_kpis.csv` | 332,640 rows: `tick, timestamp_utc, component, kpi_id, value, health` |
| `z_kqis.csv` | 10,080 rows: `tick, timestamp_utc, C1 ... C8, global, status` (status of global) |
| `labels.csv` | 24 bad periods: `component, start_tick, end_tick, start_utc, end_utc, description` (ends included) |
| `manifest.json` | seed, start, ticks, and the row count and SHA-256 of every file |

Resource names can contain dots (`telemetry.metrics.dws.v1`): split an x column name
on its last dot.
