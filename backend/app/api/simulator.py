# app/api/simulator.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter(prefix="/api/simulator", tags=["Simulator"])


@router.get("/state")
def simulator_state(tick: int, db: Session = Depends(get_db)):
    sql = """
    SELECT component_code, payload
    FROM timeseries_points
    WHERE tick = :tick
    """

    rows = db.execute(text(sql), {"tick": tick}).fetchall()

    state = {}

    for r in rows:
        if r.component_code not in state:
            state[r.component_code] = {}
        state[r.component_code].update(r.payload)

    return {
        "tick": tick,
        "state": state
    }
