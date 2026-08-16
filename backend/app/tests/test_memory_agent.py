import pytest

from app.agents.memory import MemoryAgent, StandingPermission
from app.tests.doubles.fake_firestore import FakeFirestoreClient


@pytest.mark.asyncio
async def test_get_standing_permissions_defaults_to_empty() -> None:
    agent = MemoryAgent(FakeFirestoreClient())
    permissions = await agent.get_standing_permissions("u1")
    assert permissions == []


@pytest.mark.asyncio
async def test_get_standing_permissions_reads_seeded_rules() -> None:
    db = FakeFirestoreClient()
    db.collection("argus_users").document("u1").collection("permissions").document("standing").set(
        {"rules": [{"category": "stub-guidance", "threshold": 0.8}]}
    )
    agent = MemoryAgent(db)

    permissions = await agent.get_standing_permissions("u1")

    assert permissions == [StandingPermission(category="stub-guidance", threshold=0.8)]


@pytest.mark.asyncio
async def test_record_task_history_persists_a_summary() -> None:
    db = FakeFirestoreClient()
    agent = MemoryAgent(db)

    await agent.record_task_history(uid="u1", session_id="s1", summary="Guided to platform 4")

    stored = db.collection("argus_users").document("u1").collection("task_history").document("s1").get()
    assert stored.to_dict()["summary"] == "Guided to platform 4"


def test_standing_permission_provider_defaults_to_none() -> None:
    from app.agents.memory import StandingPermission

    permission = StandingPermission(category="pharmacy_refill_under_20", threshold=0.5)

    assert permission.provider is None
