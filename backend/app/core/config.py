from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# argus/.env is the single source of truth for env vars shared by backend/
# and frontend/, regardless of the working directory the app is launched from.
_ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ROOT_ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    environment: str = "local"
    gcp_project_id: str = "argus-local-dev"
    firebase_project_id: str = "argus-local-dev"
    vertex_ai_location: str = "us-central1"
    gemini_live_model: str = "gemini-live-2.5-flash"
    cors_allow_origins: list[str] = ["http://localhost:3000"]
    gtfs_ch_static_feed_url: str = ""
    gtfs_ch_realtime_feed_url: str = ""
    gtfs_ch_auth_token: str = ""
    gtfs_mbta_static_feed_url: str = "https://cdn.mbta.com/MBTA_GTFS.zip"
    gtfs_mbta_realtime_feed_url: str = "https://cdn.mbta.com/realtime/TripUpdates.pb"
    gtfs_realtime_cache_ttl_seconds: float = 5.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
