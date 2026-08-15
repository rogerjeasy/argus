from fastapi.testclient import TestClient

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.clients import get_firestore_client
from app.main import app
from app.tests.doubles.fake_firestore import FakeFirestoreClient


def _client() -> TestClient:
    fake_db = FakeFirestoreClient()
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(uid="user-1", email=None)
    app.dependency_overrides[get_firestore_client] = lambda: fake_db
    return TestClient(app)


def test_get_settings_returns_defaults_when_unset() -> None:
    client = _client()
    response = client.get("/api/settings")
    assert response.status_code == 200
    assert response.json() == {"verbosity": "normal", "pace": "normal"}


def test_put_settings_persists_partial_update() -> None:
    client = _client()
    response = client.put("/api/settings", json={"verbosity": "terse"})
    assert response.status_code == 200
    assert response.json() == {"verbosity": "terse", "pace": "normal"}

    follow_up = client.get("/api/settings")
    assert follow_up.json() == {"verbosity": "terse", "pace": "normal"}


def test_settings_writes_to_argus_prefixed_collection() -> None:
    fake_db = FakeFirestoreClient()
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(uid="user-1", email=None)
    app.dependency_overrides[get_firestore_client] = lambda: fake_db
    client = TestClient(app)

    client.put("/api/settings", json={"verbosity": "terse"})

    stored_keys = [k for k in fake_db._store if k[0] == "argus_users"]
    assert len(stored_keys) == 1
