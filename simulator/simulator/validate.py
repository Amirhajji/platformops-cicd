"""Acceptance checks of the output files: section 8 of the specification.

Reads only the output files, the configuration and the catalog. It must not import
generator, kpis or kqis: the formulas are written again here on purpose, so that an
error in those modules cannot hide itself. The check "two runs give identical files"
needs the generator, so it is a test (tests/test_run.py).
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from functools import cached_property
from pathlib import Path
from typing import Any, Callable, Iterator

from .config import Component, Metric, RunConfig, load_config
from .expr import Expression

# Sizes fixed by the specification.
X_FILES, TICKS, X_COLUMNS, Y_ROWS = 8, 10_080, 504, 332_640
MIN_KQI_DROP = 30
TOLERANCE = 1e-9

# "Paired values add up": (component, parts, total).
PAIRS = [
    ("C3", ("disk_used", "disk_free"), "disk_total"),
    ("C3", ("cpu_usage", "cpu_usage_idle"), 100),
    ("C7", ("subnet_ipv4_availability_used_number",
            "subnet_ipv4_availability_remain_number"),
     "subnet_ipv4_availability_total_number"),
]

Problems = Iterator[str]


class XFile:
    """One x file, checked for number format while it is read."""

    def __init__(self, path: Path, component: Component) -> None:
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.reader(handle))
        self.header, body = rows[0], rows[1:]
        self.row_count = len(body)
        self.keys = [row[:2] for row in body]
        self.format_errors: list[str] = []
        self.columns: dict[tuple[str, str], list[float]] = {}
        decimals = {f"{resource}.{metric.id}": ((resource, metric.id), metric.decimals)
                    for resource, metric in component.columns()}
        for index, name in enumerate(self.header[2:], start=2):
            key, places = decimals[name]
            values = []
            for tick, row in enumerate(body):
                value = float(row[index])
                if row[index] != f"{value:.{places}f}":
                    self.format_errors.append(f"{path.name} {name} tick {tick}: "
                                              f"{row[index]!r} is not {places} decimals")
                values.append(value)
            self.columns[key] = values


class Output:
    def __init__(self, config_dir: Path, catalog_path: Path, output_dir: Path) -> None:
        self.run: RunConfig = load_config(config_dir)
        self.dir = output_dir
        with catalog_path.open(encoding="utf-8", newline="") as handle:
            self.catalog = [row for row in csv.DictReader(handle)
                            if row["in_scope"] == "yes"]

    @cached_property
    def x(self) -> dict[str, XFile]:
        return {c.id: XFile(self.dir / "x" / f"{c.stem}.csv", c)
                for c in self.run.components}

    @cached_property
    def y(self) -> list[list[str]]:
        return self._table("y_kpis.csv")

    @cached_property
    def z(self) -> list[list[str]]:
        return self._table("z_kqis.csv")

    def _table(self, name: str) -> list[list[str]]:
        with (self.dir / name).open(encoding="utf-8", newline="") as handle:
            return list(csv.reader(handle))

    def series(self) -> Iterator[tuple[Component, str, Metric, list[float]]]:
        """Every metric column: (component, resource, metric, values)."""
        for component in self.run.components:
            columns = self.x[component.id].columns
            for resource, metric in component.columns():
                yield component, resource, metric, columns[resource, metric.id]

    def catalog_rows(self, component: Component) -> dict[str, dict[str, str]]:
        return {row["metric_id"]: row for row in self.catalog
                if row["component"].split()[0] == component.id}


def written(metric: Metric, value: float) -> float:
    if metric.range_low is not None and value < metric.range_low:
        value = metric.range_low
    if metric.range_high is not None and value > metric.range_high:
        value = metric.range_high
    return round(value, metric.decimals)


# --- x files ---------------------------------------------------------------

def check_x_shape(out: Output) -> Problems:
    expected = {f"{c.stem}.csv" for c in out.run.components}
    found = {path.name for path in (out.dir / "x").iterdir()}
    if found != expected or len(found) != X_FILES:
        yield f"files in x/: {sorted(found)}"
    for component in out.run.components:
        x = out.x[component.id]
        if x.row_count != TICKS:
            yield f"{component.stem}.csv has {x.row_count} rows"
        if x.header[:2] != ["tick", "timestamp_utc"]:
            yield f"{component.stem}.csv starts with {x.header[:2]}"
        for tick, key in enumerate(x.keys):
            if key != [str(tick), out.run.timestamp(tick)]:
                yield f"{component.stem}.csv row {tick}: {key}"


def check_x_columns(out: Output) -> Problems:
    total = 0
    for component in out.run.components:
        level_of = {metric.id: metric.level for metric in component.metrics}
        expected = []
        for metric_id, row in out.catalog_rows(component).items():
            level = level_of.get(metric_id)
            if level is None or not row["level"].startswith(level):
                yield f"{component.id} {metric_id}: level {level!r} is not in the catalog"
                continue
            expected += [f"{name}.{metric_id}" for name in component.resources[level]]
        header = out.x[component.id].header[2:]
        total += len(header)
        if sorted(header) != sorted(expected):
            yield f"{component.stem}.csv: {sorted(set(header) ^ set(expected))[:5]}"
    if total != X_COLUMNS:
        yield f"{total} metric columns"


def check_x_ranges(out: Output) -> Problems:
    """official_range of the YAML files, which are authoritative (section 4)."""
    for component, resource, metric, values in out.series():
        low = -math.inf if metric.range_low is None else metric.range_low
        high = math.inf if metric.range_high is None else metric.range_high
        if metric.unit == "%":
            low, high = max(low, 0), min(high, 100)
        if metric.unit == "count":
            low = max(low, 0)
        for tick, value in enumerate(values):
            if not (math.isfinite(value) and low <= value <= high):
                yield f"{component.id} {resource}.{metric.id} tick {tick}: {value}"


def check_x_decimals(out: Output) -> Problems:
    for component in out.run.components:
        yield from out.x[component.id].format_errors
        for metric in component.metrics:
            if metric.unit == "count" and metric.decimals != 0:
                yield f"{component.id} {metric.id}: count with {metric.decimals} decimals"


def check_x_periods(out: Output) -> Problems:
    for component, resource, metric, values in out.series():
        if metric.period_min != int(
                out.catalog_rows(component)[metric.id]["period_min"]):
            yield f"{component.id} {metric.id}: period differs from the catalog"
        for tick in range(1, len(values)):
            if tick % metric.period_min and values[tick] != values[tick - 1]:
                yield f"{component.id} {resource}.{metric.id} changes at tick {tick}"


def check_x_incidents(out: Output) -> Problems:
    """Random and flag values follow the incident schedule of run.yaml."""
    for component, resource, metric, values in out.series():
        if metric.kind not in ("random", "flag"):
            continue
        for tick in range(0, len(values), metric.period_min):
            bad = component.is_bad(tick)
            if metric.kind == "flag":
                unhealthy = bad and resource == metric.params["bad_resource"]
                low = high = metric.params["unhealthy" if unhealthy else "healthy"]
            else:
                low, high = metric.params["bad" if bad else "normal"]
            if not written(metric, low) <= values[tick] <= written(metric, high):
                yield f"{component.id} {resource}.{metric.id} tick {tick}: {values[tick]}"


def check_x_constants(out: Output) -> Problems:
    for component, resource, metric, values in out.series():
        if metric.kind == "constant" and set(values) != {
                written(metric, metric.params["value"])}:
            yield f"{component.id} {resource}.{metric.id}: {sorted(set(values))[:3]}"


def check_x_counters(out: Output) -> Problems:
    for component, resource, metric, values in out.series():
        if metric.kind != "counter":
            continue
        previous = metric.params["start"]
        for tick, value in enumerate(values):
            if value < previous:
                yield f"{component.id} {resource}.{metric.id} goes down at tick {tick}"
            previous = value


def check_x_pairs(out: Output) -> Problems:
    components = {c.id: c for c in out.run.components}
    for component_id, parts, total in PAIRS:
        component, columns = components[component_id], out.x[component_id].columns
        metrics = {metric.id: metric for metric in component.metrics}
        first = metrics[parts[0]]
        for resource in component.resources[first.level]:
            for tick in range(out.x[component_id].row_count):
                got = sum(columns[resource, part][tick] for part in parts)
                want = total if isinstance(total, int) else columns[resource, total][tick]
                if round(got, first.decimals) != want:
                    yield f"{component_id} {resource} {'+'.join(parts)} tick {tick}: " \
                          f"{got} != {want}"


def check_x_derived(out: Output) -> Problems:
    for component, resource, metric, values in out.series():
        if metric.kind != "derived":
            continue
        evaluate = Expression(metric.params["expr"]).evaluate
        columns = out.x[component.id].columns
        for tick in range(0, len(values), metric.period_min):
            want = written(metric, evaluate(
                lambda name: columns[resource, name][tick],
                lambda level, name: [columns[other, name][tick]
                                     for other in component.resources[level]]))
            if values[tick] != want:
                yield f"{component.id} {resource}.{metric.id} tick {tick}: " \
                      f"{values[tick]} != {want}"


# --- KPIs, health, KQIs ----------------------------------------------------

def _ratio_side(text: str, level: str, count: int,
                at: Callable[[str], list[float]]) -> float:
    if match := re.fullmatch(r"sum\((\w+)\)", text):
        return sum(at(match[1]))
    if match := re.fullmatch(r"count\((\w+) == (\d+)\)", text):
        return sum(value == float(match[2]) for value in at(match[1]))
    if match := re.fullmatch(r"count\((\w+)\)", text):
        if match[1] != level:
            raise ValueError(f"count({match[1]}) is not level {level!r}")
        return count
    return sum(at(name.strip())[0] for name in text.split("+"))


def _kpi_value(kpi: dict[str, Any], resources: list[str],
               columns: dict[tuple[str, str], list[float]], tick: int) -> float:
    def at(metric: str) -> list[float]:
        return [columns[resource, metric][tick] for resource in resources]

    source = kpi["input"]
    if kpi["type"] == "ratio":
        part, total = (_ratio_side(source[side], kpi["level"], len(resources), at)
                       for side in ("part", "total"))
        return part / total * 100
    values = [v for name in (source if isinstance(source, list) else [source])
              for v in at(name)]
    if kpi["type"] == "maximum":
        return max(values)
    if kpi["type"] == "value" and len(values) != 1:
        raise ValueError(f"{kpi['id']}: value needs exactly one input")
    return math.fsum(values) / len(values)


def _health(value: float, kpi: dict[str, Any]) -> float:
    """Rule 8 of section 9, as written there: one formula per direction."""
    good, bad = kpi["good"], kpi["bad"]
    if kpi["better"] == "lower":
        if value <= good:
            return 100.0
        score = 0.0 if value >= bad else 100 * (bad - value) / (bad - good)
    else:
        if value >= good:
            return 100.0
        score = 0.0 if value <= bad else 100 * (value - bad) / (good - bad)
    return round(score, 2)


def _same(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=TOLERANCE, abs_tol=TOLERANCE)


def check_y_rows(out: Output) -> Problems:
    header, *body = out.y
    if header != ["tick", "timestamp_utc", "component", "kpi_id", "value", "health"]:
        yield f"header {header}"
    if len(body) != Y_ROWS:
        yield f"{len(body)} rows"
    keys = ([str(tick), out.run.timestamp(tick), kpi["component"], kpi["id"]]
            for tick in range(TICKS) for kpi in out.run.kpis)
    for row, key in zip(body, keys):
        if row[:4] != key:
            yield f"row {row[:4]}, expected {key}"


def check_y_values(out: Output) -> Problems:
    components = {c.id: c for c in out.run.components}
    rows = iter(out.y[1:])
    for tick in range(TICKS):
        for kpi in out.run.kpis:
            row = next(rows)
            component = components[kpi["component"]]
            value = _kpi_value(kpi, component.resources[kpi["level"]],
                               out.x[component.id].columns, tick)
            if not _same(float(row[4]), value):
                yield f"{kpi['id']} tick {tick}: value {row[4]}, expected {value}"
            if not _same(float(row[5]), _health(value, kpi)):
                yield f"{kpi['id']} tick {tick}: health {row[5]}, " \
                      f"expected {_health(value, kpi)}"


def check_z_rows(out: Output) -> Problems:
    header, *body = out.z
    if header != ["tick", "timestamp_utc", *(c.id for c in out.run.components),
                  "global", "status"]:
        yield f"header {header}"
    if len(body) != TICKS:
        yield f"{len(body)} rows"
    for tick, row in enumerate(body):
        if row[:2] != [str(tick), out.run.timestamp(tick)]:
            yield f"row {tick}: {row[:2]}"


def _mean(scores: list[float]) -> float:
    return round(math.fsum(scores) / len(scores), 2)


def check_z_values(out: Output) -> Problems:
    ids = [c.id for c in out.run.components]
    health: dict[tuple[str, str], list[float]] = {}
    for row in out.y[1:]:
        health.setdefault((row[0], row[2]), []).append(float(row[5]))
    for row in out.z[1:]:
        z = [_mean(health[row[0], component]) for component in ids]
        for name, got, want in zip(ids + ["global"], row[2:-1], z + [_mean(z)]):
            if not _same(float(got), want):
                yield f"tick {row[0]} {name}: {got}, expected {want}"


def check_z_status(out: Output) -> Problems:
    lows = {name: low for name, (low, _) in out.run.status_bands.items()}
    for row in out.z[1:]:
        score = float(row[-2])
        want = ("healthy" if score >= lows["healthy"] else
                "degraded" if score >= lows["degraded"] else "critical")
        if row[-1] != want:
            yield f"tick {row[0]}: {row[-1]}, expected {want}"


def check_z_drop(out: Output) -> Problems:
    for index, component in enumerate(out.run.components, start=2):
        z = [float(row[index]) for row in out.z[1:]]
        normal = [value for tick, value in enumerate(z) if not component.is_bad(tick)]
        limit = math.fsum(normal) / len(normal) - MIN_KQI_DROP
        for tick, value in enumerate(z):
            if component.is_bad(tick) and value > limit:
                yield f"{component.id} tick {tick}: {value} is above {limit:.2f}"


# --- labels and manifest ---------------------------------------------------

def check_labels(out: Output) -> Problems:
    header, *body = out._table("labels.csv")
    if header != ["component", "start_tick", "end_tick", "start_utc", "end_utc",
                  "description"]:
        yield f"header {header}"
    expected = [[c.id, str(start), str(end), out.run.timestamp(start),
                 out.run.timestamp(end)]
                for c in out.run.components for start, end in c.incidents]
    if [row[:5] for row in body] != expected:
        yield "rows differ from the incidents of run.yaml"
    if any(not row[5] for row in body):
        yield "empty description"


def check_manifest(out: Output) -> Problems:
    manifest = json.loads((out.dir / "manifest.json").read_text(encoding="utf-8"))
    want = {"seed": out.run.seed, "start": out.run.timestamp(0), "ticks": out.run.ticks}
    if {key: manifest.get(key) for key in want} != want:
        yield f"seed, start or ticks differ from run.yaml: {want}"
    on_disk = {path.relative_to(out.dir).as_posix()
               for path in out.dir.rglob("*") if path.is_file()} - {"manifest.json"}
    if set(manifest["files"]) != on_disk:
        yield f"files: {sorted(set(manifest['files']) ^ on_disk)}"
    for name, entry in manifest["files"].items():
        content = (out.dir / name).read_bytes()
        if entry["rows"] != content.count(b"\n") - 1:
            yield f"{name}: {entry['rows']} rows"
        if entry["sha256"] != hashlib.sha256(content).hexdigest():
            yield f"{name}: sha256"


CHECKS: list[tuple[str, Callable[[Output], Problems]]] = [
    ("x: 8 files, 10,080 rows, ticks and timestamps", check_x_shape),
    ("x: 504 columns, in-scope catalog x resources", check_x_columns),
    ("x: values inside official_range", check_x_ranges),
    ("x: decimals, counts are whole numbers", check_x_decimals),
    ("x: values change only on their period", check_x_periods),
    ("x: random and flag values follow the incidents", check_x_incidents),
    ("x: constants never change", check_x_constants),
    ("x: growing totals never go down", check_x_counters),
    ("x: paired values add up", check_x_pairs),
    ("x: derived columns match their expression", check_x_derived),
    ("y: 332,640 rows, one per tick and KPI", check_y_rows),
    ("y: KPI values and health recomputed from x", check_y_values),
    ("z: 10,080 rows, ticks and timestamps", check_z_rows),
    ("z: component and global KQIs recomputed from y", check_z_values),
    ("z: status matches the bands", check_z_status),
    ("z: at least 30 points below normal in incidents", check_z_drop),
    ("labels match the incidents of run.yaml", check_labels),
    ("manifest: settings, row counts and sha256", check_manifest),
]


def validate(config_dir: Path, catalog_path: Path, output_dir: Path) -> bool:
    """Print one PASS/FAIL line per check. True if every check passes."""
    out = Output(config_dir, catalog_path, output_dir)
    passed = 0
    for name, check in CHECKS:
        first, count = "", 0
        try:
            for problem in check(out):
                first, count = first or problem, count + 1
        except Exception as error:  # an unreadable file is a failed check, not a crash
            first, count = first or f"{type(error).__name__}: {error}", count + 1
        if count:
            print(f"FAIL  {name}: {count} problem(s), first: {first}")
        else:
            print(f"PASS  {name}")
            passed += 1
    print(f"{passed}/{len(CHECKS)} checks passed")
    return passed == len(CHECKS)
