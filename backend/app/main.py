from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.settings import router as settings_router
from app.core.config import get_settings
from app.ws.session import router as ws_router


def create_app() -> FastAPI:
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
    app.include_router(ws_router)
    return app


app = create_app()
