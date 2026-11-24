"""KQIs (z): section 9 of the specification, rule 9."""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Kqi:
    components: list[float]  # z_C1 ... z_C8
    overall: float  # Z
    status: str


def mean(scores: list[float]) -> float:
    """Mean of scores, with 2 decimals (the precision of the status bands)."""
    return round(math.fsum(scores) / len(scores), 2)


def status(score: float, bands: dict[str, list[float]]) -> str:
    """The band with the highest lower bound that the score reaches."""
    reached = [(low, name) for name, (low, _) in bands.items() if score >= low]
    return max(reached)[1]


def compute_kqi(health_by_component: list[list[float]],
                bands: dict[str, list[float]]) -> Kqi:
    """KQIs of one tick, from the KPI health scores of each component."""
    components = [mean(scores) for scores in health_by_component]
    overall = mean(components)
    return Kqi(components, overall, status(overall, bands))
