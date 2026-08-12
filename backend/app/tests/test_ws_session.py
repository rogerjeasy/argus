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

    async def connect(self) -> None:
        self.connected = True

    async def send_audio(self, chunk: bytes) -> None:
        self.sent.append(chunk)

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

    async def connect(self) -> None:
        raise RuntimeError("gemini connect failed")

    async def send_audio(self, chunk: bytes) -> None:  # pragma: no cover - unreachable
        raise AssertionError("send_audio should never be called")

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

    async def connect(self) -> None:
        pass

    async def send_audio(self, chunk: bytes) -> None:
        self.sent.append(chunk)

    async def receive_audio(self) -> AsyncIterator[bytes]:
        raise RuntimeError("gemini dropped mid-session")
        yield b""  # noqa: unreachable, keeps this an async generator

    async def close(self) -> None:
        self.closed = True


def _authenticated_as(uid: str):
    return lambda token: AuthenticatedUser(uid=uid, email=None)


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

    client = TestClient(app)
    with client.websocket_connect("/ws/session?token=valid-token") as websocket:
        websocket.send_bytes(b"mic-audio")
        response = websocket.receive_bytes()
        assert response == b"spoken-response"

    assert stub_bridge.sent == [b"mic-audio"]
    stored = [v for k, v in fake_db._store.items() if k[0] == "sessions"]
    assert len(stored) == 1
    assert stored[0]["uid"] == "user-1"
    assert stored[0]["status"] == "closed"


def test_ws_session_marks_error_when_gemini_connect_fails(monkeypatch) -> None:
    fake_db = FakeFirestoreClient()
    failing_bridge = _FailingConnectBridge()

    app.dependency_overrides[get_firestore_client] = lambda: fake_db
    app.dependency_overrides[get_bridge_factory] = lambda: (lambda settings: failing_bridge)
    monkeypatch.setattr("app.ws.session.verify_id_token_string", _authenticated_as("user-2"))

    client = TestClient(app)
    with client.websocket_connect("/ws/session?token=valid-token") as websocket:
        with pytest.raises(Exception):
            websocket.receive_bytes()

    stored = [v for k, v in fake_db._store.items() if k[0] == "sessions"]
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

    client = TestClient(app)
    with client.websocket_connect("/ws/session?token=valid-token") as websocket:
        with pytest.raises(Exception):
            websocket.receive_bytes()

    assert dropping_bridge.closed is True
    stored = [v for k, v in fake_db._store.items() if k[0] == "sessions"]
    assert len(stored) == 1
    assert stored[0]["uid"] == "user-3"
    assert stored[0]["status"] == "error"
