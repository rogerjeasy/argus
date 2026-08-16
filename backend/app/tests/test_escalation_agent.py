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
