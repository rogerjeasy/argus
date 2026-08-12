import asyncio
import uuid
from datetime import datetime, timezone
from typing import Callable

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from google.cloud import firestore

from app.core.auth import AuthenticatedUser, InvalidTokenError, verify_id_token_string
from app.core.clients import get_firestore_client
from app.core.config import Settings, get_settings
from app.core.telemetry import get_tracer
from app.ws.gemini_bridge import GeminiLiveBridge

router = APIRouter()
tracer = get_tracer(__name__)


def get_bridge_factory() -> Callable[[Settings], GeminiLiveBridge]:
    return lambda settings: GeminiLiveBridge(settings)


def _authenticate(websocket: WebSocket) -> AuthenticatedUser:
    token = websocket.query_params.get("token")
    if not token:
        raise InvalidTokenError("Missing token query parameter")
    return verify_id_token_string(token)


@router.websocket("/ws/session")
async def session_endpoint(
    websocket: WebSocket,
    db: firestore.Client = Depends(get_firestore_client),
    settings: Settings = Depends(get_settings),
    bridge_factory: Callable[[Settings], GeminiLiveBridge] = Depends(get_bridge_factory),
) -> None:
    try:
        user = _authenticate(websocket)
    except InvalidTokenError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    session_id = str(uuid.uuid4())

    with tracer.start_as_current_span("ws.session") as span:
        span.set_attribute("argus.uid", user.uid)
        span.set_attribute("argus.session_id", session_id)

        db.collection("sessions").document(session_id).set(
            {
                "session_id": session_id,
                "uid": user.uid,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "ended_at": None,
                "status": "active",
            }
        )

        bridge = bridge_factory(settings)
        await bridge.connect()

        async def relay_from_gemini() -> None:
            async for chunk in bridge.receive_audio():
                await websocket.send_bytes(chunk)

        receiver_task = asyncio.create_task(relay_from_gemini())
        try:
            while True:
                chunk = await websocket.receive_bytes()
                await bridge.send_audio(chunk)
        except WebSocketDisconnect:
            pass
        finally:
            receiver_task.cancel()
            await bridge.close()
            db.collection("sessions").document(session_id).update(
                {"ended_at": datetime.now(timezone.utc).isoformat(), "status": "closed"}
            )
