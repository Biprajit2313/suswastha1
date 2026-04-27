from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, image_prediction, prediction, reports
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.middleware import SecurityHeadersMiddleware
from app.db.session import init_db, test_database_connection

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
    )

    # CORS MUST be added before any custom middleware.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://biprajit2313.github.io",
            "http://localhost:5500",
            "http://127.0.0.1:5500",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # Add security headers middleware AFTER CORS
    application.add_middleware(SecurityHeadersMiddleware)

    # Register API routes
    application.include_router(auth.router)
    application.include_router(prediction.router)
    application.include_router(image_prediction.router)
    application.include_router(reports.router)

    @application.get("/")
    def root() -> dict:
        return {"status": "ok"}

    @application.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @application.on_event("startup")
    def on_startup() -> None:
        init_db()
        test_database_connection()
        logger.info(
            "application_started",
            extra={"environment": settings.environment},
        )

    return application


app = create_app()
