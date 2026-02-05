# app/ingestion/csv_loader.py
from pathlib import Path
import pandas as pd
import math
from sqlalchemy.orm import Session
from app.db.models.timeseries import TimeSeriesPoint



def _sanitize_payload(payload: dict) -> dict:
    """
    Convert NaN / inf values to None so JSONB is valid.
    """
    clean = {}
    for k, v in payload.items():
        if isinstance(v, float):
            if math.isnan(v) or math.isinf(v):
                clean[k] = None
            else:
                clean[k] = v
        else:
            clean[k] = v
    return clean


def load_csv_to_db(
    db: Session,
    csv_path: Path,
    component_code: str,
):
    df = pd.read_csv(csv_path)

    required_cols = {"tick", "timestamp"}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"{csv_path.name} missing required columns")

    records = []

    for _, row in df.iterrows():
        raw_payload = row.drop(labels=["tick", "timestamp"]).to_dict()
        payload = _sanitize_payload(raw_payload)

        records.append(
            TimeSeriesPoint(
                component_code=component_code,
                tick=int(row["tick"]),
                timestamp=int(row["timestamp"]),
                payload=payload,
            )
        )

    db.bulk_save_objects(records)
    db.commit()

    return len(records)
