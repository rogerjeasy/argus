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

#: (name, args) -> the function response dict Gemini should see.
ToolHandler = Callable[[str, dict], Awaitable[dict]]


def _default_client_factory(settings: Settings) -> Callable[[], Any]:
    def factory() -> Any:
        return genai.Client(
            vertexai=True,
            project=settings.gcp_project_id,
            location=settings.vertex_ai_location,
        )

    return factory


class GeminiLiveBridge:
    """Wraps a single Gemini Live API session and relays it to and from a
    browser WebSocket. Gemini is the conversational agent: its own spoken
    audio is what the user hears, its function calls are dispatched to the
    real backends through the injected tool handler, and its transcription
    of the user is forwarded for deterministic safety checks (distress
    keywords) only — routing and planning are the model's job now, not a
    fixed pipeline's."""

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
        self._tool_handler: ToolHandler | None = None
        self._system_instruction: str | None = None
        self._tool_declarations: list[genai_types.FunctionDeclaration] = []
        self._pending_input_transcript = ""

    def configure(
        self,
        *,
        system_instruction: str,
        tool_declarations: list[genai_types.FunctionDeclaration],
        tool_handler: ToolHandler,
    ) -> None:
        self._system_instruction = system_instruction
        self._tool_declarations = tool_declarations
        self._tool_handler = tool_handler

    def set_on_input_transcript(self, callback: Callable[[str], Awaitable[None]]) -> None:
        self._on_input_transcript = callback

    async def connect(self) -> None:
        client = self._client_factory()
        config_kwargs: dict[str, Any] = {
            "response_modalities": ["AUDIO"],
            "input_audio_transcription": genai_types.AudioTranscriptionConfig(),
            "output_audio_transcription": genai_types.AudioTranscriptionConfig(),
        }
        if self._system_instruction:
            config_kwargs["system_instruction"] = self._system_instruction
        if self._tool_declarations:
            config_kwargs["tools"] = [genai_types.Tool(function_declarations=self._tool_declarations)]
        # `client.aio.live.connect(...)` is an @asynccontextmanager, so the
        # object it returns — not the `AsyncSession` it yields — owns the
        # teardown. Retaining only the yielded session would leave the
        # generator suspended at its `yield` forever, so the `async with
        # websockets.connect(...)` block wrapping it never unwinds. Keep the
        # context manager itself and finalize it in close().
        self._session_cm = client.aio.live.connect(
            model=self._settings.gemini_live_model,
            config=genai_types.LiveConnectConfig(**config_kwargs),
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
        """Have Gemini say a backend-authored line (a session-open briefing,
        a framing nudge, an escalation notice). Injected as a model turn;
        its audio flows to the user like any other turn's."""
        if self._live_session is None:
            raise RuntimeError("call connect() before speak()")
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
        # a WebSocket close code (>= 1000), which ends the generator cleanly.
        while True:
            saw_response = False
            try:
                async for response in self._live_session.receive():
                    saw_response = True
                    if response.tool_call is not None:
                        await self._handle_tool_call(response.tool_call)

                    content = response.server_content
                    if content is not None:
                        transcript = content.input_transcription
                        if transcript is not None and transcript.text:
                            self._pending_input_transcript += transcript.text
                        if transcript is not None and transcript.finished and self._pending_input_transcript:
                            finished_text, self._pending_input_transcript = self._pending_input_transcript, ""
                            if self._on_input_transcript is not None:
                                await self._on_input_transcript(finished_text)

                    if response.data is not None:
                        yield response.data
            except genai_errors.APIError as exc:
                if exc.code and exc.code >= 1000:
                    logger.info("gemini_live_session_closed", extra={"close_code": exc.code})
                    return
                raise
            if not saw_response:
                return

    async def _handle_tool_call(self, tool_call: Any) -> None:
        for fc in tool_call.function_calls:
            if self._tool_handler is not None:
                response = await self._tool_handler(fc.name, dict(fc.args or {}))
            else:
                response = {"error": "no tools available"}
            await self._live_session.send_tool_response(
                function_responses=genai_types.FunctionResponse(id=fc.id, name=fc.name, response=response)
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
