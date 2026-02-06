from pydantic import BaseModel
from typing import Optional

class SignalOut(BaseModel):
    signal_code: str
    component_code: str
    signal_type: str
    unit: Optional[str] = None
    polarity: Optional[str] = None
    family: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True
