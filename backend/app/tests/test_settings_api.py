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
    assert response.json() == {
        "verbosity": "normal", "pace": "normal", "audio_perception_enabled": False, "language_preference": "en",
    }


def test_put_settings_persists_partial_update() -> None:
    client = _client()
    response = client.put("/api/settings", json={"verbosity": "terse"})
    assert response.status_code == 200
    assert response.json() == {
        "verbosity": "terse", "pace": "normal", "audio_perception_enabled": False, "language_preference": "en",
    }

    follow_up = client.get("/api/settings")
    assert follow_up.json() == {
        "verbosity": "terse", "pace": "normal", "audio_perception_enabled": False, "language_preference": "en",
    }


def test_put_settings_can_enable_audio_perception() -> None:
    client = _client()
    response = client.put("/api/settings", json={"audio_perception_enabled": True})
    assert response.status_code == 200
    assert response.json() == {
        "verbosity": "normal", "pace": "normal", "audio_perception_enabled": True, "language_preference": "en",
    }


def test_get_settings_defaults_to_english() -> None:
    client = _client()
    response = client.get("/api/settings")
    assert response.json()["language_preference"] == "en"


def test_put_settings_can_set_language_preference() -> None:
    client = _client()
    response = client.put("/api/settings", json={"language_preference": "ar"})
    assert response.status_code == 200
    assert response.json()["language_preference"] == "ar"

    follow_up = client.get("/api/settings")
    assert follow_up.json()["language_preference"] == "ar"


def test_put_settings_can_explicitly_disable_audio_perception_after_enabling() -> None:
    """exclude_none=True (UserSettingsUpdate's existing pattern in
    update_user_settings) must still allow explicitly setting False —
    False is not None, so this must not be silently dropped."""
    client = _client()
    client.put("/api/settings", json={"audio_perception_enabled": True})

    response = client.put("/api/settings", json={"audio_perception_enabled": False})

    assert response.json()["audio_perception_enabled"] is False


def test_settings_writes_to_argus_prefixed_collection() -> None:
    fake_db = FakeFirestoreClient()
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(uid="user-1", email=None)
    app.dependency_overrides[get_firestore_client] = lambda: fake_db
    client = TestClient(app)

    client.put("/api/settings", json={"verbosity": "terse"})

    stored_keys = [k for k in fake_db._store if k[0] == "argus_users"]
    assert len(stored_keys) == 1
