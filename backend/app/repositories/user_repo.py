from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate
from app.services.encryption_service import EncryptionService


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.crypto = EncryptionService()

    def get_user_by_email(self, email: str) -> User | None:
        normalized = email.lower()
        email_hash = self.crypto.keyed_hash(normalized)
        user = (
            self.db.query(User)
            .filter((User.email_hash == email_hash) | (User.email == normalized))
            .first()
        )
        if user and (not user.email_hash or not user.encrypted_email):
            user.email_hash = user.email_hash or email_hash
            user.encrypted_email = user.encrypted_email or self.crypto.encrypt_text(normalized)
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        return user

    def create_user(self, payload: UserCreate, password_hash: str | None = None) -> User:
        normalized = str(payload.email).lower()
        user = User(
            name=payload.name,
            email=normalized,
            email_hash=self.crypto.keyed_hash(normalized),
            encrypted_email=self.crypto.encrypt_text(normalized),
            password_hash=password_hash,
            dob=payload.dob,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
