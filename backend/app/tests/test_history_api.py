import pytest
from fastapi.testclient import TestClient

from app.agents.memory import MemoryAgent
from app.core.auth import AuthenticatedUser, get_current_user
from app.core.clients import get_firestore_client
from app.main import app
from app.tests.doubles.fake_firestore import FakeFirestoreClient


def _client(db: FakeFirestoreClient) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(uid="user-1", email=None)
    app.dependency_overrides[get_firestore_client] = lambda: db
    return TestClient(app)


def test_history_is_empty_for_a_new_user() -> None:
    response = _client(FakeFirestoreClient()).get("/api/history")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_history_returns_recorded_sessions_newest_first() -> None:
    db = FakeFirestoreClient()
    memory = MemoryAgent(db)
    await memory.record_session_summary(
        uid="user-1", session_id="s1", summary="Checked your platform at North Station.",
        started_at="2026-08-26T09:00:00+00:00", ended_at="2026-08-26T09:05:00+00:00",
    )
    await memory.record_session_summary(
        uid="user-1", session_id="s2", summary="Read a sign for you.",
        started_at="2026-08-27T18:00:00+00:00", ended_at="2026-08-27T18:03:00+00:00",
    )

    rows = _client(db).get("/api/history").json()

    assert [r["session_id"] for r in rows] == ["s2", "s1"]
    assert rows[0]["summary"] == "Read a sign for you."
    assert rows[0]["started_at"] == "2026-08-27T18:00:00+00:00"


@pytest.mark.asyncio
async def test_memory_remember_and_recall_round_trip() -> None:
    memory = MemoryAgent(FakeFirestoreClient())
    await memory.remember("user-1", "home_address", "42 Oak Street")
    assert await memory.recall("user-1", "home_address") == "42 Oak Street"
    assert await memory.recall("user-1", "unknown") is None
