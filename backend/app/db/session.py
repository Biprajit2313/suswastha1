from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy import inspect, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.base import Base

settings = get_settings()
logger = get_logger(__name__)


def _build_connect_args(database_url: str) -> dict:
    url = database_url.strip()
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    if url.startswith("postgresql"):
        # Supabase requires SSL. Prefer URL query param if provided; otherwise enforce.
        parsed = make_url(url)
        sslmode_in_url = "sslmode" in (parsed.query or {})
        if not sslmode_in_url:
            logger.warning("postgres_sslmode_missing_enforcing_require")
            return {"sslmode": "require"}
    return {}


try:
    # Validate URL early for readable failures.
    make_url(settings.normalized_database_url)
    connect_args = _build_connect_args(settings.normalized_database_url)
    engine = create_engine(
        settings.normalized_database_url,
        pool_recycle=3600,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
except Exception as e:
    logger.exception("database_engine_initialization_failed", extra={"error": str(e)})
    raise RuntimeError(
        "Failed to initialize database engine. Check DATABASE_URL format and reachability."
    ) from e

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    from app.models import otp, prediction, user  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_legacy_columns()


def test_database_connection() -> None:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("database_connected_successfully")
    except Exception as e:
        logger.exception("database_connection_failed", extra={"error": str(e)})
        raise


def _ensure_legacy_columns() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    dialect = engine.dialect.name

    def add_column(table: str, column: str, ddl: str) -> None:
        if table not in table_names:
            return
        existing = {item["name"] for item in inspector.get_columns(table)}
        if column in existing:
            return
        with engine.begin() as connection:
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))

    if dialect == "sqlite":
        add_column("users", "email_hash", "email_hash VARCHAR(64)")
        add_column("users", "encrypted_email", "encrypted_email VARCHAR(1024)")
        add_column("predictions", "recommendations", "recommendations TEXT")
    else:
        add_column("users", "email_hash", "email_hash VARCHAR(64) NULL")
        add_column("users", "encrypted_email", "encrypted_email VARCHAR(1024) NULL")
        add_column("predictions", "recommendations", "recommendations TEXT NULL")
