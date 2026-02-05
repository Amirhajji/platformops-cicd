# app/observability/family_thresholds.py

def thresholds_for_family(family: str):
    """
    Returns (operator, warning_threshold, critical_threshold)
    """

    # F1 — Utilization (bounded)
    if family == "utilization":
        return "gt", 75, 90

    # F2 — Throughput / rate (low is bad)
    if family == "throughput":
        return "lt", 0.6, 0.4   # % of baseline (handled later)

    # F3 — Queue / backlog
    if family == "backlog":
        return "gt", 2.0, 4.0   # σ multipliers

    # F4 — Latency
    if family == "latency":
        return "gt", 3.0, 6.0   # σ multipliers

    # F5 — Error rate
    if family == "error_rate":
        return "gt", 0.01, 0.05

    # F6 — Count / cardinality
    if family == "count":
        return "gt", 1.3, 1.6   # × baseline

    # F7 — Control / events (your rule ❤️)
    if family == "events":
        return "gte", 1, 3

    # safety net
    return "gt", 999999, 999999
