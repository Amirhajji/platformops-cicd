# app/ingestion/ingest_cli.py
from pathlib import Path
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.ingestion.csv_loader import load_csv_to_db

CSV_ROOT = Path(
    r"C:\Users\h50048240\3D Objects\PlatformOPS\simulator\output\csv"
)

COMPONENT_FILES = {
    "C1": "c1.csv",
    "C2": "c2.csv",
    "C3": "c3.csv",
    "C4": "c4.csv",
    "C5": "c5.csv",
    "C6": "c6.csv",
    "C7": "c7.csv",
    "C8": "c8.csv",
    "C9": "c9.csv",
    "GLOBAL": "global.csv",
}


def run_ingestion():
    db: Session = SessionLocal()

    try:
        for component, filename in COMPONENT_FILES.items():
            csv_path = CSV_ROOT / filename
            if not csv_path.exists():
                raise FileNotFoundError(csv_path)

            count = load_csv_to_db(db, csv_path, component)
            print(f"[OK] {component}: {count} rows ingested")

    finally:
        db.close()


if __name__ == "__main__":
    run_ingestion()
