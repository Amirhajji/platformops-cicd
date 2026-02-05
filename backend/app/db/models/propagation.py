# app/db/models/propagation.py
from sqlalchemy import Column, Integer, Text, Float
from app.db.base import Base

class SignalDependency(Base):
    __tablename__ = "signal_dependencies"

    source_signal = Column(Text, primary_key=True)
    target_signal = Column(Text, primary_key=True)
    relationship = Column(Text)  # FORMULA | PROPAGATION


class PropagationEvidence(Base):
    __tablename__ = "propagation_evidence"

    id = Column(Integer, primary_key=True)
    source_signal = Column(Text, nullable=False)
    target_signal = Column(Text, nullable=False)
    lag_ticks = Column(Integer)
    correlation = Column(Float)
    confidence_score = Column(Float)
