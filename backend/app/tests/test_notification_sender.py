from datetime import datetime, timezone

import pytest

from app.agents.escalation import RealNotificationSender
from app.agents.memory import MemoryAgent
from app.models.agent_events import EscalationEvent
from app.models.trusted_contact import TrustedContact
from app.tests.doubles.fake_firestore import FakeFirestoreClient
from app.tests.doubles.fake_twilio_client import FakeTwilioClient


def _event(**overrides) -> EscalationEvent:
    defaults = dict(
        session_id="s1", uid="user-1", reason="distress signal", signals=["knock", "distress_utterance"],
        triggered_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return EscalationEvent(**defaults)


@pytest.mark.asyncio
async def test_sends_sms_and_places_call_when_contact_configured() -> None:
    db = FakeFirestoreClient()
    memory = MemoryAgent(db)
    await memory.set_trusted_contact("user-1", TrustedContact(name="Jamie", phone_number="+15559990000"))
    twilio = FakeTwilioClient()
    sender = RealNotificationSender(twilio, memory, from_number="+15551234567")

    await sender.send(_event())

    assert len(twilio.sms_sent) == 1
    assert twilio.sms_sent[0]["to"] == "+15559990000"
    assert twilio.sms_sent[0]["from_"] == "+15551234567"
    assert "distress signal" in twilio.sms_sent[0]["body"]

    assert len(twilio.placed_calls) == 1
    assert twilio.placed_calls[0]["to"] == "+15559990000"
    assert "distress signal" in twilio.placed_calls[0]["twiml"]


@pytest.mark.asyncio
async def test_no_real_twilio_call_when_no_contact_configured() -> None:
    db = FakeFirestoreClient()
    memory = MemoryAgent(db)
    twilio = FakeTwilioClient()
    sender = RealNotificationSender(twilio, memory, from_number="+15551234567")

    await sender.send(_event())  # must not raise

    assert twilio.sms_sent == []
    assert twilio.placed_calls == []


@pytest.mark.asyncio
async def test_message_text_is_xml_escaped_in_the_call_twiml() -> None:
    """A reason string containing XML-special characters must not corrupt
    the TwiML - this codebase's reason strings are short fixed category
    labels today, not user-typed text, but this stays a correctness
    property regardless of what future callers pass."""
    db = FakeFirestoreClient()
    memory = MemoryAgent(db)
    await memory.set_trusted_contact("user-1", TrustedContact(name="Jamie", phone_number="+15559990000"))
    twilio = FakeTwilioClient()
    sender = RealNotificationSender(twilio, memory, from_number="+15551234567")

    await sender.send(_event(reason="a <script> & \"quote\""))

    assert "<script>" not in twilio.placed_calls[0]["twiml"]
    assert "&lt;script&gt;" in twilio.placed_calls[0]["twiml"]
