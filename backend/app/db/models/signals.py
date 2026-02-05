# app/db/models/signals.py
from sqlalchemy import Column, Text, ARRAY
from app.db.base import Base

class Signal(Base):
    __tablename__ = "signals"

    signal_code = Column(Text, primary_key=True)
    component_code = Column(Text, nullable=False)
    column_name = Column(Text, nullable=False)
    signal_type = Column(Text, nullable=False)
    unit = Column(Text)
    polarity = Column(Text)
    description = Column(Text)
    visible_to_roles = Column(ARRAY(Text))
    family = Column(Text)
