from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.otp import OTPChallenge


class OTPRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def count_recent_requests(self, *, email_hash: str, purpose: str, since: datetime) -> int:
        return (
            self.db.query(OTPChallenge)
            .filter(
                OTPChallenge.email_hash == email_hash,
                OTPChallenge.purpose == purpose,
                OTPChallenge.created_at >= since,
            )
            .count()
        )

    def create_challenge(
        self,
        *,
        email_hash: str,
        otp_hash: str,
        purpose: str,
        expires_at: datetime,
    ) -> OTPChallenge:
        challenge = OTPChallenge(
            email_hash=email_hash,
            otp_hash=otp_hash,
            purpose=purpose,
            expires_at=expires_at,
        )
        self.db.add(challenge)
        self.db.commit()
        self.db.refresh(challenge)
        return challenge

    def latest_active(self, *, email_hash: str, purpose: str, now: datetime) -> OTPChallenge | None:
        return (
            self.db.query(OTPChallenge)
            .filter(
                OTPChallenge.email_hash == email_hash,
                OTPChallenge.purpose == purpose,
                OTPChallenge.expires_at > now,
                OTPChallenge.consumed_at.is_(None),
            )
            .order_by(OTPChallenge.created_at.desc())
            .first()
        )

    def mark_consumed(self, challenge: OTPChallenge, now: datetime) -> None:
        challenge.consumed_at = now
        self.db.add(challenge)
        self.db.commit()

    def increment_attempts(self, challenge: OTPChallenge) -> None:
        challenge.attempts += 1
        self.db.add(challenge)
        self.db.commit()

    def delete_expired(self, older_than: datetime | None = None) -> None:
        cutoff = older_than or (datetime.utcnow() - timedelta(days=1))
        self.db.query(OTPChallenge).filter(OTPChallenge.expires_at < cutoff).delete()
        self.db.commit()
