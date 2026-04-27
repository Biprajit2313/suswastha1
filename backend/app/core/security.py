import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repo import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


def hash_password(password: str) -> str:
    if not password or not password.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password is required")
    import bcrypt

    password_bytes = password.strip().encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    # Support legacy SHA256 rows from older deployments.
    if password_hash and len(password_hash) == 64 and all(ch in "0123456789abcdef" for ch in password_hash.lower()):
        legacy_hash = hashlib.sha256(plain_password.strip().encode("utf-8")).hexdigest()
        return legacy_hash == password_hash

    try:
        import bcrypt

        return bcrypt.checkpw(
            plain_password.strip().encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except Exception:
        return False


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode: Dict[str, Any] = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    settings = get_settings()
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        email = payload.get("sub")
        if not isinstance(email, str) or not email:
            raise credentials_error
    except JWTError as exc:
        raise credentials_error from exc

    user = UserRepository(db).get_user_by_email(email)
    if user is None:
        raise credentials_error
    return user
