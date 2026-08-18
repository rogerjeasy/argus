from fastapi.testclient import TestClient

from app.core.clients import get_firestore_client
from app.core.config import get_settings, Settings
from app.main import app
from app.tests.doubles.fake_firestore import FakeFirestoreClient


def _settings_with_secret(secret: str) -> Settings:
    return Settings(calibration_job_shared_secret=secret)


def test_run_calibration_rejects_missing_secret() -> None:
    app.dependency_overrides[get_settings] = lambda: _settings_with_secret("real-secret")
    app.dependency_overrides[get_firestore_client] = lambda: FakeFirestoreClient()
    client = TestClient(app)

    response = client.post("/internal/run-calibration")

    assert response.status_code == 403
    app.dependency_overrides.clear()


def test_run_calibration_rejects_wrong_secret() -> None:
    app.dependency_overrides[get_settings] = lambda: _settings_with_secret("real-secret")
    app.dependency_overrides[get_firestore_client] = lambda: FakeFirestoreClient()
    client = TestClient(app)

    response = client.post("/internal/run-calibration", headers={"X-Calibration-Secret": "wrong"})

    assert response.status_code == 403
    app.dependency_overrides.clear()


def test_run_calibration_accepts_correct_secret_and_reports_a_count() -> None:
    fake_db = FakeFirestoreClient()
    app.dependency_overrides[get_settings] = lambda: _settings_with_secret("real-secret")
    app.dependency_overrides[get_firestore_client] = lambda: fake_db
    client = TestClient(app)

    response = client.post("/internal/run-calibration", headers={"X-Calibration-Secret": "real-secret"})

    assert response.status_code == 200
    assert response.json() == {"proposals_created": 0}  # no users/history in a fresh fake db
    app.dependency_overrides.clear()
