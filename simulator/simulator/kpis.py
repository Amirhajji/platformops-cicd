"""KPIs (y) and health scores (h): section 9 of the specification, rules 7 and 8.

KPIs are computed only from the written x values, read back from the x files.
"""
from __future__ import annotations

import ast
import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator

from .config import Component, ConfigError
from .expr import Evaluator, ExprError, Expression, GetLevel, GetValue

# compute(get, get_level) -> KPI value for one tick
Compute = Callable[[GetValue, GetLevel], float]


@dataclass(frozen=True)
class Kpi:
    component: str
    id: str
    good: float
    bad: float
    level: str
    inputs: frozenset[tuple[str, str]]  # (level, metric) read by compute
    compute: Compute


def health(value: float, good: float, bad: float) -> float:
    """0 at `bad` or worse, 100 at `good` or better, linear in between.

    The same formula works for both directions (good < bad or good > bad).
    """
    score = 100 * (value - bad) / (good - bad)
    return round(min(max(0.0, score), 100.0), 2)


class RatioExpression(Expression):
    """Part or total of a ratio KPI: metric ids of the level's single resource,
    sum(metric), count(level) and count(metric == number)."""

    def __init__(self, text: str, level: str, resource_count: int) -> None:
        self._level = level
        self._resource_count = resource_count
        super().__init__(text)

    def _compile_call(self, node: ast.Call) -> Evaluator:
        if isinstance(node.func, ast.Name) and len(node.args) == 1 and not node.keywords:
            argument, level = node.args[0], self._level
            if node.func.id == "sum" and isinstance(argument, ast.Name):
                metric = argument.id
                self.level_refs.add((level, metric))
                return lambda get, get_level: math.fsum(get_level(level, metric))
            if node.func.id == "count" and isinstance(argument, ast.Name):
                if argument.id != level:
                    raise ExprError(f"count({argument.id}) is not level {level!r}")
                count = self._resource_count
                return lambda get, get_level: count
            if node.func.id == "count" and isinstance(argument, ast.Compare):
                metric, number = self._parse_equality(argument)
                self.level_refs.add((level, metric))
                return lambda get, get_level: get_level(level, metric).count(number)
        raise ExprError(f"unsupported call in {self.text!r}")

    def _parse_equality(self, node: ast.Compare) -> tuple[str, float]:
        if (isinstance(node.left, ast.Name) and len(node.ops) == 1
                and isinstance(node.ops[0], ast.Eq)
                and isinstance(node.comparators[0], ast.Constant)
                and type(node.comparators[0].value) in (int, float)):
            return node.left.id, node.comparators[0].value
        raise ExprError(f"only metric == number is allowed in {self.text!r}")


def build_kpis(raw_kpis: list[dict[str, Any]], component: Component) -> list[Kpi]:
    """The KPIs of one component, in kpis.yaml order."""
    return [_build_kpi(raw, component) for raw in raw_kpis
            if raw["component"] == component.id]


def _build_kpi(raw: dict[str, Any], component: Component) -> Kpi:
    level, kind, source = raw["level"], raw["type"], raw["input"]
    where = f"kpis.yaml: {raw['id']}"
    resources = component.resources.get(level)
    if resources is None:
        raise ConfigError(f"{where}: unknown level {level!r}")
    if kind == "ratio":
        compute, names = _ratio(where, source, level, len(resources))
    elif kind in ("value", "average", "maximum"):
        metrics = source if isinstance(source, list) else [source]
        if kind == "value" and (len(metrics) != 1 or len(resources) != 1):
            raise ConfigError(f"{where}: value needs one metric of one resource")
        reduce = {"value": lambda values: values[0],
                  "average": lambda values: math.fsum(values) / len(values),
                  "maximum": max}[kind]
        names = set(metrics)

        def compute(get: GetValue, get_level: GetLevel) -> float:
            return reduce([value for metric in metrics
                           for value in get_level(level, metric)])
    else:
        raise ConfigError(f"{where}: unknown type {kind!r}")
    known = {metric.id for metric in component.metrics if metric.level == level}
    if not names <= known:
        raise ConfigError(f"{where}: unknown metrics {sorted(names - known)}")
    return Kpi(component.id, raw["id"], raw["good"], raw["bad"], level,
               frozenset((level, name) for name in names), compute)


def _ratio(where: str, source: dict[str, str], level: str,
           resource_count: int) -> tuple[Compute, set[str]]:
    part, total = (RatioExpression(source[key], level, resource_count)
                   for key in ("part", "total"))
    if resource_count != 1 and (part.names or total.names):
        raise ConfigError(f"{where}: a bare metric needs a level with one resource")

    def compute(get: GetValue, get_level: GetLevel) -> float:
        denominator = total.evaluate(get, get_level)
        if denominator == 0:
            # The specification defines no value for this case.
            raise ZeroDivisionError(f"{where}: the total of the ratio is 0")
        return part.evaluate(get, get_level) / denominator * 100

    names = part.names | total.names
    names |= {metric for _, metric in part.level_refs | total.level_refs}
    return compute, names


def compute_component(component: Component, kpis: list[Kpi],
                      x_path: Path) -> Iterator[list[tuple[float, float]]]:
    """For each tick of the x file: (value, health) of each KPI."""
    with x_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        position = {name: index for index, name in enumerate(next(reader))}
        indexes = {
            (level, metric): [position[f"{resource}.{metric}"]
                              for resource in component.resources[level]]
            for kpi in kpis for level, metric in kpi.inputs
        }
        for row in reader:
            values = {key: [float(row[index]) for index in found]
                      for key, found in indexes.items()}

            def get_level(level: str, metric: str) -> list[float]:
                return values[level, metric]

            result = []
            for kpi in kpis:
                value = kpi.compute(lambda metric: values[kpi.level, metric][0],
                                    get_level)
                result.append((value, health(value, kpi.good, kpi.bad)))
            yield result
