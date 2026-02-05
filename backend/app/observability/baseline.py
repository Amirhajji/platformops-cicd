# app/observability/baseline.py
import statistics
from sqlalchemy import text

DEFAULT_BASELINE_WINDOW = 200


def metric_baseline(db, component: str, column: str, window: int = DEFAULT_BASELINE_WINDOW):
    sql = text("""
        SELECT (payload ->> :column)::double precision AS v
        FROM timeseries_points
        WHERE component_code = :component
          AND payload ? :column
        ORDER BY tick DESC
        LIMIT :window
    """)

    rows = db.execute(
        sql,
        {
            "component": component,
            "column": column,
            "window": window,   # 🔒 ALWAYS BOUND
        },
    ).fetchall()

    values = [r.v for r in rows if r.v is not None]

    if len(values) < 5:
        return None

    mean = statistics.mean(values)
    p95 = statistics.quantiles(values, n=20)[18]
    max_v = max(values)

    return {
        "mean": mean,
        "p95": p95,
        "max": max_v,
    }
