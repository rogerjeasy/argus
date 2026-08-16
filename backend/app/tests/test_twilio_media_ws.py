import asyncio
import base64
import json

import pytest
from fastapi.testclient import TestClient

from app.domains.personal_admin.call_session_registry import CallSessionRegistry
from app.domains.personal_admin.models import CallGoal, CallOutcome
from app.main import app
from app.tests.doubles.fake_twilio_client import FakeTwilioClient
from app.ws.twilio_media import get_call_bridge_factory, get_call_session_registry


class _FakeCallReasoningBridge:
    """Stands in for CallReasoningBridge — run() reports a scripted outcome
    via whatever on_outcome callback was registered, without needing a
    real Gemini Live session. It waits for at least one send_audio() call
    first: the real bridge's run() only ever produces a tool call after
    Gemini has actually seen call audio (its receive() genuinely blocks on
    network I/O), so firing the outcome unconditionally here would let
    run_task win the endpoint's asyncio.wait(FIRST_COMPLETED) race before
    the media-relay task gets a chance to forward a single frame — a
    scheduling artifact this fake must not introduce."""

    def __init__(self, outcome: CallOutcome) -> None:
        self._outcome = outcome
        self._on_outcome = None
        self.audio_received: list[bytes] = []
        self.connected = False
        self._audio_seen = asyncio.Event()

    def set_on_dtmf(self, callback) -> None:
        pass

    def set_on_outcome(self, callback) -> None:
        self._on_outcome = callback

    async def connect(self) -> None:
        self.connected = True

    async def send_audio(self, chunk: bytes) -> None:
        self.audio_received.append(chunk)
        self._audio_seen.set()

    async def run(self) -> None:
        await self._audio_seen.wait()
        if self._on_outcome is not None:
            await self._on_outcome(self._outcome)

    async def close(self) -> None:
        pass


def test_twilio_media_endpoint_relays_audio_and_resolves_the_registry() -> None:
    import audioop

    registry = CallSessionRegistry()
    goal = CallGoal(target_phone_number="+15559990000", purpose="confirm refill status", structured_question="Is it ready?")
    registry.register("step-1", goal, FakeTwilioClient())
    outcome = CallOutcome(status="connected_resolved", structured_data={}, transcript_summary="Refill confirmed.", confidence=0.9)
    fake_bridge = _FakeCallReasoningBridge(outcome)

    app.dependency_overrides[get_call_session_registry] = lambda: registry
    app.dependency_overrides[get_call_bridge_factory] = lambda: (lambda settings, call_goal: fake_bridge)

    mulaw_payload = base64.b64encode(audioop.lin2ulaw(b"\x10\x00" * 80, 2)).decode("ascii")

    client = TestClient(app)
    with client.websocket_connect("/ws/twilio-media/step-1") as websocket:
        websocket.send_text(json.dumps({"event": "start", "start": {"callSid": "CA123"}}))
        websocket.send_text(json.dumps({"event": "media", "media": {"payload": mulaw_payload}}))
        websocket.send_text(json.dumps({"event": "stop"}))

    assert fake_bridge.connected is True
    assert len(fake_bridge.audio_received) == 1
    assert registry.get_call_sid("step-1") == "CA123"


def test_twilio_media_endpoint_closes_immediately_for_an_unregistered_step_id() -> None:
    registry = CallSessionRegistry()  # nothing registered

    app.dependency_overrides[get_call_session_registry] = lambda: registry
    app.dependency_overrides[get_call_bridge_factory] = lambda: (lambda settings, call_goal: None)

    client = TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/twilio-media/never-registered"):
            pass
