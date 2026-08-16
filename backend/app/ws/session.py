import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Callable

import anyio
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.cloud import firestore
from starlette.concurrency import run_in_threadpool
from starlette.websockets import WebSocketState

from app.agents.escalation import EscalationAgent, LoggingNotificationSender
from app.agents.grounding import GroundingAgent
from app.agents.guardrail import GuardrailAgent
from app.agents.guidance import GuidanceAgent
from app.agents.llm_runner import LlmAgentRunner
from app.agents.memory import MemoryAgent
from app.agents.orchestrator import TaskOrchestrator
from app.agents.perception import PerceptionAgent
from app.agents.planner import PlannerAgent
from app.agents.replanning import ReplanningAgent
from app.agents.router import DomainRouterAgent
from app.core.auth import AuthenticatedUser, InvalidTokenError, verify_id_token_string
from app.core.clients import get_firestore_client
from app.core.config import Settings, get_settings
from app.core.pubsub import get_publisher_client
from app.core.telemetry import get_tracer
from app.domains.transit.registry import get_transit_domains
from app.models.agent_events import PerceivedGoal
from app.ws.gemini_bridge import GeminiLiveBridge

router = APIRouter()
tracer = get_tracer(__name__)
logger = logging.getLogger(__name__)

#: Client-to-server binary frames now carry two kinds of payload on one
#: socket — this 1-byte prefix says which. Server-to-client stays
#: unprefixed (still audio-only in this phase). The frontend's
#: `frontend/lib/session/useSession.ts` must use these exact values.
FRAME_TYPE_AUDIO = 1
FRAME_TYPE_VIDEO = 2


def get_bridge_factory() -> Callable[[Settings], GeminiLiveBridge]:
    return lambda settings: GeminiLiveBridge(settings)


def _reasoning_model(settings: Settings) -> Gemini:
    """ADK's `Gemini` model wrapper builds its own `google.genai.Client()`
    lazily, and — unlike `GeminiLiveBridge`'s client, which we configure
    explicitly — it does that from ambient `GOOGLE_GENAI_USE_VERTEXAI`/
    `GOOGLE_CLOUD_PROJECT`/`GOOGLE_CLOUD_LOCATION` env vars unless given
    `client_kwargs` directly. Passing them here keeps one source of truth
    (`Settings`) instead of relying on the process environment separately
    agreeing with it."""
    return Gemini(
        model="gemini-2.5-flash",
        client_kwargs={"vertexai": True, "project": settings.gcp_project_id, "location": settings.vertex_ai_location},
    )


async def build_orchestrator(db: firestore.Client) -> TaskOrchestrator:
    settings = get_settings()
    # Phase 2: the real TransitDomain(s) replace Phase 1's StubDomain in
    # live wiring (StubDomain's class and its own tests still exist, just
    # unused here). get_transit_domains() is lazy — see
    # app/domains/transit/registry.py — so this doesn't refetch/reparse the
    # static feed on every WebSocket session.
    domains = await get_transit_domains(settings)
    router_runner = LlmAgentRunner(
        agent=LlmAgent(
            name="domain_router", model=_reasoning_model(settings), instruction="Classify the goal into one domain id."
        )
    )
    planner_runner = LlmAgentRunner(
        agent=LlmAgent(name="planner", model=_reasoning_model(settings), instruction="Produce the next plan step as JSON.")
    )
    guidance_runner = LlmAgentRunner(
        agent=LlmAgent(
            name="guidance",
            model=_reasoning_model(settings),
            instruction="Phrase this plan step as one short spoken instruction.",
        )
    )

    grounding_agents = {d.domain_id: GroundingAgent(d) for d in domains}
    memory = MemoryAgent(db)
    return TaskOrchestrator(
        perception=PerceptionAgent(),
        router=DomainRouterAgent(router_runner, domains=domains),
        grounding_agents=grounding_agents,
        planner=PlannerAgent(planner_runner),
        guardrail=GuardrailAgent(),
        replanning=ReplanningAgent(),
        guidance=GuidanceAgent(guidance_runner),
        memory=memory,
        escalation=EscalationAgent(db, get_publisher_client(), LoggingNotificationSender()),
    )


def _authenticate(websocket: WebSocket) -> AuthenticatedUser:
    """Blocking: `verify_id_token_string` fetches/refreshes Google's JWKs over
    the network via `firebase-admin`. Always call it through
    `run_in_threadpool` so one handshake cannot stall every other concurrent
    session sharing this worker's event loop."""
    token = websocket.query_params.get("token")
    if not token:
        raise InvalidTokenError("Missing token query parameter")
    return verify_id_token_string(token)


async def _close_if_connected(websocket: WebSocket, code: int) -> None:
    if websocket.application_state == WebSocketState.CONNECTED:
        try:
            await websocket.close(code=code)
        except RuntimeError:
            pass


@router.websocket("/ws/session")
async def session_endpoint(
    websocket: WebSocket,
    db: firestore.Client = Depends(get_firestore_client),
    settings: Settings = Depends(get_settings),
    bridge_factory: Callable[[Settings], GeminiLiveBridge] = Depends(get_bridge_factory),
) -> None:
    try:
        user = await run_in_threadpool(_authenticate, websocket)
    except InvalidTokenError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    session_id = str(uuid.uuid4())

    with tracer.start_as_current_span("ws.session") as span:
        span.set_attribute("argus.uid", user.uid)
        span.set_attribute("argus.session_id", session_id)

        # Every Firestore call below is a synchronous gRPC round trip. Run them
        # in a worker thread so an unrelated concurrent session's audio relay
        # keeps flowing while this one talks to Firestore.
        session_doc = db.collection("argus_sessions").document(session_id)
        await run_in_threadpool(
            session_doc.set,
            {
                "session_id": session_id,
                "uid": user.uid,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "ended_at": None,
                "status": "active",
            },
        )

        bridge = bridge_factory(settings)
        orchestrator = await build_orchestrator(db)

        async def _handle_transcript(text: str) -> None:
            goal = PerceivedGoal(session_id=session_id, uid=user.uid, raw_text=text)
            result = await orchestrator.handle_goal(goal)
            await bridge.speak(result.guidance.text)
            if websocket.application_state == WebSocketState.CONNECTED:
                await websocket.send_text(json.dumps({
                    "type": "guidance",
                    "text": result.guidance.text,
                    "haptic_pattern": result.guidance.haptic_pattern,
                    "earcon": result.guidance.earcon,
                    "guardrail_decision": result.guardrail.decision,
                }))

        bridge.set_on_input_transcript(_handle_transcript)

        try:
            await bridge.connect()
        except Exception:
            logger.exception(
                "ws_session_connect_failed",
                extra={"session_id": session_id, "uid": user.uid},
            )
            await run_in_threadpool(
                session_doc.update,
                {"ended_at": datetime.now(timezone.utc).isoformat(), "status": "error"},
            )
            await _close_if_connected(websocket, status.WS_1011_INTERNAL_ERROR)
            return

        logger.info(
            "ws_session_connected",
            extra={"session_id": session_id, "uid": user.uid},
        )

        final_status = "closed"

        async def relay_from_gemini() -> None:
            async for chunk in bridge.receive_audio():
                await websocket.send_bytes(chunk)

        async def relay_from_client() -> None:
            first_frame_logged = False
            while True:
                chunk = await websocket.receive_bytes()
                if not first_frame_logged:
                    logger.info(
                        "ws_session_first_audio_frame",
                        extra={"session_id": session_id},
                    )
                    first_frame_logged = True
                if not chunk:
                    continue
                frame_type, payload = chunk[0], chunk[1:]
                if frame_type == FRAME_TYPE_AUDIO:
                    await bridge.send_audio(payload)
                elif frame_type == FRAME_TYPE_VIDEO:
                    await bridge.send_video_frame(payload)
                else:
                    logger.warning(
                        "ws_session_unknown_frame_type",
                        extra={"session_id": session_id, "frame_type": frame_type},
                    )

        receiver_task = asyncio.create_task(relay_from_gemini())
        sender_task = asyncio.create_task(relay_from_client())

        try:
            done, pending = await asyncio.wait(
                {receiver_task, sender_task}, return_when=asyncio.FIRST_COMPLETED
            )

            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            for task in done:
                exc = task.exception()
                if exc is not None and not isinstance(exc, WebSocketDisconnect):
                    final_status = "error"
                    logger.exception(
                        "ws_session_task_failed",
                        exc_info=exc,
                        extra={"session_id": session_id, "uid": user.uid},
                    )
        finally:
            # Record the terminal state and log first, before any best-effort
            # teardown, so the session is never left stuck at status "active"
            # even if the surrounding task is cancelled (e.g. TestClient/ASGI
            # server tearing down the connection concurrently with our own
            # cleanup).
            #
            # The shield is load-bearing. `run_in_threadpool` delegates to
            # `anyio.to_thread.run_sync`, which opens with
            # `checkpoint_if_cancelled()` — inside an already-cancelled anyio
            # cancel scope (exactly what an ASGI server or TestClient tearing
            # down the connection produces) that raises before the worker
            # thread ever starts, and the session would be left stuck at
            # status "active". Shielding defers that cancellation until the
            # write has actually happened.
            with anyio.CancelScope(shield=True):
                await run_in_threadpool(
                    session_doc.update,
                    {
                        "ended_at": datetime.now(timezone.utc).isoformat(),
                        "status": final_status,
                    },
                )
            logger.info(
                "ws_session_disconnected",
                extra={"session_id": session_id, "uid": user.uid, "status": final_status},
            )
            await bridge.close()
            close_code = (
                status.WS_1011_INTERNAL_ERROR
                if final_status == "error"
                else status.WS_1000_NORMAL_CLOSURE
            )
            await _close_if_connected(websocket, close_code)
