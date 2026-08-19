from fastapi.testclient import TestClient

from app.api.daily_briefing import _get_transit_domains_dep
from app.core.clients import get_firestore_client
from app.core.config import get_settings, Settings
from app.domains.transit.config import TransitFeedConfig
from app.domains.transit.domain import TransitDomain
from app.domains.transit.static_index import GtfsStaticIndex
from app.main import app
from app.tests.doubles.fake_firestore import FakeFirestoreClient
from app.tests.fixtures.gtfs_builders import build_static_feed_zip

_CONFIG = TransitFeedConfig(
    domain_id="transit-ch", display_name="Switzerland", static_feed_url="", realtime_feed_url="",
    auth_header=None, locale="de-CH",
)


class _NoAlertPoller:
    async def latest_for(self, trip_id, candidate_stop_ids):
        return None

    async def latest_alert_for(self, trip_id, candidate_stop_ids):
        return None


def _fake_transit_domain() -> TransitDomain:
    static_index = GtfsStaticIndex(build_static_feed_zip(
        [{"stop_id": "s1", "stop_name": "Zürich HB", "platform_code": "", "parent_station": ""}],
        [{"trip_id": "t1", "stop_id": "s1", "arrival_time": "09:00:00", "stop_sequence": "1"}],
    ))
    return TransitDomain(_CONFIG, static_index, _NoAlertPoller())


def _settings_with_secret(secret: str) -> Settings:
    return Settings(daily_briefing_job_shared_secret=secret)


def test_run_daily_briefing_rejects_missing_secret() -> None:
    app.dependency_overrides[get_settings] = lambda: _settings_with_secret("real-secret")
    app.dependency_overrides[get_firestore_client] = lambda: FakeFirestoreClient()
    app.dependency_overrides[_get_transit_domains_dep] = lambda: [_fake_transit_domain()]
    client = TestClient(app)

    response = client.post("/internal/run-daily-briefing")

    assert response.status_code == 403
    app.dependency_overrides.clear()


def test_run_daily_briefing_rejects_wrong_secret() -> None:
    app.dependency_overrides[get_settings] = lambda: _settings_with_secret("real-secret")
    app.dependency_overrides[get_firestore_client] = lambda: FakeFirestoreClient()
    app.dependency_overrides[_get_transit_domains_dep] = lambda: [_fake_transit_domain()]
    client = TestClient(app)

    response = client.post("/internal/run-daily-briefing", headers={"X-Daily-Briefing-Secret": "wrong"})

    assert response.status_code == 403
    app.dependency_overrides.clear()


def test_run_daily_briefing_accepts_correct_secret_and_reports_a_count() -> None:
    fake_db = FakeFirestoreClient()
    app.dependency_overrides[get_settings] = lambda: _settings_with_secret("real-secret")
    app.dependency_overrides[get_firestore_client] = lambda: fake_db
    app.dependency_overrides[_get_transit_domains_dep] = lambda: [_fake_transit_domain()]
    client = TestClient(app)

    response = client.post("/internal/run-daily-briefing", headers={"X-Daily-Briefing-Secret": "real-secret"})

    assert response.status_code == 200
    assert response.json() == {"briefings_created": 0}  # no users/routes in a fresh fake db
    app.dependency_overrides.clear()
