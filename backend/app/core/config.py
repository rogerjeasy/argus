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
    #: Full resource name: projects/.../locations/.../keyRings/.../cryptoKeys/...
    #: Empty means "no KMS key provisioned yet" — MemoryAgent then stores
    #: personal_admin profile fields as plaintext rather than failing, the
    #: same graceful-degradation posture every other optional integration
    #: in this project already takes.
    kms_key_name: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    twilio_test_ivr_number: str = ""
    cloud_tasks_queue: str = "argus-call-retries"
    cloud_tasks_location: str = "us-central1"
    #: Public base URL this backend is reachable at — Twilio's Media Stream
    #: and status-callback webhook both need a real, internet-reachable URL
    #: to call back into (e.g. the Cloud Run service URL, or an ngrok URL
    #: for local dev against a real Twilio account). Empty is fine until
    #: Task 9+ actually places a real call.
    public_base_url: str = ""
    #: Empty by default (Phase 3b, matches the twilio_* fields' pattern) —
    #: nothing in the build is blocked on a real bucket existing yet.
    #: build_orchestrator only registers FormExecutor when this is set.
    personal_admin_storage_bucket: str = ""

    #: Empty defaults to a signage-only demo venue with zero configuration —
    #: see app/domains/indoor_wayfinding/config.py.
    indoor_wayfinding_venue_id: str = ""
    indoor_wayfinding_directory_url: str = ""

    #: Shared secret Cloud Scheduler sends as X-Calibration-Secret when it
    #: invokes /internal/run-calibration. Empty means the endpoint always
    #: rejects (fail-closed, not fail-open) — see app/api/calibration.py.
    calibration_job_shared_secret: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
