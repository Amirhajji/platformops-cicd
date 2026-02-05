# app/api/patterns.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.patterns_service import detect_spikes, detect_recovery

router = APIRouter(prefix="/api/analytics/patterns", tags=["Patterns"])


@router.get("/spikes")
def spikes(db: Session = Depends(get_db)):
    return detect_spikes(db)


@router.get("/recovery")
def recovery(db: Session = Depends(get_db)):
    return detect_recovery(db)
