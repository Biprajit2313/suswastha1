from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str | None = Field(default=None, min_length=6, max_length=128)
    dob: date | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserRead(BaseModel):
    id: int
    name: str
    email: EmailStr
    dob: date | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class OTPRequest(BaseModel):
    email: EmailStr
    purpose: str = Field(default="login", pattern="^(signup|login)$")


class SignupOTPRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=6, max_length=128)
    dob: date | None = None


class VerifySignupOTP(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)
    name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=6, max_length=128)
    dob: date | None = None


class VerifyLoginOTP(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)
