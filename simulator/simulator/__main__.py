"""Command line: `python -m simulator run` (from the simulator/ folder)."""
from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Iterator

from . import writer
from .config import RunConfig, load_config
from .generator import ComponentGenerator
from .kpis import build_kpis, compute_component
from .kqis import Kqi, compute_kqi

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
OUTPUT_DIR = ROOT / "output"


def x_name(stem: str) -> str:
    return f"x/{stem}.csv"


def compute_kpi_ticks(config: RunConfig) -> Iterator[list[writer.KpiRow]]:
    """KPI rows of each tick, for all components, from the written x files."""
    kpis = [build_kpis(config.kpis, component) for component in config.components]
    streams = [compute_component(component, own, OUTPUT_DIR / x_name(component.stem))
               for component, own in zip(config.components, kpis)]
    for results in zip(*streams, strict=True):
        yield [(kpi.component, kpi.id, value, health)
               for own, result in zip(kpis, results)
               for kpi, (value, health) in zip(own, result)]


def compute_kqis(config: RunConfig, ticks: list[list[writer.KpiRow]]) -> Iterator[Kqi]:
    for rows in ticks:
        health = [[row[3] for row in rows if row[0] == component.id]
                  for component in config.components]
        yield compute_kqi(health, config.status_bands)


def run() -> None:
    started = time.perf_counter()
    config = load_config(CONFIG_DIR)
    counts: dict[str, int] = {}
    for component in config.components:
        name = x_name(component.stem)
        rows = ComponentGenerator(config, component).rows()
        counts[name] = writer.write_x(OUTPUT_DIR / name, config, component, rows)
    ticks = list(compute_kpi_ticks(config))
    counts["y_kpis.csv"] = writer.write_kpis(OUTPUT_DIR / "y_kpis.csv", config, ticks)
    counts["z_kqis.csv"] = writer.write_kqis(
        OUTPUT_DIR / "z_kqis.csv", config, compute_kqis(config, ticks))
    counts["labels.csv"] = writer.write_labels(OUTPUT_DIR / "labels.csv", config)
    writer.write_manifest(OUTPUT_DIR / "manifest.json", config, counts)

    for name, count in counts.items():
        print(f"{name:<22} {count:>7} rows")
    columns = sum(len(component.columns()) for component in config.components)
    print(f"manifest.json          {len(counts):>7} files listed")
    print(f"{columns} metric columns, {time.perf_counter() - started:.1f} s")


def main() -> None:
    parser = argparse.ArgumentParser(prog="simulator")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("run", help="generate all the files of output/")
    parser.parse_args()
    run()


if __name__ == "__main__":
    main()
