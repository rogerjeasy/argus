from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.calibration import router as calibration_router
from app.api.health import router as health_router
from app.api.webhooks import internal_router, router as webhooks_router
from app.api.settings import router as settings_router
from app.api.users import router as users_router
from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.ws.session import router as ws_router
from app.ws.twilio_media import router as twilio_media_router


def create_app() -> FastAPI:
    # Before anything else: the root logger is WARNING-with-no-handler by
    # default, which silently swallows every lifecycle log the WS session
    # emits. Cloud Run scrapes stdout into Cloud Logging, so this is what
    # makes the observability commitment real rather than declared.
    configure_logging()
    settings = get_settings()
    app = FastAPI(title="Argus Orchestrator")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(settings_router)
    app.include_router(users_router)
    app.include_router(ws_router)
    app.include_router(twilio_media_router)
    app.include_router(webhooks_router)
    app.include_router(internal_router)
    app.include_router(calibration_router)
    return app


app = create_app()
