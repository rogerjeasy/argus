"""End-to-end regression for the real Escalation notification path (real
gap found during the Phase 5 spec audit, fixed here): a configured trusted
contact actually receives a real SMS + call through the swappable
TwilioClient interface; an unconfigured one degrades to logging only,
never crashes, never makes a real Twilio call."""
from app.agents.escalation import EscalationAgent, RealNotificationSender
from app.agents.memory import MemoryAgent
from app.models.trusted_contact import TrustedContact
from app.tests.doubles.fake_firestore import FakeFirestoreClient
from app.tests.doubles.fake_twilio_client import FakeTwilioClient


class _FakePublisher:
    def publish(self, topic_path, data):
        class _F:
            def result(self):
                return "id"
        return _F()

    def topic_path(self, project, topic):
        return f"projects/{project}/topics/{topic}"


async def test_escalation_with_configured_contact_sends_real_shaped_sms_and_call() -> None:
    db = FakeFirestoreClient()
    memory = MemoryAgent(db)
    await memory.set_trusted_contact("user-1", TrustedContact(name="Jamie", phone_number="+15559990000"))
    twilio = FakeTwilioClient()
    sender = RealNotificationSender(twilio, memory, from_number="+15551234567")
    agent = EscalationAgent(db, _FakePublisher(), sender)

    await agent.escalate(session_id="s1", uid="user-1", reason="distress signal", signals=["knock", "distress_utterance"])

    assert len(twilio.sms_sent) == 1
    assert len(twilio.placed_calls) == 1
    # Persisted to Firestore regardless - the audit trail from Task 4's
    # design note, unaffected by whether notification succeeded.
    stored = db.collection("argus_users").document("user-1").collection("escalations")
    assert len(stored.stream()) == 1


async def test_escalation_with_no_contact_never_touches_twilio() -> None:
    db = FakeFirestoreClient()
    memory = MemoryAgent(db)
    twilio = FakeTwilioClient()
    sender = RealNotificationSender(twilio, memory, from_number="+15551234567")
    agent = EscalationAgent(db, _FakePublisher(), sender)

    event = await agent.escalate(session_id="s1", uid="user-1", reason="test", signals=["a", "b"])

    assert twilio.sms_sent == []
    assert twilio.placed_calls == []
    assert event.reason == "test"  # the escalation itself still succeeds and is recorded
