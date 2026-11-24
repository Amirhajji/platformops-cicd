"""Command line: `python -m simulator run` (from the simulator/ folder)."""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from .config import load_config
from .generator import ComponentGenerator
from .writer import write_x

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
OUTPUT_DIR = ROOT / "output"


def run() -> None:
    started = time.perf_counter()
    config = load_config(CONFIG_DIR)
    total_columns = 0
    for component in config.components:
        rows = ComponentGenerator(config, component).rows()
        path, count, columns = write_x(config, component, rows, OUTPUT_DIR / "x")
        total_columns += columns
        print(f"{path.name:<20} {count:>6} rows  {columns:>4} metric columns")
    print(f"{len(config.components)} files, {total_columns} metric columns, "
          f"{time.perf_counter() - started:.1f} s")


def main() -> None:
    parser = argparse.ArgumentParser(prog="simulator")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("run", help="generate the metrics (x) into output/x/")
    parser.parse_args()
    run()


if __name__ == "__main__":
    main()
