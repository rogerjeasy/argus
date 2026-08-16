import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from google import genai
from google.genai import types as genai_types

from app.core.config import Settings
from app.domains.personal_admin.models import CallGoal, CallOutcome
from app.ws.gemini_bridge import INPUT_MIME_TYPE

logger = logging.getLogger(__name__)

#: Bounded per the same "never loop forever" discipline as
#: ReplanningAgent.MAX_REPLAN_ATTEMPTS — exhausting it reports an
#: unresolved outcome instead of holding the call open indefinitely.
MAX_CALL_TURNS = 12

_PRESS_DTMF_FUNCTION = genai_types.FunctionDeclaration(
    name="press_dtmf",
    description="Press a DTMF touch-tone digit on the current phone call to navigate an IVR menu.",
    parameters={"type": "OBJECT", "properties": {"digit": {"type": "STRING"}}, "required": ["digit"]},
)
_REPORT_CALL_OUTCOME_FUNCTION = genai_types.FunctionDeclaration(
    name="report_call_outcome",
    description="Report the final resolved (or unresolved) outcome of this call and end the task.",
    parameters={
        "type": "OBJECT",
        "properties": {
            "status": {"type": "STRING", "enum": ["connected_resolved", "connected_unresolved"]},
            "structured_data_json": {"type": "STRING", "description": "A JSON object string of any extracted facts."},
            "transcript_summary": {"type": "STRING"},
            "confidence": {"type": "NUMBER"},
        },
        "required": ["status", "structured_data_json", "transcript_summary", "confidence"],
    },
)


def _default_client_factory(settings: Settings) -> Callable[[], Any]:
    def factory() -> Any:
        return genai.Client(vertexai=True, project=settings.gcp_project_id, location=settings.vertex_ai_location)
    return factory


class CallReasoningBridge:
    """A second, narrower Gemini Live session scoped to one bounded call
    goal — audio in, DTMF/outcome function calls out, never synthesized
    speech back into the call (master spec §7.1's own diagram: "IVR Audio
    In, DTMF Out"). See this task's Interfaces note for why this is not a
    branch on GeminiLiveBridge."""

    def __init__(self, settings: Settings, call_goal: CallGoal, client_factory: Callable[[], Any] | None = None) -> None:
        self._settings = settings
        self._call_goal = call_goal
        self._client_factory = client_factory or _default_client_factory(settings)
        self._live_session: Any | None = None
        self._session_cm: Any | None = None
        self._on_dtmf: Callable[[str], Awaitable[None]] | None = None
        self._on_outcome: Callable[[CallOutcome], Awaitable[None]] | None = None
        self._turns = 0
        self._outcome_reported = False

    def set_on_dtmf(self, callback: Callable[[str], Awaitable[None]]) -> None:
        self._on_dtmf = callback

    def set_on_outcome(self, callback: Callable[[CallOutcome], Awaitable[None]]) -> None:
        self._on_outcome = callback

    async def connect(self) -> None:
        client = self._client_factory()
        instruction = (
            "You are listening to a live phone call's audio on behalf of a blind user. "
            f"Your single bounded goal: {self._call_goal.purpose}. "
            f"You need to resolve: {self._call_goal.structured_question}. "
            "Call press_dtmf to navigate any IVR menu one digit at a time. "
            "Once you have a resolved answer, or once it's clear this call cannot resolve it, "
            "call report_call_outcome exactly once and stop."
        )
        self._session_cm = client.aio.live.connect(
            model=self._settings.gemini_live_model,
            config=genai_types.LiveConnectConfig(
                response_modalities=["TEXT"],
                input_audio_transcription=genai_types.AudioTranscriptionConfig(),
                tools=[genai_types.Tool(function_declarations=[_PRESS_DTMF_FUNCTION, _REPORT_CALL_OUTCOME_FUNCTION])],
                system_instruction=instruction,
            ),
        )
        self._live_session = await self._session_cm.__aenter__()

    async def send_audio(self, chunk: bytes) -> None:
        if self._live_session is None:
            raise RuntimeError("call connect() before send_audio()")
        await self._live_session.send_realtime_input(audio=genai_types.Blob(data=chunk, mime_type=INPUT_MIME_TYPE))

    async def run(self) -> None:
        """Consumes tool calls until report_call_outcome fires or the turn
        budget is exhausted. Mirrors GeminiLiveBridge.receive_audio()'s
        long-running-consumer shape, driven concurrently with send_audio()
        by whoever owns this bridge (Task 12's Media Stream WS handler) —
        not invoked per-send."""
        if self._live_session is None:
            raise RuntimeError("call connect() before run()")
        async for response in self._live_session.receive():
            if response.tool_call is not None:
                await self._handle_tool_call(response.tool_call)
            if self._outcome_reported:
                return
            if self._turns >= MAX_CALL_TURNS:
                await self._report_unresolved("Turn budget exhausted before a clear resolution.")
                return

    async def _handle_tool_call(self, tool_call: Any) -> None:
        self._turns += 1
        for fc in tool_call.function_calls:
            if fc.name == "press_dtmf" and self._on_dtmf is not None:
                await self._on_dtmf(str(fc.args.get("digit", "")))
            elif fc.name == "report_call_outcome":
                structured_data = json.loads(fc.args.get("structured_data_json") or "{}")
                outcome = CallOutcome(
                    status=str(fc.args.get("status", "connected_unresolved")),
                    structured_data=structured_data,
                    transcript_summary=str(fc.args.get("transcript_summary", "")),
                    confidence=float(fc.args.get("confidence", 0.0)),
                )
                self._outcome_reported = True
                if self._on_outcome is not None:
                    await self._on_outcome(outcome)
            await self._live_session.send_tool_response(
                function_responses=genai_types.FunctionResponse(id=fc.id, name=fc.name, response={"status": "received"})
            )

    async def _report_unresolved(self, reason: str) -> None:
        self._outcome_reported = True
        if self._on_outcome is not None:
            await self._on_outcome(
                CallOutcome(status="connected_unresolved", structured_data={}, transcript_summary=reason, confidence=0.0)
            )

    async def close(self) -> None:
        session_cm, self._session_cm = self._session_cm, None
        self._live_session = None
        if session_cm is not None:
            await session_cm.__aexit__(None, None, None)
