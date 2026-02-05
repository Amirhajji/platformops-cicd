# app/services/propagation_service.py
import numpy as np
from sqlalchemy.orm import Session
from app.services.timeseries_service import get_timeseries


def compute_propagation(
    db: Session,
    source_signal: str,
    target_signal: str,
    window: int = 30,
):
    src = get_timeseries(db, source_signal, None, None)
    tgt = get_timeseries(db, target_signal, None, None)

    if len(src) < window or len(tgt) < window:
        raise ValueError("Insufficient data for propagation analysis")

    # Align by tick
    src_values = np.array([p["value"] for p in src], dtype=float)
    tgt_values = np.array([p["value"] for p in tgt], dtype=float)

    # Remove NaNs
    mask = ~np.isnan(src_values) & ~np.isnan(tgt_values)
    src_values = src_values[mask]
    tgt_values = tgt_values[mask]

    # Normalize
    src_z = (src_values - src_values.mean()) / src_values.std()
    tgt_z = (tgt_values - tgt_values.mean()) / tgt_values.std()

    best_corr = 0.0
    best_lag = 0

    for lag in range(-window, window + 1):
        if lag < 0:
            corr = np.corrcoef(src_z[:lag], tgt_z[-lag:])[0, 1]
        elif lag > 0:
            corr = np.corrcoef(src_z[lag:], tgt_z[:-lag])[0, 1]
        else:
            corr = np.corrcoef(src_z, tgt_z)[0, 1]

        if abs(corr) > abs(best_corr):
            best_corr = corr
            best_lag = lag

    confidence = abs(best_corr) * (len(src_z) / len(src))

    classification = (
        "strong_positive_propagation"
        if best_corr > 0.7
        else "weak_or_no_propagation"
    )

    return {
        "source_signal": source_signal,
        "target_signal": target_signal,
        "window": window,
        "correlation": round(float(best_corr), 3),
        "lag_ticks": best_lag,
        "confidence": round(float(confidence), 3),
        "classification": classification,
    }
