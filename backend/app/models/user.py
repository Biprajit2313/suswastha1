from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Integer, String

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    email_hash = Column(String(64), unique=True, index=True, nullable=True)
    encrypted_email = Column(String(1024), nullable=True)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=True)
    dob = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
