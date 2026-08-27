import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types

from app.core.config import Settings

logger = logging.getLogger(__name__)

#: Gemini Live accepts raw 16-bit signed little-endian PCM, mono, at 16 kHz on
#: the input side. The rate parameter is not optional — without it the service
#: has to guess, and the browser capture path (`frontend/lib/session/audio.ts`,
#: `CAPTURE_SAMPLE_RATE`) is pinned to the same value. Change both together.
INPUT_SAMPLE_RATE = 16_000
INPUT_MIME_TYPE = f"audio/pcm;rate={INPUT_SAMPLE_RATE}"

#: Gemini Live's only channel for reporting what it sees in a camera frame —
#: a structured function call, not free text, so PerceptionAgent (the one
#: place raw model output gets parsed) has a fixed shape to read instead of
#: another prose string to interpret.
_SCENE_OBSERVATION_FUNCTION = genai_types.FunctionDeclaration(
    name="report_scene_observation",
    description="Report what the camera currently sees. Call this once for every camera frame received.",
    parameters={
        "type": "OBJECT",
        "properties": {
            "text_detected": {"type": "BOOLEAN", "description": "Whether readable text is visible in frame."},
            "position": {
                "type": "STRING",
                "enum": ["left", "right", "center", "too-close", "too-far", "none"],
                "description": "Where the readable text is relative to frame center, or 'none' if not detected.",
            },
            "signage_text": {"type": "STRING", "description": "The legible text, if any; empty string otherwise."},
            "confidence": {"type": "NUMBER", "description": "Confidence 0.0-1.0 in the signage_text reading."},
        },
        "required": ["text_detected", "position", "signage_text", "confidence"],
    },
)

_SCENE_OBSERVATION_SYSTEM_INSTRUCTION = (
    "You will periodically receive camera frames from a blind or low-vision user's device. "
    "For every frame, call report_scene_observation exactly once describing what you see. "
    "Do not speak about what the camera sees — only call the tool."
)


def _default_client_factory(settings: Settings) -> Callable[[], Any]:
    def factory() -> Any:
        return genai.Client(
            vertexai=True,
            project=settings.gcp_project_id,
            location=settings.vertex_ai_location,
        )

    return factory


class GeminiLiveBridge:
    """Wraps a single Gemini Live API session so it can be relayed to and from
    a browser WebSocket, with the user's spoken utterances transcribed for the
    agent loop and only orchestrator-vetted text ever spoken back."""

    def __init__(
        self,
        settings: Settings,
        client_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._settings = settings
        self._client_factory = client_factory or _default_client_factory(settings)
        self._live_session: Any | None = None
        self._session_cm: Any | None = None
        self._on_input_transcript: Callable[[str], Awaitable[None]] | None = None
        # Gemini keeps generating its own spoken reply to every raw mic turn
        # (there is no config flag to suppress that generation) — the trust
        # boundary is enforced here instead, by only forwarding audio that
        # arrives during a turn *we* triggered via speak(). Everything else
        # is generated, then thrown away unheard.
        #
        # `_relay_current_turn` alone isn't enough: it only knows "a turn is
        # currently open for relay", not which turn produced which chunk. If
        # speak() is called (as Task 15's transcript callback does) while an
        # unrelated turn — e.g. Gemini's automatic reply to the same raw-mic
        # input — is still in flight, flipping the flag immediately would let
        # that turn's remaining, unvetted chunks slip through. So speak()
        # only starts relaying immediately at a clean turn boundary
        # (`_turn_active` False); otherwise it defers via
        # `_pending_speak_relay` until the in-flight turn closes.
        self._turn_active = False
        self._relay_current_turn = False
        self._pending_speak_relay = False
        self._pending_input_transcript = ""
        self._on_scene_observation: Callable[[dict], Awaitable[None]] | None = None

    def set_on_input_transcript(self, callback: Callable[[str], Awaitable[None]]) -> None:
        self._on_input_transcript = callback

    def set_on_scene_observation(self, callback: Callable[[dict], Awaitable[None]]) -> None:
        self._on_scene_observation = callback

    async def connect(self) -> None:
        client = self._client_factory()
        # `client.aio.live.connect(...)` is an @asynccontextmanager, so the
        # object it returns — not the `AsyncSession` it yields — owns the
        # teardown. Retaining only the yielded session would leave the
        # generator suspended at its `yield` forever, so the `async with
        # websockets.connect(...)` block wrapping it never unwinds. Keep the
        # context manager itself and finalize it in close().
        self._session_cm = client.aio.live.connect(
            model=self._settings.gemini_live_model,
            config=genai_types.LiveConnectConfig(
                response_modalities=["AUDIO"],
                input_audio_transcription=genai_types.AudioTranscriptionConfig(),
                output_audio_transcription=genai_types.AudioTranscriptionConfig(),
                tools=[genai_types.Tool(function_declarations=[_SCENE_OBSERVATION_FUNCTION])],
                system_instruction=_SCENE_OBSERVATION_SYSTEM_INSTRUCTION,
            ),
        )
        self._live_session = await self._session_cm.__aenter__()

    async def send_audio(self, chunk: bytes) -> None:
        if self._live_session is None:
            raise RuntimeError("call connect() before send_audio()")
        await self._live_session.send_realtime_input(
            audio=genai_types.Blob(data=chunk, mime_type=INPUT_MIME_TYPE)
        )

    async def send_video_frame(self, jpeg_bytes: bytes) -> None:
        if self._live_session is None:
            raise RuntimeError("call connect() before send_video_frame()")
        await self._live_session.send_realtime_input(video=genai_types.Blob(data=jpeg_bytes, mime_type="image/jpeg"))

    async def speak(self, text: str) -> None:
        """Send orchestrator-vetted text as a model turn for Gemini to
        vocalize. If no turn is currently in flight, the very next turn's
        audio is relayed immediately. If an unrelated turn is still open
        (e.g. Task 15 calling this from inside the transcript callback while
        Gemini's automatic reply to that same raw-mic turn hasn't reached
        `turn_complete` yet), relaying is deferred via
        `_pending_speak_relay` until that turn closes — see
        `receive_audio()`."""
        if self._live_session is None:
            raise RuntimeError("call connect() before speak()")
        if self._turn_active:
            self._pending_speak_relay = True
        else:
            self._relay_current_turn = True
        await self._live_session.send_client_content(
            turns=genai_types.Content(role="model", parts=[genai_types.Part(text=text)]),
            turn_complete=True,
        )

    async def receive_audio(self) -> AsyncIterator[bytes]:
        if self._live_session is None:
            raise RuntimeError("call connect() before receive_audio()")
        # In this SDK version AsyncSession.receive() ends its iterator at each
        # turn_complete, so a single `async for` would relay exactly one model
        # turn and then let the whole session tear down. Restart it per turn
        # for the life of the socket; a close surfaces as an APIError carrying
        # a WebSocket close code (>= 1000), which ends the generator cleanly
        # rather than bubbling up as a session failure.
        while True:
            saw_response = False
            try:
                async for response in self._live_session.receive():
                    saw_response = True
                    if response.tool_call is not None:
                        await self._handle_tool_call(response.tool_call)

                    content = response.server_content
                    if content is not None:
                        self._turn_active = True
                        transcript = content.input_transcription
                        if transcript is not None and transcript.text:
                            self._pending_input_transcript += transcript.text
                        if transcript is not None and transcript.finished and self._pending_input_transcript:
                            finished_text, self._pending_input_transcript = self._pending_input_transcript, ""
                            if self._on_input_transcript is not None:
                                await self._on_input_transcript(finished_text)

                    if self._relay_current_turn and response.data is not None:
                        yield response.data
                    elif response.data is not None:
                        logger.debug("discarding unvetted audio chunk outside a speak() turn")

                    if content is not None and (content.turn_complete or content.interrupted):
                        self._turn_active = False
                        if self._pending_speak_relay:
                            self._relay_current_turn = True
                            self._pending_speak_relay = False
                        else:
                            self._relay_current_turn = False
            except genai_errors.APIError as exc:
                # A WebSocket close surfaces here with a close code (>= 1000);
                # end the stream cleanly rather than failing the session.
                if exc.code and exc.code >= 1000:
                    logger.info("gemini_live_session_closed", extra={"close_code": exc.code})
                    return
                raise
            # A real session blocks in receive() between turns; an iterator
            # that yields nothing means the session object is exhausted (the
            # socket is gone, or — in tests — the fake has no more messages).
            if not saw_response:
                return

    async def _handle_tool_call(self, tool_call: Any) -> None:
        for fc in tool_call.function_calls:
            if fc.name == "report_scene_observation" and self._on_scene_observation is not None:
                await self._on_scene_observation(dict(fc.args))
            await self._live_session.send_tool_response(
                function_responses=genai_types.FunctionResponse(id=fc.id, name=fc.name, response={"status": "received"})
            )

    async def close(self) -> None:
        """Finalize the Live session, idempotently. Only `__aexit__` is
        called, not `AsyncSession.close()` — in the installed SDK,
        `AsyncLive.connect()` wraps its `yield` in `async with
        websockets.connect(uri, ...) as ws:`, so finalizing the context
        manager closes the same socket *and* unwinds the websockets client
        that owns it, making `__aexit__` a strict superset."""
        session_cm, self._session_cm = self._session_cm, None
        self._live_session = None
        if session_cm is not None:
            await session_cm.__aexit__(None, None, None)
