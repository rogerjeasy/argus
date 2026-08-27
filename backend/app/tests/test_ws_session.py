import asyncio
import json
from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient

from app.agents.escalation import LoggingNotificationSender
from app.core.auth import AuthenticatedUser
from app.core.clients import get_firestore_client
from app.main import app
from app.tests.doubles.fake_firestore import FakeFirestoreClient
from app.ws.session import get_bridge_factory, get_frame_prefilter_factory


class _StubBridge:
    def __init__(self) -> None:
        self.connected = False
        self.sent: list[bytes] = []
        self.video_sent: list[bytes] = []
        self.spoken: list[str] = []
        self.on_input_transcript = None
        self.tool_handler = None

    def configure(self, *, system_instruction, tool_declarations, tool_handler) -> None:
        self.tool_handler = tool_handler

    def set_on_input_transcript(self, callback) -> None:
        self.on_input_transcript = callback

    async def connect(self) -> None:
        self.connected = True

    async def send_audio(self, chunk: bytes) -> None:
        self.sent.append(chunk)

    async def send_video_frame(self, chunk: bytes) -> None:
        self.video_sent.append(chunk)

    async def speak(self, text: str) -> None:
        self.spoken.append(text)

    async def receive_audio(self) -> AsyncIterator[bytes]:
        yield b"spoken-response"
        # A real Gemini Live stream stays open until the session ends.
        await asyncio.Event().wait()

    async def close(self) -> None:
        self.connected = False


class _FailingConnectBridge(_StubBridge):
    def __init__(self) -> None:
        super().__init__()
        self.closed = False

    async def connect(self) -> None:
        raise RuntimeError("gemini connect failed")

    async def receive_audio(self) -> AsyncIterator[bytes]:  # pragma: no cover
        raise AssertionError("receive_audio should never be called")
        yield b""

    async def close(self) -> None:
        self.closed = True


class _DroppingBridge(_StubBridge):
    def __init__(self) -> None:
        super().__init__()
        self.closed = False

    async def receive_audio(self) -> AsyncIterator[bytes]:
        raise RuntimeError("gemini dropped mid-session")
        yield b""

    async def close(self) -> None:
        self.closed = True


def _authenticated_as(uid: str):
    return lambda token: AuthenticatedUser(uid=uid, email=None)


class _FakeOrchestrator:
    """Only the methods session.py still calls on the orchestrator: the
    session-open background checks and the deterministic distress check."""

    def __init__(self) -> None:
        self.distress_calls: list[tuple[str, str, str]] = []
        self._distress_result = None

    async def check_spoken_distress(self, session_id, uid, text):
        self.distress_calls.append((session_id, uid, text))
        return self._distress_result

    async def check_for_pending_calibration_proposal(self, session_id, uid):
        return None

    async def check_for_pending_daily_briefing(self, session_id, uid):
        return None

    async def handle_ambient_sound_signal(self, session_id, uid, category):
        return None


def _result(text: str, decision: str = "approved"):
    from app.models.agent_events import GuardrailDecision, GuidanceOutput
    r = type("R", (), {})()
    r.guidance = GuidanceOutput(session_id="s1", text=text, haptic_pattern=None, earcon=None)
    r.guardrail = GuardrailDecision(step_id="s", decision=decision, reason="t")
    return r


def _mock_session_deps(monkeypatch, orchestrator=None) -> _FakeOrchestrator:
    """build_orchestrator and get_transit_domains both do real network work
    unmocked (MBTA's feed URL is a non-empty default). Every session test
    stubs both."""
    fake = orchestrator if orchestrator is not None else _FakeOrchestrator()

    async def _fake_build_orchestrator(db):
        return fake

    async def _fake_get_transit_domains(settings):
        return []

    monkeypatch.setattr("app.ws.session.build_orchestrator", _fake_build_orchestrator)
    monkeypatch.setattr("app.ws.session.get_transit_domains", _fake_get_transit_domains)
    return fake


def test_ws_session_rejects_missing_token() -> None:
    client = TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/session"):
            pass


def test_ws_session_relays_audio_when_authenticated(monkeypatch) -> None:
    fake_db = FakeFirestoreClient()
    stub_bridge = _StubBridge()

    app.dependency_overrides[get_firestore_client] = lambda: fake_db
    app.dependency_overrides[get_bridge_factory] = lambda: (lambda settings: stub_bridge)
    monkeypatch.setattr("app.ws.session.verify_id_token_string", _authenticated_as("user-1"))
    _mock_session_deps(monkeypatch)

    client = TestClient(app)
    with client.websocket_connect("/ws/session?token=valid-token") as websocket:
        websocket.send_bytes(bytes([1]) + b"mic-audio")
        assert websocket.receive_bytes() == b"spoken-response"

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
    _mock_session_deps(monkeypatch)

    client = TestClient(app)
    with client.websocket_connect("/ws/session?token=valid-token") as websocket:
        with pytest.raises(Exception):
            websocket.receive_bytes()

    stored = [v for k, v in fake_db._store.items() if k[0] == "argus_sessions"]
    assert stored[0]["status"] == "error"
    assert stored[0]["ended_at"] is not None


def test_ws_session_closes_when_gemini_drops_mid_session(monkeypatch) -> None:
    fake_db = FakeFirestoreClient()
    dropping_bridge = _DroppingBridge()

    app.dependency_overrides[get_firestore_client] = lambda: fake_db
    app.dependency_overrides[get_bridge_factory] = lambda: (lambda settings: dropping_bridge)
    monkeypatch.setattr("app.ws.session.verify_id_token_string", _authenticated_as("user-3"))
    _mock_session_deps(monkeypatch)

    client = TestClient(app)
    with client.websocket_connect("/ws/session?token=valid-token") as websocket:
        with pytest.raises(Exception):
            websocket.receive_bytes()

    assert dropping_bridge.closed is True
    stored = [v for k, v in fake_db._store.items() if k[0] == "argus_sessions"]
    assert stored[0]["status"] == "error"


def test_ws_session_dispatches_prefixed_audio_and_video_frames(monkeypatch) -> None:
    fake_db = FakeFirestoreClient()
    stub_bridge = _StubBridge()

    app.dependency_overrides[get_firestore_client] = lambda: fake_db
    app.dependency_overrides[get_bridge_factory] = lambda: (lambda settings: stub_bridge)
    monkeypatch.setattr("app.ws.session.verify_id_token_string", _authenticated_as("user-1"))
    _mock_session_deps(monkeypatch)

    client = TestClient(app)
    with client.websocket_connect("/ws/session?token=valid-token") as websocket:
        websocket.send_bytes(bytes([1]) + b"mic-audio")
        websocket.send_bytes(bytes([2]) + b"jpeg-frame")
        websocket.receive_bytes()

    assert stub_bridge.sent == [b"mic-audio"]
    assert stub_bridge.video_sent == [b"jpeg-frame"]


@pytest.mark.parametrize(
    "passes,expected",
    [(True, [b"jpeg-frame"]), (False, [])],
    ids=["prefilter-passes", "prefilter-rejects"],
)
def test_video_frame_respects_the_prefilter(monkeypatch, passes, expected) -> None:
    fake_db = FakeFirestoreClient()
    stub_bridge = _StubBridge()

    class _Filter:
        async def has_readable_text(self, frame: bytes) -> bool:
            return passes

    app.dependency_overrides[get_firestore_client] = lambda: fake_db
    app.dependency_overrides[get_bridge_factory] = lambda: (lambda settings: stub_bridge)
    app.dependency_overrides[get_frame_prefilter_factory] = lambda: (lambda settings: _Filter())
    monkeypatch.setattr("app.ws.session.verify_id_token_string", _authenticated_as("user-1"))
    _mock_session_deps(monkeypatch)

    client = TestClient(app)
    with client.websocket_connect("/ws/session?token=valid-token") as websocket:
        websocket.send_bytes(bytes([2]) + b"jpeg-frame")
        websocket.receive_bytes()

    assert stub_bridge.video_sent == expected


def test_transcript_runs_the_distress_check_and_speaks_an_escalation(monkeypatch) -> None:
    fake_db = FakeFirestoreClient()
    stub_bridge = _StubBridge()
    orchestrator = _FakeOrchestrator()
    orchestrator._distress_result = _result("I'm getting you help now.", "denied")

    app.dependency_overrides[get_firestore_client] = lambda: fake_db
    app.dependency_overrides[get_bridge_factory] = lambda: (lambda settings: stub_bridge)
    monkeypatch.setattr("app.ws.session.verify_id_token_string", _authenticated_as("user-1"))
    _mock_session_deps(monkeypatch, orchestrator)

    client = TestClient(app)
    with client.websocket_connect("/ws/session?token=valid-token") as websocket:
        websocket.receive_bytes()
        asyncio.run(stub_bridge.on_input_transcript("please help me"))
        frame = json.loads(websocket.receive_text())

    assert orchestrator.distress_calls[0][2] == "please help me"
    assert frame["type"] == "guidance"
    assert stub_bridge.spoken == ["I'm getting you help now."]


def test_transcript_without_distress_speaks_nothing(monkeypatch) -> None:
    fake_db = FakeFirestoreClient()
    stub_bridge = _StubBridge()
    orchestrator = _FakeOrchestrator()  # _distress_result stays None

    app.dependency_overrides[get_firestore_client] = lambda: fake_db
    app.dependency_overrides[get_bridge_factory] = lambda: (lambda settings: stub_bridge)
    monkeypatch.setattr("app.ws.session.verify_id_token_string", _authenticated_as("user-1"))
    _mock_session_deps(monkeypatch, orchestrator)

    client = TestClient(app)
    with client.websocket_connect("/ws/session?token=valid-token") as websocket:
        websocket.receive_bytes()
        asyncio.run(stub_bridge.on_input_transcript("which platform is my train on"))
        websocket.send_bytes(bytes([1]) + b"more-audio")

    assert orchestrator.distress_calls
    assert stub_bridge.spoken == []
    assert stub_bridge.sent == [b"more-audio"]


def test_tool_calls_from_gemini_are_dispatched_to_the_toolbox(monkeypatch) -> None:
    fake_db = FakeFirestoreClient()
    stub_bridge = _StubBridge()

    app.dependency_overrides[get_firestore_client] = lambda: fake_db
    app.dependency_overrides[get_bridge_factory] = lambda: (lambda settings: stub_bridge)
    monkeypatch.setattr("app.ws.session.verify_id_token_string", _authenticated_as("user-1"))
    _mock_session_deps(monkeypatch)

    client = TestClient(app)
    with client.websocket_connect("/ws/session?token=valid-token") as websocket:
        websocket.receive_bytes()
        # session.py wired the toolbox dispatcher as the bridge's tool_handler.
        result = asyncio.run(stub_bridge.tool_handler("recall", {"key": "nothing"}))

    assert "error" in result  # nothing stored, but dispatched without raising


def test_malformed_client_text_message_is_ignored(monkeypatch) -> None:
    fake_db = FakeFirestoreClient()
    stub_bridge = _StubBridge()

    app.dependency_overrides[get_firestore_client] = lambda: fake_db
    app.dependency_overrides[get_bridge_factory] = lambda: (lambda settings: stub_bridge)
    monkeypatch.setattr("app.ws.session.verify_id_token_string", _authenticated_as("user-1"))
    _mock_session_deps(monkeypatch)

    client = TestClient(app)
    with client.websocket_connect("/ws/session?token=valid-token") as websocket:
        websocket.receive_bytes()
        websocket.send_text("not json")
        websocket.send_text('{"type": "resolve_confirmation"}')
        websocket.send_bytes(bytes([1]) + b"more-audio")

    assert stub_bridge.sent == [b"more-audio"]


class _FakeOrchestratorWithBackgroundMessage(_FakeOrchestrator):
    def __init__(self, *, calibration=None, briefing=None) -> None:
        super().__init__()
        self._calibration = calibration
        self._briefing = briefing
        self.checked: list[str] = []

    async def check_for_pending_calibration_proposal(self, session_id, uid):
        self.checked.append("calibration")
        return self._calibration

    async def check_for_pending_daily_briefing(self, session_id, uid):
        self.checked.append("briefing")
        return self._briefing


@pytest.mark.parametrize("kind", ["calibration", "briefing"])
def test_session_connect_speaks_a_pending_background_message_first(monkeypatch, kind) -> None:
    fake_db = FakeFirestoreClient()
    stub_bridge = _StubBridge()
    msg = _result("I noticed a pattern — want me to stop asking?")
    orchestrator = _FakeOrchestratorWithBackgroundMessage(
        calibration=msg if kind == "calibration" else None,
        briefing=msg if kind == "briefing" else None,
    )

    app.dependency_overrides[get_firestore_client] = lambda: fake_db
    app.dependency_overrides[get_bridge_factory] = lambda: (lambda settings: stub_bridge)
    monkeypatch.setattr("app.ws.session.verify_id_token_string", _authenticated_as("user-1"))
    _mock_session_deps(monkeypatch, orchestrator)

    client = TestClient(app)
    with client.websocket_connect("/ws/session?token=valid-token") as websocket:
        frame = json.loads(websocket.receive_text())

    assert frame["type"] == "guidance"
    assert stub_bridge.spoken == ["I noticed a pattern — want me to stop asking?"]


class _FakeAudioPerceptionOrchestrator(_FakeOrchestrator):
    def __init__(self) -> None:
        super().__init__()
        self.ambient_calls: list[tuple[str, str, str]] = []

    async def handle_ambient_sound_signal(self, session_id, uid, category):
        self.ambient_calls.append((session_id, uid, category))
        return None


def test_audio_perception_runs_when_enabled_and_throttled(monkeypatch) -> None:
    fake_db = FakeFirestoreClient()
    fake_db.collection("argus_users").document("user-1").collection("settings").document("preferences").set(
        {"verbosity": "normal", "pace": "normal", "audio_perception_enabled": True}
    )
    stub_bridge = _StubBridge()
    orchestrator = _FakeAudioPerceptionOrchestrator()

    class _AlwaysAlarm:
        async def classify(self, audio_chunk: bytes) -> str:
            return "alarm"

    app.dependency_overrides[get_firestore_client] = lambda: fake_db
    app.dependency_overrides[get_bridge_factory] = lambda: (lambda settings: stub_bridge)
    from app.ws.session import get_audio_classifier_factory
    app.dependency_overrides[get_audio_classifier_factory] = lambda: (lambda settings: _AlwaysAlarm())
    monkeypatch.setattr("app.ws.session.verify_id_token_string", _authenticated_as("user-1"))
    _mock_session_deps(monkeypatch, orchestrator)

    client = TestClient(app)
    with client.websocket_connect("/ws/session?token=valid-token") as websocket:
        for _ in range(51):
            websocket.send_bytes(bytes([1]) + b"x")
        websocket.receive_bytes()

    assert len(orchestrator.ambient_calls) == 1
    assert orchestrator.ambient_calls[0][2] == "alarm"


def test_audio_perception_never_runs_when_disabled(monkeypatch) -> None:
    fake_db = FakeFirestoreClient()
    stub_bridge = _StubBridge()
    orchestrator = _FakeAudioPerceptionOrchestrator()

    class _FailIfCalled:
        async def classify(self, audio_chunk: bytes) -> str:
            raise AssertionError("must never be invoked when disabled")

    app.dependency_overrides[get_firestore_client] = lambda: fake_db
    app.dependency_overrides[get_bridge_factory] = lambda: (lambda settings: stub_bridge)
    from app.ws.session import get_audio_classifier_factory
    app.dependency_overrides[get_audio_classifier_factory] = lambda: (lambda settings: _FailIfCalled())
    monkeypatch.setattr("app.ws.session.verify_id_token_string", _authenticated_as("user-1"))
    _mock_session_deps(monkeypatch, orchestrator)

    client = TestClient(app)
    with client.websocket_connect("/ws/session?token=valid-token") as websocket:
        for _ in range(100):
            websocket.send_bytes(bytes([1]) + b"x")
        websocket.receive_bytes()

    assert orchestrator.ambient_calls == []


def test_build_orchestrator_registers_personal_admin_alongside_transit(monkeypatch) -> None:
    import httpx

    from app.core.config import Settings
    from app.domains.transit.registry import reset_transit_domain_registry_for_tests
    from app.tests.fixtures.gtfs_builders import build_static_feed_zip
    from app.ws.session import build_orchestrator

    _real_async_client = httpx.AsyncClient
    static_zip = build_static_feed_zip(
        [{"stop_id": "s1", "stop_name": "North Station", "platform_code": "", "parent_station": ""}],
        [{"trip_id": "t1", "stop_id": "s1", "arrival_time": "09:00:00", "stop_sequence": "1"}],
    )

    class _FakeTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=static_zip, request=request)

    reset_transit_domain_registry_for_tests()
    monkeypatch.setattr(
        "app.ws.session.get_settings",
        lambda: Settings(gtfs_ch_static_feed_url="", gtfs_ch_realtime_feed_url=""),
    )
    monkeypatch.setattr(
        "app.domains.transit.registry.httpx.AsyncClient", lambda **kw: _real_async_client(transport=_FakeTransport())
    )

    orchestrator = asyncio.run(build_orchestrator(FakeFirestoreClient()))

    assert "personal_admin" in orchestrator._domains
    assert orchestrator._domains["personal_admin"].executors == {}
    assert isinstance(orchestrator._escalation._sender, LoggingNotificationSender)
    reset_transit_domain_registry_for_tests()


def test_build_orchestrator_uses_real_notification_sender_when_twilio_configured(monkeypatch) -> None:
    import httpx

    from app.agents.escalation import RealNotificationSender
    from app.core.config import Settings
    from app.domains.transit.registry import reset_transit_domain_registry_for_tests
    from app.tests.fixtures.gtfs_builders import build_static_feed_zip
    from app.ws.session import build_orchestrator

    _real_async_client = httpx.AsyncClient
    static_zip = build_static_feed_zip(
        [{"stop_id": "s1", "stop_name": "North Station", "platform_code": "", "parent_station": ""}],
        [{"trip_id": "t1", "stop_id": "s1", "arrival_time": "09:00:00", "stop_sequence": "1"}],
    )

    class _FakeTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=static_zip, request=request)

    reset_transit_domain_registry_for_tests()
    monkeypatch.setattr(
        "app.ws.session.get_settings",
        lambda: Settings(
            gtfs_ch_static_feed_url="", gtfs_ch_realtime_feed_url="",
            twilio_account_sid="AC_fake", twilio_auth_token="fake_token", twilio_from_number="+15551234567",
        ),
    )
    monkeypatch.setattr(
        "app.domains.transit.registry.httpx.AsyncClient", lambda **kw: _real_async_client(transport=_FakeTransport())
    )

    orchestrator = asyncio.run(build_orchestrator(FakeFirestoreClient()))

    assert isinstance(orchestrator._escalation._sender, RealNotificationSender)
    reset_transit_domain_registry_for_tests()
