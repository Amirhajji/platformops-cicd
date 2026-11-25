"""Output files: section 6 of the specification."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from .config import Component, RunConfig
from .kqis import Kqi

KpiRow = tuple[str, str, float, float]  # (component, kpi_id, value, health)


def write_csv(path: Path, header: list[str], rows: Iterable[list[Any]]) -> int:
    """Write one CSV file and return its number of data rows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    # newline="" and "\n": the same bytes on every platform.
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def write_x(path: Path, run: RunConfig, component: Component,
            rows: Iterable[list[float]]) -> int:
    columns = component.columns()
    # Fixed number of decimals per column (0 decimals: whole numbers).
    formats = [f"{{:.{metric.decimals}f}}".format for _, metric in columns]
    header = ["tick", "timestamp_utc"] + [
        f"{resource}.{metric.id}" for resource, metric in columns]
    return write_csv(path, header, (
        [tick, run.timestamp(tick)] + [fmt(value) for fmt, value in zip(formats, values)]
        for tick, values in enumerate(rows)))


def write_kpis(path: Path, run: RunConfig, ticks: Iterable[list[KpiRow]]) -> int:
    # KPI values are not rounded, so health can be recomputed from this file.
    return write_csv(
        path, ["tick", "timestamp_utc", "component", "kpi_id", "value", "health"],
        ([tick, run.timestamp(tick), component, kpi_id, value, f"{health:.2f}"]
         for tick, rows in enumerate(ticks)
         for component, kpi_id, value, health in rows))


def write_kqis(path: Path, run: RunConfig, kqis: Iterable[Kqi]) -> int:
    header = (["tick", "timestamp_utc"] + [c.id for c in run.components]
              + ["global", "status"])
    return write_csv(path, header, (
        [tick, run.timestamp(tick)] + [f"{z:.2f}" for z in kqi.components]
        + [f"{kqi.overall:.2f}", kqi.status]
        for tick, kqi in enumerate(kqis)))


def write_labels(path: Path, run: RunConfig) -> int:
    header = ["component", "start_tick", "end_tick", "start_utc", "end_utc",
              "description"]
    return write_csv(path, header, (
        [component.id, start, end, run.timestamp(start), run.timestamp(end),
         f"{component.name} bad period {number} of {len(component.incidents)}"]
        for component in run.components
        for number, (start, end) in enumerate(component.incidents, start=1)))


def write_manifest(path: Path, run: RunConfig, row_counts: dict[str, int]) -> None:
    """row_counts: file path relative to the manifest -> number of data rows."""
    manifest = {
        "seed": run.seed,
        "start": run.timestamp(0),
        "ticks": run.ticks,
        "files": {
            name: {
                "rows": rows,
                "sha256": hashlib.sha256((path.parent / name).read_bytes()).hexdigest(),
            }
            for name, rows in row_counts.items()
        },
    }
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")
