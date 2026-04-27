from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.db.base import Base


class OTPChallenge(Base):
    __tablename__ = "otp_challenges"

    id = Column(Integer, primary_key=True, index=True)
    email_hash = Column(String(64), index=True, nullable=False)
    otp_hash = Column(String(255), nullable=False)
    purpose = Column(String(32), index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    consumed_at = Column(DateTime, nullable=True)
    attempts = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
