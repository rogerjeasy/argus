from fastapi.testclient import TestClient

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.clients import get_firestore_client
from app.main import app
from app.tests.doubles.fake_firestore import FakeFirestoreClient


def _client(fake_db: FakeFirestoreClient, uid: str = "user-1", provider: str | None = "password"):
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        uid=uid, email="a@example.com", provider=provider
    )
    app.dependency_overrides[get_firestore_client] = lambda: fake_db
    return TestClient(app)


def test_put_users_me_creates_profile_on_first_call() -> None:
    fake_db = FakeFirestoreClient()
    client = _client(fake_db)

    response = client.put("/api/users/me", json={"display_name": "Ada Lovelace"})

    assert response.status_code == 200
    body = response.json()
    assert body["uid"] == "user-1"
    assert body["email"] == "a@example.com"
    assert body["display_name"] == "Ada Lovelace"
    assert body["provider"] == "password"
    assert body["created_at"] == body["last_login_at"]


def test_put_users_me_preserves_created_at_across_calls() -> None:
    fake_db = FakeFirestoreClient()
    client = _client(fake_db)

    first_created_at = client.put("/api/users/me", json={"display_name": "Ada Lovelace"}).json()["created_at"]
    second_created_at = client.put("/api/users/me", json={"display_name": "Ada Lovelace"}).json()["created_at"]

    assert second_created_at == first_created_at


def test_put_users_me_preserves_display_name_when_omitted() -> None:
    fake_db = FakeFirestoreClient()
    client = _client(fake_db)

    client.put("/api/users/me", json={"display_name": "Ada Lovelace"})
    response = client.put("/api/users/me", json={})

    assert response.json()["display_name"] == "Ada Lovelace"


def test_put_users_me_writes_to_argus_users_collection() -> None:
    fake_db = FakeFirestoreClient()
    client = _client(fake_db)

    client.put("/api/users/me", json={})

    stored_keys = [k for k in fake_db._store if k[0] == "argus_users"]
    assert stored_keys == [("argus_users", "user-1")]


def test_put_users_me_preserves_unmodeled_fields_via_merge() -> None:
    fake_db = FakeFirestoreClient()
    fake_db._store[("argus_users", "user-1")] = {"some_future_field": "value"}
    client = _client(fake_db)

    response = client.put("/api/users/me", json={"display_name": "Ada Lovelace"})

    assert response.status_code == 200
    stored = fake_db._store[("argus_users", "user-1")]
    assert stored["some_future_field"] == "value"
    assert stored["display_name"] == "Ada Lovelace"


def test_put_users_me_rejects_unauthenticated_request() -> None:
    fake_db = FakeFirestoreClient()
    app.dependency_overrides[get_firestore_client] = lambda: fake_db
    client = TestClient(app)

    response = client.put("/api/users/me", json={})

    assert response.status_code == 401
