from collections.abc import AsyncIterator, Callable
from typing import Any

from google import genai
from google.genai import types as genai_types

from app.core.config import Settings

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
    """Wraps a single Gemini Live API session so it can be relayed to and from a browser WebSocket."""

    def __init__(self, settings: Settings, client_factory: Callable[[], Any] | None = None) -> None:
        self._settings = settings
        self._client_factory = client_factory or _default_client_factory(settings)
        self._live_session: Any | None = None
        self._session_cm: Any | None = None

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
            config=genai_types.LiveConnectConfig(response_modalities=["AUDIO"]),
        )
        self._live_session = await self._session_cm.__aenter__()

    async def send_audio(self, chunk: bytes) -> None:
        if self._live_session is None:
            raise RuntimeError("call connect() before send_audio()")
        await self._live_session.send(input={"data": chunk, "mime_type": INPUT_MIME_TYPE})

    async def receive_audio(self) -> AsyncIterator[bytes]:
        if self._live_session is None:
            raise RuntimeError("call connect() before receive_audio()")
        async for response in self._live_session.receive():
            if response.data is not None:
                yield response.data

    async def close(self) -> None:
        """Finalize the Live session, idempotently.

        Only `__aexit__` is called, not `AsyncSession.close()`. In
        google-genai 0.3.0 (`google/genai/live.py`) `AsyncSession.close()` is
        exactly `await self._ws.close()`, while `AsyncLive.connect()` wraps its
        `yield` in `async with websockets.connect(uri, ...) as ws:` — so
        finalizing the context manager closes the same socket *and* unwinds the
        websockets client that owns it. That makes `__aexit__` a strict
        superset. Calling both would not error (websockets' `close()` is
        idempotent) but the second call is dead weight.
        """
        session_cm, self._session_cm = self._session_cm, None
        self._live_session = None
        if session_cm is not None:
            await session_cm.__aexit__(None, None, None)
