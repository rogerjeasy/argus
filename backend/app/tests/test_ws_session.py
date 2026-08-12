from collections.abc import AsyncIterator

from fastapi.testclient import TestClient

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

    async def close(self) -> None:
        self.connected = False


def test_ws_session_rejects_missing_token() -> None:
    client = TestClient(app)
    # The server closes the socket (code 1008) without ever calling accept(),
    # so Starlette's TestClient raises WebSocketDisconnect on __enter__ itself
    # rather than on a later receive call.
    with __import__("pytest").raises(Exception):
        with client.websocket_connect("/ws/session"):
            pass


def test_ws_session_relays_audio_when_authenticated(monkeypatch) -> None:
    fake_db = FakeFirestoreClient()
    stub_bridge = _StubBridge()

    app.dependency_overrides[get_firestore_client] = lambda: fake_db
    app.dependency_overrides[get_bridge_factory] = lambda: (lambda settings: stub_bridge)
    monkeypatch.setattr(
        "app.ws.session.verify_id_token_string",
        lambda token: __import__("app.core.auth", fromlist=["AuthenticatedUser"]).AuthenticatedUser(
            uid="user-1", email=None
        ),
    )

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
