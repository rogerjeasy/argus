import asyncio
from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient

from app.core.auth import AuthenticatedUser
from app.core.clients import get_firestore_client
from app.main import app
from app.tests.doubles.fake_firestore import FakeFirestoreClient
from app.ws.session import get_bridge_factory


class _StubBridge:
    def __init__(self) -> None:
        self.connected = False
        self.sent: list[bytes] = []
        self.video_sent: list[bytes] = []

    def set_on_input_transcript(self, callback) -> None:
        pass

    def set_on_scene_observation(self, callback) -> None:
        pass

    async def connect(self) -> None:
        self.connected = True

    async def send_audio(self, chunk: bytes) -> None:
        self.sent.append(chunk)

    async def send_video_frame(self, chunk: bytes) -> None:
        self.video_sent.append(chunk)

    async def receive_audio(self) -> AsyncIterator[bytes]:
        yield b"spoken-response"
        # A real Gemini Live stream stays open until the session ends; block
        # here so this task only ends via cancellation (client disconnect),
        # not by the generator completing on its own.
        await asyncio.Event().wait()

    async def close(self) -> None:
        self.connected = False


class _FailingConnectBridge:
    """Bridge whose connect() fails, e.g. Gemini auth/quota/network failure."""

    def __init__(self) -> None:
        self.closed = False

    def set_on_input_transcript(self, callback) -> None:
        pass

    def set_on_scene_observation(self, callback) -> None:
        pass

    async def connect(self) -> None:
        raise RuntimeError("gemini connect failed")

    async def send_audio(self, chunk: bytes) -> None:  # pragma: no cover - unreachable
        raise AssertionError("send_audio should never be called")

    async def send_video_frame(self, chunk: bytes) -> None:  # pragma: no cover - unreachable
        raise AssertionError("send_video_frame should never be called")

    async def receive_audio(self) -> AsyncIterator[bytes]:  # pragma: no cover - unreachable
        raise AssertionError("receive_audio should never be called")
        yield b""  # noqa: unreachable, keeps this an async generator

    async def close(self) -> None:
        self.closed = True


class _DroppingBridge:
    """Bridge that connects fine but fails as soon as Gemini starts streaming."""

    def __init__(self) -> None:
        self.sent: list[bytes] = []
        self.closed = False

    def set_on_input_transcript(self, callback) -> None:
        pass

    def set_on_scene_observation(self, callback) -> None:
        pass

    async def connect(self) -> None:
        pass

    async def send_audio(self, chunk: bytes) -> None:
        self.sent.append(chunk)

    async def send_video_frame(self, chunk: bytes) -> None:
        pass

    async def receive_audio(self) -> AsyncIterator[bytes]:
        raise RuntimeError("gemini dropped mid-session")
        yield b""  # noqa: unreachable, keeps this an async generator

    async def close(self) -> None:
        self.closed = True


def _authenticated_as(uid: str):
    return lambda token: AuthenticatedUser(uid=uid, email=None)


def _mock_build_orchestrator(monkeypatch, orchestrator=None) -> None:
    """build_orchestrator is now async and, unmocked, calls
    get_transit_domains() — a real network fetch (MBTA's feed URL has a
    non-empty default, so this isn't conditional on Settings). Every test
    below that reaches this line, not just the ones that care about
    orchestrator behavior, must mock it out or it would hit the real
    network — a Global Constraints violation and a source of CI flakiness.
    """
    fake = orchestrator if orchestrator is not None else _FakeOrchestrator()

    async def _fake_build_orchestrator(db):
        return fake

    monkeypatch.setattr("app.ws.session.build_orchestrator", _fake_build_orchestrator)


def test_ws_session_rejects_missing_token() -> None:
    client = TestClient(app)
    # The server closes the socket (code 1008) without ever calling accept(),
    # so Starlette's TestClient raises WebSocketDisconnect on __enter__ itself
    # rather than on a later receive call.
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/session"):
            pass


def test_ws_session_relays_audio_when_authenticated(monkeypatch) -> None:
    fake_db = FakeFirestoreClient()
    stub_bridge = _StubBridge()

    app.dependency_overrides[get_firestore_client] = lambda: fake_db
    app.dependency_overrides[get_bridge_factory] = lambda: (lambda settings: stub_bridge)
    monkeypatch.setattr("app.ws.session.verify_id_token_string", _authenticated_as("user-1"))
    _mock_build_orchestrator(monkeypatch)

    client = TestClient(app)
    with client.websocket_connect("/ws/session?token=valid-token") as websocket:
        websocket.send_bytes(bytes([1]) + b"mic-audio")
        response = websocket.receive_bytes()
        assert response == b"spoken-response"

    assert stub_bridge.sent == [b"mic-audio"]
    stored = [v for k, v in fake_db._store.items() if k[0] == "argus_sessions"]
    assert len(stored) == 1
    assert stored[0]["uid"] == "user-1"
    assert stored[0]["status"] == "closed"


def test_ws_session_marks_error_when_gemini_connect_fails(monkeypatch) -> None:
    fake_db = FakeFirestoreClient()
    failing_bridge = _FailingConnectBridge()

    app.dependency_overrides[get_firestore_client] = lambda: fake_db
    app.dependency_overrides[get_bridge_factory] = lambda: (lambda settings: failing_bridge)
    monkeypatch.setattr("app.ws.session.verify_id_token_string", _authenticated_as("user-2"))
    _mock_build_orchestrator(monkeypatch)

    client = TestClient(app)
    with client.websocket_connect("/ws/session?token=valid-token") as websocket:
        with pytest.raises(Exception):
            websocket.receive_bytes()

    stored = [v for k, v in fake_db._store.items() if k[0] == "argus_sessions"]
    assert len(stored) == 1
    assert stored[0]["uid"] == "user-2"
    assert stored[0]["status"] == "error"
    assert stored[0]["ended_at"] is not None


def test_ws_session_closes_when_gemini_drops_mid_session(monkeypatch) -> None:
    fake_db = FakeFirestoreClient()
    dropping_bridge = _DroppingBridge()

    app.dependency_overrides[get_firestore_client] = lambda: fake_db
    app.dependency_overrides[get_bridge_factory] = lambda: (lambda settings: dropping_bridge)
    monkeypatch.setattr("app.ws.session.verify_id_token_string", _authenticated_as("user-3"))
    _mock_build_orchestrator(monkeypatch)

    client = TestClient(app)
    with client.websocket_connect("/ws/session?token=valid-token") as websocket:
        with pytest.raises(Exception):
            websocket.receive_bytes()

    assert dropping_bridge.closed is True
    stored = [v for k, v in fake_db._store.items() if k[0] == "argus_sessions"]
    assert len(stored) == 1
    assert stored[0]["uid"] == "user-3"
    assert stored[0]["status"] == "error"


class _StubBridgeWithTranscript(_StubBridge):
    def __init__(self) -> None:
        super().__init__()
        self.on_input_transcript = None
        self.on_scene_observation = None
        self.spoken: list[str] = []

    def set_on_input_transcript(self, callback) -> None:
        self.on_input_transcript = callback

    def set_on_scene_observation(self, callback) -> None:
        self.on_scene_observation = callback

    async def speak(self, text: str) -> None:
        self.spoken.append(text)


class _FakeOrchestratorResult:
    def __init__(self, text: str, decision: str) -> None:
        from app.models.agent_events import GuardrailDecision, GuidanceOutput
        self.guidance = GuidanceOutput(session_id="s1", text=text, haptic_pattern="pattern-forward", earcon="earcon-plan-updated")
        self.guardrail = GuardrailDecision(step_id="step-1", decision=decision, reason="test")


class _FakeOrchestrator:
    async def handle_goal(self, goal):
        return _FakeOrchestratorResult("Head to platform 4.", "requires_confirmation")


def test_ws_session_sends_a_guidance_frame_after_a_finished_transcript(monkeypatch) -> None:
    import json

    fake_db = FakeFirestoreClient()
    stub_bridge = _StubBridgeWithTranscript()

    app.dependency_overrides[get_firestore_client] = lambda: fake_db
    app.dependency_overrides[get_bridge_factory] = lambda: (lambda settings: stub_bridge)
    monkeypatch.setattr("app.ws.session.verify_id_token_string", _authenticated_as("user-1"))
    _mock_build_orchestrator(monkeypatch, _FakeOrchestrator())

    client = TestClient(app)
    with client.websocket_connect("/ws/session?token=valid-token") as websocket:
        # Drain the audio frame from _StubBridge's receive_audio() first.
        websocket.receive_bytes()
        # `set_on_input_transcript` was called with the real closure during
        # session setup, before the endpoint blocks on the relay tasks below
        # — call it directly to simulate Gemini reporting a finished
        # transcript, exactly as `session.py`'s receive loop would.
        import asyncio

        asyncio.run(stub_bridge.on_input_transcript("get me to platform 4"))
        frame = websocket.receive_text()
        payload = json.loads(frame)

    assert payload["type"] == "guidance"
    assert payload["text"] == "Head to platform 4."
    assert payload["guardrail_decision"] == "requires_confirmation"
    assert stub_bridge.spoken == ["Head to platform 4."]


def test_ws_session_dispatches_prefixed_audio_and_video_frames(monkeypatch) -> None:
    fake_db = FakeFirestoreClient()
    stub_bridge = _StubBridge()

    app.dependency_overrides[get_firestore_client] = lambda: fake_db
    app.dependency_overrides[get_bridge_factory] = lambda: (lambda settings: stub_bridge)
    monkeypatch.setattr("app.ws.session.verify_id_token_string", _authenticated_as("user-1"))
    _mock_build_orchestrator(monkeypatch)

    client = TestClient(app)
    with client.websocket_connect("/ws/session?token=valid-token") as websocket:
        websocket.send_bytes(bytes([1]) + b"mic-audio")
        websocket.send_bytes(bytes([2]) + b"jpeg-frame")
        websocket.receive_bytes()

    assert stub_bridge.sent == [b"mic-audio"]
    assert stub_bridge.video_sent == [b"jpeg-frame"]


def test_ws_session_speaks_framing_guidance_and_dedups_repeated_positions(monkeypatch) -> None:
    import json

    fake_db = FakeFirestoreClient()
    stub_bridge = _StubBridgeWithTranscript()

    app.dependency_overrides[get_firestore_client] = lambda: fake_db
    app.dependency_overrides[get_bridge_factory] = lambda: (lambda settings: stub_bridge)
    monkeypatch.setattr("app.ws.session.verify_id_token_string", _authenticated_as("user-1"))
    _mock_build_orchestrator(monkeypatch, _FakeOrchestrator())

    client = TestClient(app)
    with client.websocket_connect("/ws/session?token=valid-token") as websocket:
        websocket.receive_bytes()  # drain the stub's one audio chunk

        import asyncio

        # First observation: "right" — must speak and send a framing frame.
        asyncio.run(stub_bridge.on_scene_observation(
            {"text_detected": True, "position": "right", "signage_text": "", "confidence": 0.9}
        ))
        frame = json.loads(websocket.receive_text())
        assert frame["type"] == "framing"
        assert frame["text"] == "Move slightly right."

        # Second observation: same position again — must NOT speak/send again.
        asyncio.run(stub_bridge.on_scene_observation(
            {"text_detected": True, "position": "right", "signage_text": "", "confidence": 0.9}
        ))

        # Third observation: position changed to "center" — must speak again.
        asyncio.run(stub_bridge.on_scene_observation(
            {"text_detected": True, "position": "center", "signage_text": "", "confidence": 0.9}
        ))
        frame2 = json.loads(websocket.receive_text())
        assert frame2["text"] == "Hold steady, almost there."

    assert stub_bridge.spoken == ["Move slightly right.", "Hold steady, almost there."]


class _FakeOrchestratorWithConfirmation:
    def __init__(self) -> None:
        self.resolve_calls: list[tuple[str, str, bool]] = []

    async def handle_goal(self, goal):
        return _FakeOrchestratorResult("Head to platform 4.", "requires_confirmation")

    async def resolve_confirmation(self, session_id, uid, accepted):
        self.resolve_calls.append((session_id, uid, accepted))
        return _FakeOrchestratorResult("Refill confirmed, ready tomorrow.", "approved")


def test_client_text_message_resolves_a_pending_confirmation(monkeypatch) -> None:
    import json

    fake_db = FakeFirestoreClient()
    stub_bridge = _StubBridgeWithTranscript()
    fake_orchestrator = _FakeOrchestratorWithConfirmation()

    app.dependency_overrides[get_firestore_client] = lambda: fake_db
    app.dependency_overrides[get_bridge_factory] = lambda: (lambda settings: stub_bridge)
    monkeypatch.setattr("app.ws.session.verify_id_token_string", _authenticated_as("user-1"))
    _mock_build_orchestrator(monkeypatch, fake_orchestrator)

    client = TestClient(app)
    with client.websocket_connect("/ws/session?token=valid-token") as websocket:
        websocket.receive_bytes()  # drain the stub's one audio chunk
        websocket.send_text(json.dumps({"type": "resolve_confirmation", "step_id": "step-1", "accepted": True}))
        frame = json.loads(websocket.receive_text())

    assert len(fake_orchestrator.resolve_calls) == 1
    _, uid, accepted = fake_orchestrator.resolve_calls[0]
    assert uid == "user-1"
    assert accepted is True
    assert frame["type"] == "guidance"
    assert frame["text"] == "Refill confirmed, ready tomorrow."
    assert frame["guardrail_decision"] == "approved"
    assert frame["step_id"] == "step-1"
    assert stub_bridge.spoken == ["Refill confirmed, ready tomorrow."]


def test_malformed_client_text_message_is_dropped_not_raised(monkeypatch) -> None:
    fake_db = FakeFirestoreClient()
    stub_bridge = _StubBridgeWithTranscript()
    fake_orchestrator = _FakeOrchestratorWithConfirmation()

    app.dependency_overrides[get_firestore_client] = lambda: fake_db
    app.dependency_overrides[get_bridge_factory] = lambda: (lambda settings: stub_bridge)
    monkeypatch.setattr("app.ws.session.verify_id_token_string", _authenticated_as("user-1"))
    _mock_build_orchestrator(monkeypatch, fake_orchestrator)

    client = TestClient(app)
    with client.websocket_connect("/ws/session?token=valid-token") as websocket:
        websocket.receive_bytes()  # drain the stub's one audio chunk
        websocket.send_text("not json at all")
        websocket.send_text('{"type": "something_else"}')
        # The session must still be alive and relay audio normally after
        # two malformed/irrelevant text frames.
        websocket.send_bytes(bytes([1]) + b"more-audio")

    assert fake_orchestrator.resolve_calls == []
    assert stub_bridge.sent == [b"more-audio"]


def test_build_orchestrator_registers_personal_admin_alongside_transit(monkeypatch) -> None:
    import asyncio

    import httpx

    from app.core.config import Settings
    from app.domains.transit.registry import reset_transit_domain_registry_for_tests
    from app.tests.fixtures.gtfs_builders import build_static_feed_zip
    from app.ws.session import build_orchestrator

    # Mirrors test_transit_domain_registry.py's own fixture exactly — a
    # single-stop static feed is enough for get_transit_domains() to build
    # without a real network fetch. Same _RealAsyncClient-capture reasoning
    # as that file's own module docstring: patching
    # app.domains.transit.registry.httpx.AsyncClient must not recurse into
    # itself.
    _real_async_client = httpx.AsyncClient
    static_zip = build_static_feed_zip(
        [{"stop_id": "s1", "stop_name": "North Station", "platform_code": "", "parent_station": ""}],
        [{"trip_id": "t1", "stop_id": "s1", "arrival_time": "09:00:00", "stop_sequence": "1"}],
    )

    class _FakeTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=static_zip, request=request)

    reset_transit_domain_registry_for_tests()
    monkeypatch.setattr("app.ws.session.get_settings", lambda: Settings(gtfs_ch_static_feed_url="", gtfs_ch_realtime_feed_url=""))
    monkeypatch.setattr(
        "app.domains.transit.registry.httpx.AsyncClient", lambda **kw: _real_async_client(transport=_FakeTransport())
    )

    db = FakeFirestoreClient()
    orchestrator = asyncio.run(build_orchestrator(db))

    assert "personal_admin" in orchestrator._domains
    personal_admin = orchestrator._domains["personal_admin"]
    assert personal_admin.executors == {}  # no Twilio credentials in this test's Settings
    reset_transit_domain_registry_for_tests()
