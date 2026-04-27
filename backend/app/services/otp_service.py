import secrets
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import otp_ip_limiter
from app.repositories.otp_repo import OTPRepository
from app.services.email_service import EmailService
from app.services.encryption_service import EncryptionService


class OTPService:
    def __init__(self, db: Session, email_service: EmailService | None = None) -> None:
        self.db = db
        self.repo = OTPRepository(db)
        self.crypto = EncryptionService()
        self.email_service = email_service or EmailService()

    def request_otp(self, *, email: str, purpose: str, client_ip: str | None = None) -> None:
        settings = get_settings()
        now = datetime.utcnow()

        if client_ip:
            allowed = otp_ip_limiter.allow(
                key=f"otp_ip:{client_ip}:{purpose}",
                limit=settings.otp_ip_request_limit,
                window_seconds=settings.otp_ip_request_window_minutes * 60,
            )
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many OTP requests from this network. Please wait before trying again.",
                )

        email_hash = self.crypto.keyed_hash(email)
        since = now - timedelta(minutes=settings.otp_request_window_minutes)
        recent = self.repo.count_recent_requests(email_hash=email_hash, purpose=purpose, since=since)
        if recent >= settings.otp_request_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many OTP requests. Please wait before trying again.",
            )

        otp = f"{secrets.randbelow(1_000_000):06d}"
        import bcrypt

        self.repo.create_challenge(
            email_hash=email_hash,
            otp_hash=bcrypt.hashpw(otp.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
            purpose=purpose,
            expires_at=now + timedelta(minutes=settings.otp_expire_minutes),
        )
        self.email_service.send_otp_email(to_email=email, otp=otp, purpose=purpose)

    def verify_otp(self, *, email: str, purpose: str, otp: str) -> None:
        now = datetime.utcnow()
        email_hash = self.crypto.keyed_hash(email)
        challenge = self.repo.latest_active(email_hash=email_hash, purpose=purpose, now=now)
        if challenge is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP expired or not found")
        if challenge.attempts >= 5:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many OTP attempts")
        import bcrypt

        if not bcrypt.checkpw(otp.encode("utf-8"), challenge.otp_hash.encode("utf-8")):
            self.repo.increment_attempts(challenge)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP")
        self.repo.mark_consumed(challenge, now)
