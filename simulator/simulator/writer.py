"""CSV output: output/x/<component file stem>.csv"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from .config import Component, RunConfig


def write_x(run: RunConfig, component: Component,
            rows: Iterable[list[float]], directory: Path) -> tuple[Path, int, int]:
    """Write one component. Returns (path, data rows, metric columns)."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{component.stem}.csv"
    columns = component.columns()
    # Fixed number of decimals per column (0 decimals: whole numbers).
    formats = [f"{{:.{metric.decimals}f}}".format for _, metric in columns]
    count = 0
    # newline="" and "\n": the same bytes on every platform.
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["tick", "timestamp_utc"]
                        + [f"{resource}.{metric.id}" for resource, metric in columns])
        for tick, values in enumerate(rows):
            writer.writerow([tick, run.timestamp(tick)]
                            + [fmt(value) for fmt, value in zip(formats, values)])
            count += 1
    return path, count, len(columns)
