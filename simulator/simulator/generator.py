"""Metric generation (x): section 9 of the specification, rules 1 to 6."""
from __future__ import annotations

import hashlib
import random
from graphlib import CycleError, TopologicalSorter
from typing import Callable, Iterator

from .config import Component, ConfigError, Metric, RunConfig
from .expr import Expression

Key = tuple[str, str]  # (resource, metric id)
Update = Callable[[bool], float]  # bad -> new raw value


def make_rng(seed: int, component: str, resource: str, metric: str) -> random.Random:
    key = f"{seed}|{component}|{resource}|{metric}"
    return random.Random(int(hashlib.sha256(key.encode()).hexdigest()[:16], 16))


def output_value(metric: Metric, value: float) -> float:
    """The written value: clamped to the official range, then rounded."""
    if metric.range_low is not None:
        value = max(value, metric.range_low)
    if metric.range_high is not None:
        value = min(value, metric.range_high)
    return round(value, metric.decimals)


class ComponentGenerator:
    """Generates one component.

    _raw holds the unclamped, unrounded values (the state of counters). _written
    holds the clamped and rounded values: the output, and the only inputs of
    derived metrics, so that written parts add up to written totals.
    """

    def __init__(self, run: RunConfig, component: Component) -> None:
        self._run = run
        self._component = component
        self._raw: dict[Key, float] = {}
        self._written: dict[Key, float] = {}
        self._updates: list[tuple[Key, Metric, Update]] = [
            ((resource, metric.id), metric, self._make_update(metric, resource))
            for metric in self._update_order()
            for resource in component.resources[metric.level]
        ]

    def rows(self) -> Iterator[list[float]]:
        """One list of output values per tick, in Component.columns() order."""
        raw, written = self._raw, self._written
        columns = [(resource, metric.id)
                   for resource, metric in self._component.columns()]
        for tick in range(self._run.ticks):
            bad = self._component.is_bad(tick)
            for key, metric, update in self._updates:
                if tick % metric.period_min == 0:
                    raw[key] = update(bad)
                    written[key] = output_value(metric, raw[key])
            yield [written[key] for key in columns]

    def _update_order(self) -> list[Metric]:
        """random, constant and flag, then counters (inc_from reads the current
        value), then derived metrics after the metrics they reference."""
        metrics = self._component.metrics
        base = [m for m in metrics if m.kind not in ("counter", "derived")]
        counters = [m for m in metrics if m.kind == "counter"]
        return base + counters + self._derived_order()

    def _derived_order(self) -> list[Metric]:
        by_id = {m.id: m for m in self._component.metrics}
        graph: dict[str, list[str]] = {}
        for metric in self._component.metrics:
            if metric.kind != "derived":
                continue
            expression = Expression(metric.params["expr"])
            used = ([(metric.level, name) for name in expression.names]
                    + list(expression.level_refs))
            for level, name in used:
                if name not in by_id or by_id[name].level != level:
                    raise ConfigError(
                        f"{self._component.id} {metric.id}: "
                        f"no metric {name!r} at level {level!r}")
            # Sorted, so that the order never depends on set iteration.
            graph[metric.id] = sorted(
                name for _, name in used if by_id[name].kind == "derived")
        try:
            order = list(TopologicalSorter(graph).static_order())
        except CycleError as error:
            raise ConfigError(
                f"{self._component.id}: circular derived metrics") from error
        return [by_id[name] for name in order]

    def _make_update(self, metric: Metric, resource: str) -> Update:
        params = metric.params
        key = (resource, metric.id)
        raw = self._raw

        if metric.kind == "random":
            return self._make_draw(metric, resource, "normal", "bad")

        if metric.kind == "constant":
            value = params["value"]
            return lambda bad: value

        if metric.kind == "flag":
            healthy = params["healthy"]
            in_incident = (params["unhealthy"] if resource == params["bad_resource"]
                           else healthy)
            return lambda bad: in_incident if bad else healthy

        if metric.kind == "counter":
            start = params["start"]
            if "inc_from" in params:
                source = (resource, params["inc_from"])
                return lambda bad: raw.get(key, start) + raw[source]
            draw = self._make_draw(metric, resource, "normal_inc", "bad_inc")
            return lambda bad: raw.get(key, start) + draw(bad)

        # derived
        evaluate = Expression(params["expr"]).evaluate
        written = self._written
        resources = self._component.resources

        def get(name: str) -> float:
            return written[resource, name]

        def get_level(level: str, name: str) -> list[float]:
            return [written[other, name] for other in resources[level]]

        return lambda bad: evaluate(get, get_level)

    def _make_draw(self, metric: Metric, resource: str,
                   normal_field: str, bad_field: str) -> Update:
        rng = make_rng(self._run.seed, self._component.id, resource, metric.id)
        normal, in_incident = metric.params[normal_field], metric.params[bad_field]
        return lambda bad: rng.uniform(*(in_incident if bad else normal))
