from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "SuSwastha API"
    app_version: str = "2.0.0"
    environment: str = "development"
    log_level: str = "INFO"

    database_url: str = Field(default="", validation_alias="DATABASE_URL")

    # SECURITY: Never ship a default SECRET_KEY. This must be provided via environment.
    secret_key: str = Field(default="", validation_alias="SECRET_KEY")
    fernet_key: str = Field(default="", validation_alias="FERNET_KEY")
    algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=60 * 24, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    force_https: bool = Field(default=False, validation_alias="FORCE_HTTPS")

    ml_models_dir: Path = Field(default=BACKEND_DIR.parent / "models", validation_alias="ML_MODELS_DIR")

    cloudinary_cloud_name: str = Field(default="", validation_alias="CLOUDINARY_CLOUD_NAME")
    cloudinary_api_key: str = Field(default="", validation_alias="CLOUDINARY_API_KEY")
    cloudinary_api_secret: str = Field(default="", validation_alias="CLOUDINARY_API_SECRET")
    cloudinary_folder: str = Field(default="suswastha/reports", validation_alias="CLOUDINARY_FOLDER")

    smtp_host: str = Field(default="smtp.gmail.com", validation_alias="SMTP_HOST")
    smtp_port: int = Field(default=587, validation_alias="SMTP_PORT")
    smtp_user: str = Field(default="", validation_alias="SMTP_USER")
    smtp_password: str = Field(default="", validation_alias="SMTP_PASS")
    smtp_from_email: str = Field(default="", validation_alias="SMTP_FROM_EMAIL")
    smtp_use_tls: bool = Field(default=True, validation_alias="SMTP_USE_TLS")

    otp_expire_minutes: int = Field(default=5, validation_alias="OTP_EXPIRE_MINUTES")
    otp_request_limit: int = Field(default=5, validation_alias="OTP_REQUEST_LIMIT")
    otp_request_window_minutes: int = Field(default=15, validation_alias="OTP_REQUEST_WINDOW_MINUTES")
    otp_ip_request_limit: int = Field(default=20, validation_alias="OTP_IP_REQUEST_LIMIT")
    otp_ip_request_window_minutes: int = Field(default=15, validation_alias="OTP_IP_REQUEST_WINDOW_MINUTES")

    cors_allowed_origins: str = Field(
        default=(
            "https://biprajit2313.github.io,"
            "https://biprajit2313.github.io/SuSwastha,"
            "http://localhost,http://127.0.0.1,"
            "http://localhost:5500,http://127.0.0.1:5500"
        ),
        validation_alias="CORS_ALLOWED_ORIGINS",
    )

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    @property
    def normalized_database_url(self) -> str:
        raw = (self.database_url or "").strip()
        if not raw:
            raise ValueError(
                "DATABASE_URL is required. Set it to your Supabase PostgreSQL connection string "
                "(for example: postgresql://...)."
            )

        # Normalize common variants for SQLAlchemy dialect resolution.
        if raw.startswith("postgres://"):
            raw = raw.replace("postgres://", "postgresql://", 1)
        if raw.startswith("mysql://"):
            raw = raw.replace("mysql://", "mysql+mysqlconnector://", 1)

        return raw

    @property
    def normalized_ml_models_dir(self) -> Path:
        raw_path = Path(self.ml_models_dir)
        if raw_path.is_absolute():
            return raw_path
        project_root = BACKEND_DIR.parent
        return (project_root / raw_path).resolve()

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() in {"production", "prod"}

    @model_validator(mode="after")
    def validate_required_secrets(self) -> "Settings":
        # Always require SECRET_KEY; it's used for JWT signing and keyed hashing.
        if not self.secret_key or not self.secret_key.strip():
            raise ValueError("SECRET_KEY is required (must be set via environment variables).")

        # In production, require integrations to be configured explicitly.
        if self.is_production:
            missing: list[str] = []
            if not self.cloudinary_cloud_name.strip():
                missing.append("CLOUDINARY_CLOUD_NAME")
            if not self.cloudinary_api_key.strip():
                missing.append("CLOUDINARY_API_KEY")
            if not self.cloudinary_api_secret.strip():
                missing.append("CLOUDINARY_API_SECRET")
            if missing:
                raise ValueError(
                    "Missing required environment variables for production: " + ", ".join(missing)
                )

        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
