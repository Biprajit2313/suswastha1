from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_current_user, hash_password, verify_password
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.user import (
    OTPRequest,
    SignupOTPRequest,
    Token,
    UserCreate,
    UserLogin,
    UserRead,
    VerifyLoginOTP,
    VerifySignupOTP,
)
from app.services.otp_service import OTPService

router = APIRouter(prefix="/api", tags=["auth"])
settings = get_settings()

class LoginOTPRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    purpose: str = Field(default="login", pattern="^(login)$")


@router.post("/signup", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def signup(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    repo = UserRepository(db)
    if repo.get_user_by_email(str(payload.email).lower()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    if payload.password is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use /api/auth/signup/request-otp and /api/auth/signup/verify for passwordless signup",
        )
    return repo.create_user(payload, hash_password(payload.password))


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> Token:
    user = UserRepository(db).get_user_by_email(str(payload.email).lower())
    if user is None or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return Token(access_token=create_access_token(subject=user.email))


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/auth/signup/request-otp")
def request_signup_otp(payload: SignupOTPRequest, request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    repo = UserRepository(db)
    if repo.get_user_by_email(str(payload.email).lower()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    OTPService(db).request_otp(
        email=str(payload.email).lower(),
        purpose="signup",
        client_ip=(request.client.host if request.client else None),
    )
    return {"message": "Verification code sent"}


@router.post("/auth/signup/verify", response_model=Token)
def verify_signup_otp(payload: VerifySignupOTP, db: Session = Depends(get_db)) -> Token:
    repo = UserRepository(db)
    email = str(payload.email).lower()
    if repo.get_user_by_email(email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    OTPService(db).verify_otp(email=email, purpose="signup", otp=payload.otp)
    user = repo.create_user(
        UserCreate(name=payload.name, email=payload.email, password=None, dob=payload.dob),
        hash_password(payload.password),
    )
    return Token(access_token=create_access_token(subject=user.email))


@router.post("/auth/login/request-otp")
def request_login_otp(payload: LoginOTPRequest, request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    email = str(payload.email).lower()
    user = UserRepository(db).get_user_by_email(email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")
    OTPService(db).request_otp(
        email=email,
        purpose="login",
        client_ip=(request.client.host if request.client else None),
    )
    return {"message": "Verification code sent"}


@router.post("/auth/login/verify", response_model=Token)
def verify_login_otp(payload: VerifyLoginOTP, db: Session = Depends(get_db)) -> Token:
    email = str(payload.email).lower()
    user = UserRepository(db).get_user_by_email(email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    OTPService(db).verify_otp(email=email, purpose="login", otp=payload.otp)
    return Token(access_token=create_access_token(subject=user.email))
