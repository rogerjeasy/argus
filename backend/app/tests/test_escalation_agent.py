import json

import pytest

from app.agents.escalation import EscalationAgent, LoggingNotificationSender
from app.tests.doubles.fake_firestore import FakeFirestoreClient


class _FakePublisher:
    def __init__(self) -> None:
        self.published: list[bytes] = []

    def publish(self, topic_path: str, data: bytes):
        self.published.append(data)

        class _Future:
            def result(self_inner):
                return "message-id"

        return _Future()

    def topic_path(self, project: str, topic: str) -> str:
        return f"projects/{project}/topics/{topic}"


class _RecordingSender:
    def __init__(self) -> None:
        self.sent = []

    async def send(self, event) -> None:
        self.sent.append(event)


@pytest.mark.asyncio
async def test_escalate_persists_publishes_and_notifies() -> None:
    db = FakeFirestoreClient()
    publisher = _FakePublisher()
    sender = _RecordingSender()
    agent = EscalationAgent(db, publisher, sender)

    event = await agent.escalate(session_id="s1", uid="u1", reason="bounded replan exhausted", signals=["replan_exhausted"])

    assert event.reason == "bounded replan exhausted"
    stored = db.collection("argus_users").document("u1").collection("escalations").document(event.session_id + "-" + str(int(event.triggered_at.timestamp()))).get()
    assert stored.exists
    assert stored.to_dict()["reason"] == "bounded replan exhausted"
    assert len(publisher.published) == 1
    assert json.loads(publisher.published[0])["reason"] == "bounded replan exhausted"
    assert sender.sent == [event]


@pytest.mark.asyncio
async def test_logging_notification_sender_does_not_raise(caplog) -> None:
    from datetime import datetime, timezone
    from app.models.agent_events import EscalationEvent

    sender = LoggingNotificationSender()
    event = EscalationEvent(session_id="s1", uid="u1", reason="test", signals=[], triggered_at=datetime.now(timezone.utc))

    await sender.send(event)  # must not raise


@pytest.mark.asyncio
async def test_consider_distress_signal_returns_none_for_a_single_signal_type() -> None:
    agent = EscalationAgent(FakeFirestoreClient(), _FakePublisher(), _RecordingSender())

    result = await agent.consider_distress_signal(
        session_id="s1", uid="u1", signal_type="spoken_distress", reason="distress keyword detected"
    )

    assert result is None


@pytest.mark.asyncio
async def test_consider_distress_signal_escalates_once_a_second_distinct_signal_type_arrives() -> None:
    agent = EscalationAgent(FakeFirestoreClient(), _FakePublisher(), _RecordingSender())

    first = await agent.consider_distress_signal(
        session_id="s1", uid="u1", signal_type="spoken_distress", reason="distress keyword detected"
    )
    second = await agent.consider_distress_signal(
        session_id="s1", uid="u1", signal_type="ambient_distress_sound", reason="ambient sound classified as distress"
    )

    assert first is None
    assert second is not None
    assert set(second.signals) == {"spoken_distress", "ambient_distress_sound"}


@pytest.mark.asyncio
async def test_consider_distress_signal_repeating_the_same_type_never_escalates_alone() -> None:
    """Red-team case: the same signal type firing twice must not be
    mistaken for two independent corroborating signals."""
    agent = EscalationAgent(FakeFirestoreClient(), _FakePublisher(), _RecordingSender())

    await agent.consider_distress_signal(session_id="s1", uid="u1", signal_type="spoken_distress", reason="x")
    result = await agent.consider_distress_signal(session_id="s1", uid="u1", signal_type="spoken_distress", reason="x")

    assert result is None


@pytest.mark.asyncio
async def test_consider_distress_signal_is_scoped_per_session() -> None:
    agent = EscalationAgent(FakeFirestoreClient(), _FakePublisher(), _RecordingSender())

    await agent.consider_distress_signal(session_id="s1", uid="u1", signal_type="spoken_distress", reason="x")
    # A different session's ambient signal must not corroborate session s1's.
    result = await agent.consider_distress_signal(session_id="s2", uid="u2", signal_type="ambient_distress_sound", reason="x")

    assert result is None
