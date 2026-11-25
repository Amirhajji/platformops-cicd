"""Alert, incident and status rules of the loader (docs/PLATFORM_V1.md, section 3)."""
import pytest

from tools.load_simulation import Alert, find_alerts, merge_alerts, status_of

BANDS = {"healthy": [80, 100], "degraded": [50, 79.99], "critical": [0, 49.99]}


def spans(health):
    return [(a.start_tick, a.end_tick, a.min_health)
            for a in find_alerts("k", "C1", health)]


def test_alert_opens_below_50_and_closes_at_50():
    assert spans([100, 50, 49.99, 10, 50, 100]) == [(2, 3, 10)]


def test_alerts_at_both_ends_of_the_run():
    assert spans([0, 100, 100, 20, 30]) == [(0, 0, 0), (3, 4, 20)]


def test_no_alert():
    assert spans([100, 50, 50.01]) == []


def merged(*intervals):
    alerts = [Alert("k", "C1", start, end, 0) for start, end in intervals]
    z = [float(100 - tick) for tick in range(100)]
    return [(i.start_tick, i.end_tick, i.alert_count, i.min_z)
            for i in merge_alerts("C1", alerts, z)]


def test_overlapping_alerts_are_merged():
    assert merged((10, 30), (12, 20), (25, 40)) == [(10, 40, 3, 60)]


def test_alerts_five_ticks_apart_are_merged_and_six_are_not():
    assert merged((10, 20), (25, 30)) == [(10, 30, 2, 70)]
    assert merged((10, 20), (26, 30)) == [(10, 20, 1, 80), (26, 30, 1, 70)]


def test_a_short_alert_does_not_shorten_the_incident():
    assert merged((10, 50), (11, 12), (54, 60)) == [(10, 60, 3, 40)]


@pytest.mark.parametrize("z, expected", [
    (100, "healthy"), (80, "healthy"), (79.99, "degraded"), (50, "degraded"),
    (49.99, "critical"), (0, "critical")])
def test_status(z, expected):
    assert status_of(z, BANDS) == expected
