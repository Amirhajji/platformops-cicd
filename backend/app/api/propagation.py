# app/api/propagation.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.propagation_service import compute_propagation

router = APIRouter(prefix="/api/propagation", tags=["propagation"])


@router.get("")
def propagation(
    source_signal: str,
    target_signal: str,
    window: int = 30,
    db: Session = Depends(get_db),
):
    try:
        return compute_propagation(
            db=db,
            source_signal=source_signal,
            target_signal=target_signal,
            window=window,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
