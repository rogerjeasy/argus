import asyncio
import base64
import json
import logging
from collections.abc import Callable
from functools import lru_cache
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, status
from starlette.websockets import WebSocketState

from app.core.config import Settings, get_settings
from app.domains.personal_admin.audio_codec import mulaw8k_to_pcm16k
from app.domains.personal_admin.call_bridge import CallReasoningBridge
from app.domains.personal_admin.call_session_registry import CallSessionRegistry
from app.domains.personal_admin.models import CallGoal, CallOutcome

logger = logging.getLogger(__name__)
router = APIRouter()


@lru_cache
def get_call_session_registry() -> CallSessionRegistry:
    return CallSessionRegistry()


def get_call_bridge_factory() -> Callable[[Settings, CallGoal], Any]:
    return lambda settings, call_goal: CallReasoningBridge(settings, call_goal)


async def _close_if_connected(websocket: WebSocket, code: int) -> None:
    if websocket.application_state == WebSocketState.CONNECTED:
        try:
            await websocket.close(code=code)
        except RuntimeError:
            pass


@router.websocket("/ws/twilio-media/{step_id}")
async def twilio_media_endpoint(
    websocket: WebSocket,
    step_id: str,
    settings: Settings = Depends(get_settings),
    registry: CallSessionRegistry = Depends(get_call_session_registry),
    bridge_factory: Callable[[Settings, CallGoal], Any] = Depends(get_call_bridge_factory),
) -> None:
    call_goal = registry.get_call_goal(step_id)
    if call_goal is None:
        # Reject at the handshake, same as ws/session.py's auth check —
        # close() before accept() so the client sees the rejection as a
        # failed connection attempt, not a socket that silently opens and
        # closes with nothing ever sent or received.
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    bridge = bridge_factory(settings, call_goal)
    await bridge.connect()

    async def _on_dtmf(digit: str) -> None:
        twilio = registry.get_twilio_client(step_id)
        call_sid = registry.get_call_sid(step_id)
        if twilio is not None and call_sid is not None:
            await twilio.send_dtmf(call_sid=call_sid, digits=digit)

    outcome_holder: dict[str, CallOutcome] = {}

    async def _on_outcome(outcome: CallOutcome) -> None:
        outcome_holder["outcome"] = outcome

    bridge.set_on_dtmf(_on_dtmf)
    bridge.set_on_outcome(_on_outcome)

    async def _relay_twilio_media() -> None:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                return
            text = message.get("text")
            if text is None:
                continue
            event = json.loads(text)
            kind = event.get("event")
            if kind == "start":
                registry.set_call_sid(step_id, event["start"]["callSid"])
            elif kind == "media":
                mulaw = base64.b64decode(event["media"]["payload"])
                await bridge.send_audio(mulaw8k_to_pcm16k(mulaw))
            elif kind == "stop":
                return

    run_task = asyncio.create_task(bridge.run())
    media_task = asyncio.create_task(_relay_twilio_media())

    try:
        _done, pending = await asyncio.wait({run_task, media_task}, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    finally:
        await bridge.close()
        final_outcome = outcome_holder.get("outcome") or CallOutcome(
            status="connected_unresolved", structured_data={}, transcript_summary="Call ended before a resolution.", confidence=0.0
        )
        registry.resolve_outcome(step_id, final_outcome)
        await _close_if_connected(websocket, status.WS_1000_NORMAL_CLOSURE)
