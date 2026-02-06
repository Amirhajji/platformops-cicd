from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import get_db
from app.schemas.signal import SignalOut
from app.services.signal_service import list_signals

router = APIRouter(prefix="/api/signals", tags=["signals"])

@router.get("", response_model=List[SignalOut])
def get_signals(
    role: str = Query(..., regex="^(ops|architect|exec)$"),
    db: Session = Depends(get_db)
):
    return list_signals(db, role)
