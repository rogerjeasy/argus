from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "local"
    gcp_project_id: str = "argus-local-dev"
    firebase_project_id: str = "argus-local-dev"
    vertex_ai_location: str = "us-central1"
    gemini_live_model: str = "gemini-live-2.5-flash"
    cors_allow_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
