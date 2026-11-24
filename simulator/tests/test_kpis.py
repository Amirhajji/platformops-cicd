import pytest

from simulator.config import Component, ConfigError, Metric
from simulator.expr import ExprError
from simulator.kpis import build_kpis, compute_component, health
from simulator.kqis import compute_kqi, status

BANDS = {"healthy": [80, 100], "degraded": [50, 79.99], "critical": [0, 49.99]}


# --- health ------------------------------------------------------------------

@pytest.mark.parametrize("value, expected", [
    (60, 100), (90, 0), (75, 50), (84, 20), (10, 100), (99, 0)])
def test_health_lower_is_better(value, expected):
    assert health(value, good=60, bad=90) == expected


@pytest.mark.parametrize("value, expected", [
    (95, 100), (80, 0), (87.5, 50), (83, 20), (99, 100), (10, 0)])
def test_health_higher_is_better(value, expected):
    assert health(value, good=95, bad=80) == expected


def test_health_is_rounded_and_never_negative_zero():
    assert health(200 / 3, good=100, bad=66) == 1.96
    assert str(health(90, good=60, bad=90)) == "0.0"


def test_health_worked_example_of_the_specification():
    scores = [health(40, 60, 90), health(74, 70, 90), health(97, 95, 80),
              health(0.055, 0.01, 0.1), health(65, 70, 90)]
    assert scores == [100, 80, 100, 50, 100]
    assert compute_kqi([scores], BANDS).overall == 86


# --- KPI types ---------------------------------------------------------------

def metric(name, level):
    return Metric(name, level, "count", "constant", 1, 0, 0, None, {"value": 0})


COMPONENT = Component(
    id="T", name="Test", stem="T_test",
    resources={"broker": ["b1", "b2", "b3"], "bucket": ["bk"]},
    metrics=[metric("alive", "broker"), metric("load", "broker"),
             *(metric(name, "bucket") for name in ("err4", "err5", "get", "put"))],
    incidents=[])

X_FILE = """\
tick,timestamp_utc,b1.alive,b1.load,b2.alive,b2.load,b3.alive,b3.load,bk.err4,bk.err5,bk.get,bk.put
0,2026-11-01T00:00:00Z,1,30,1,40,1,50,0,0,80,20
1,2026-11-01T00:01:00Z,1,10,1,20,0,90,3,2,60,40
"""


def values(tmp_path, kind, level, source):
    path = tmp_path / "x.csv"
    path.write_text(X_FILE, encoding="utf-8")
    kpis = build_kpis([{"component": "T", "id": "k", "type": kind, "level": level,
                        "input": source, "good": 0, "bad": 100}], COMPONENT)
    return [tick[0][0] for tick in compute_component(COMPONENT, kpis, path)]


def test_average(tmp_path):
    assert values(tmp_path, "average", "broker", "load") == [40, 40]


def test_maximum_over_resources(tmp_path):
    assert values(tmp_path, "maximum", "broker", "load") == [50, 90]


def test_maximum_over_metrics(tmp_path):
    assert values(tmp_path, "maximum", "bucket", ["err4", "err5"]) == [0, 3]


def test_value(tmp_path):
    assert values(tmp_path, "value", "bucket", "get") == [80, 60]


def test_ratio_of_sums_of_metrics(tmp_path):
    source = {"part": "err4 + err5", "total": "get + put"}
    assert values(tmp_path, "ratio", "bucket", source) == [0, 5]


def test_ratio_sum_over_count(tmp_path):
    source = {"part": "sum(alive)", "total": "count(broker)"}
    assert values(tmp_path, "ratio", "broker", source) == [
        100, pytest.approx(200 / 3)]


def test_ratio_conditional_count(tmp_path):
    source = {"part": "count(alive == 0)", "total": "count(broker)"}
    assert values(tmp_path, "ratio", "broker", source) == [
        0, pytest.approx(100 / 3)]


def test_ratio_with_zero_total_stops(tmp_path):
    with pytest.raises(ZeroDivisionError, match="total of the ratio is 0"):
        values(tmp_path, "ratio", "bucket", {"part": "get", "total": "err4"})


@pytest.mark.parametrize("part", [
    "eval('1')", "max(alive)", "count(alive > 0)", "count(bucket)", "alive.real"])
def test_unsafe_ratio_is_rejected(tmp_path, part):
    with pytest.raises(ExprError):
        values(tmp_path, "ratio", "broker", {"part": part, "total": "count(broker)"})


@pytest.mark.parametrize("kind, level, source", [
    ("value", "broker", "load"),  # several resources
    ("median", "broker", "load"),
    ("average", "nowhere", "load"),
    ("average", "broker", "missing"),
    ("ratio", "broker", {"part": "load", "total": "count(broker)"}),
])
def test_invalid_kpi_is_rejected(tmp_path, kind, level, source):
    with pytest.raises(ConfigError):
        values(tmp_path, kind, level, source)


# --- KQIs --------------------------------------------------------------------

def test_kqi_is_the_mean_of_health_and_global_the_mean_of_components():
    kqi = compute_kqi([[100, 50], [0, 100, 0], [20, 40]], BANDS)
    assert kqi.components == [75, 33.33, 30]
    assert kqi.overall == 46.11  # 138.33 / 3
    assert kqi.status == "critical"


@pytest.mark.parametrize("score, expected", [
    (100, "healthy"), (80, "healthy"), (79.99, "degraded"), (50, "degraded"),
    (49.99, "critical"), (0, "critical")])
def test_status_bands(score, expected):
    assert status(score, BANDS) == expected
