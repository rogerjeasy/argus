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


def test_get_trusted_contact_returns_null_when_unset() -> None:
    client = _client()
    response = client.get("/api/trusted-contact")
    assert response.status_code == 200
    assert response.json() is None


def test_put_trusted_contact_persists_it() -> None:
    client = _client()
    response = client.put("/api/trusted-contact", json={"name": "Jamie", "phone_number": "+15559990000"})
    assert response.status_code == 200
    assert response.json() == {"name": "Jamie", "phone_number": "+15559990000"}

    follow_up = client.get("/api/trusted-contact")
    assert follow_up.json() == {"name": "Jamie", "phone_number": "+15559990000"}


def test_put_trusted_contact_requires_both_fields_on_first_write() -> None:
    """Unlike UserSettingsUpdate's partial-update semantics, a trusted
    contact has no sensible partial default (no meaningful "default phone
    number") - the PUT body must set both fields."""
    client = _client()
    response = client.put("/api/trusted-contact", json={"name": "Jamie"})
    assert response.status_code == 422
