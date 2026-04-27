from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.db.base import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(255), index=True, nullable=False)
    test_type = Column(String(64), nullable=False)
    raw_input = Column(Text, nullable=False)
    label = Column(String(64), nullable=False)
    risk_score = Column(Float, nullable=False)
    recommendations = Column(Text, nullable=True)
    pdf_url = Column("pdf_path", String(1024), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
