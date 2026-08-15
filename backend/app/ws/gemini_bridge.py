import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from google import genai
from google.genai import types as genai_types

from app.core.config import Settings

logger = logging.getLogger(__name__)

#: Gemini Live accepts raw 16-bit signed little-endian PCM, mono, at 16 kHz on
#: the input side. The rate parameter is not optional — without it the service
#: has to guess, and the browser capture path (`frontend/lib/session/audio.ts`,
#: `CAPTURE_SAMPLE_RATE`) is pinned to the same value. Change both together.
INPUT_SAMPLE_RATE = 16_000
INPUT_MIME_TYPE = f"audio/pcm;rate={INPUT_SAMPLE_RATE}"


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
        self._relay_current_turn = False
        self._pending_input_transcript = ""

    def set_on_input_transcript(self, callback: Callable[[str], Awaitable[None]]) -> None:
        self._on_input_transcript = callback

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
            ),
        )
        self._live_session = await self._session_cm.__aenter__()

    async def send_audio(self, chunk: bytes) -> None:
        if self._live_session is None:
            raise RuntimeError("call connect() before send_audio()")
        await self._live_session.send_realtime_input(
            audio=genai_types.Blob(data=chunk, mime_type=INPUT_MIME_TYPE)
        )

    async def speak(self, text: str) -> None:
        """Send orchestrator-vetted text as a model turn for Gemini to
        vocalize. The very next turn's audio is the only audio
        `receive_audio()` will forward — see `_relay_current_turn`."""
        if self._live_session is None:
            raise RuntimeError("call connect() before speak()")
        self._relay_current_turn = True
        await self._live_session.send_client_content(
            turns=genai_types.Content(role="model", parts=[genai_types.Part(text=text)]),
            turn_complete=True,
        )

    async def receive_audio(self) -> AsyncIterator[bytes]:
        if self._live_session is None:
            raise RuntimeError("call connect() before receive_audio()")
        async for response in self._live_session.receive():
            content = response.server_content
            if content is not None:
                transcript = content.input_transcription
                if transcript is not None and transcript.text:
                    self._pending_input_transcript += transcript.text
                if transcript is not None and transcript.finished and self._pending_input_transcript:
                    finished_text, self._pending_input_transcript = self._pending_input_transcript, ""
                    if self._on_input_transcript is not None:
                        await self._on_input_transcript(finished_text)

            if self._relay_current_turn and response.data is not None:
                yield response.data

            if content is not None and content.turn_complete:
                self._relay_current_turn = False

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
