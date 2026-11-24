"""Load and check the frozen configuration (run.yaml, kpis.yaml, components/*.yaml)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

# Fields each kind must define. A counter needs either inc_from or both *_inc.
REQUIRED_FIELDS = {
    "random": ("normal", "bad"),
    "constant": ("value",),
    "flag": ("healthy", "unhealthy", "bad_resource"),
    "counter": ("start",),
    "derived": ("expr",),
}
COMMON_FIELDS = {"id", "name", "namespace", "level", "unit", "official_range",
                 "period_min", "decimals", "kind"}


class ConfigError(ValueError):
    """The configuration does not follow the specification."""


@dataclass(frozen=True)
class Metric:
    id: str
    level: str
    kind: str
    period_min: int
    decimals: int
    range_low: float | None
    range_high: float | None
    params: dict[str, Any]  # the kind-specific fields, as written in the YAML


@dataclass(frozen=True)
class Component:
    id: str
    name: str
    stem: str  # component file name without extension, e.g. "C1_dws"
    resources: dict[str, list[str]]  # level -> resource names
    metrics: list[Metric]
    incidents: list[tuple[int, int]]  # (start_tick, end_tick), both inclusive

    def is_bad(self, tick: int) -> bool:
        return any(start <= tick <= end for start, end in self.incidents)

    def columns(self) -> list[tuple[str, Metric]]:
        """(resource, metric) pairs in output order: level, resource, metric."""
        return [
            (resource, metric)
            for level, names in self.resources.items()
            for resource in names
            for metric in self.metrics
            if metric.level == level
        ]


@dataclass(frozen=True)
class RunConfig:
    seed: int
    start_utc: datetime
    tick_seconds: int
    ticks: int
    components: list[Component]
    kpis: list[dict[str, Any]]  # entries of kpis.yaml
    status_bands: dict[str, list[float]]  # status -> [low, high]

    def timestamp(self, tick: int) -> str:
        moment = self.start_utc + timedelta(seconds=tick * self.tick_seconds)
        return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def load_config(config_dir: Path) -> RunConfig:
    run = _read_yaml(config_dir / "run.yaml")
    start = datetime.fromisoformat(run["start_utc"]).astimezone(timezone.utc)
    components = [
        _load_component(config_dir / relative, run["incidents"])
        for relative in run["components"]
    ]
    kpi_config = _read_yaml(config_dir / "kpis.yaml")
    return RunConfig(run["seed"], start, run["tick_seconds"], run["ticks"], components,
                     kpi_config["kpis"], kpi_config["status_bands"])


def _read_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _load_component(path: Path, incidents: dict[str, Any]) -> Component:
    raw = _read_yaml(path)
    component = Component(
        id=raw["id"],
        name=raw["name"],
        stem=path.stem,
        resources=raw["resources"],
        metrics=[_load_metric(entry, path) for entry in raw["metrics"]],
        incidents=[(i["start_tick"], i["end_tick"]) for i in incidents[raw["id"]]],
    )
    _check_component(component, path)
    return component


def _load_metric(raw: dict[str, Any], path: Path) -> Metric:
    where = f"{path.name}: {raw['id']}"
    kind = raw["kind"]
    if kind not in REQUIRED_FIELDS:
        raise ConfigError(f"{where}: unknown kind {kind!r}")
    missing = [name for name in REQUIRED_FIELDS[kind] if name not in raw]
    if kind == "counter" and "inc_from" not in raw:
        missing += [name for name in ("normal_inc", "bad_inc") if name not in raw]
    if missing:
        raise ConfigError(f"{where}: missing {', '.join(missing)}")
    low, high = raw["official_range"]
    return Metric(
        id=raw["id"],
        level=raw["level"],
        kind=kind,
        period_min=raw["period_min"],
        decimals=raw["decimals"],
        range_low=low,
        range_high=high,
        params={key: value for key, value in raw.items() if key not in COMMON_FIELDS},
    )


def _check_component(component: Component, path: Path) -> None:
    names = [name for level in component.resources.values() for name in level]
    if len(names) != len(set(names)):
        raise ConfigError(f"{path.name}: resource names are not unique")
    by_id = {metric.id: metric for metric in component.metrics}
    if len(by_id) != len(component.metrics):
        raise ConfigError(f"{path.name}: metric ids are not unique")
    for metric in component.metrics:
        where = f"{path.name}: {metric.id}"
        if metric.level not in component.resources:
            raise ConfigError(f"{where}: unknown level {metric.level!r}")
        if (metric.kind == "flag" and metric.params["bad_resource"]
                not in component.resources[metric.level]):
            raise ConfigError(f"{where}: unknown bad_resource")
        if metric.kind == "counter" and "inc_from" in metric.params:
            source = by_id.get(metric.params["inc_from"])
            if (source is None or source.level != metric.level
                    or source.kind in ("counter", "derived")):
                raise ConfigError(
                    f"{where}: inc_from must be a random, constant or flag metric "
                    "of the same level")
