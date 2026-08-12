from collections.abc import AsyncIterator, Callable
from typing import Any

from google import genai
from google.genai import types as genai_types

from app.core.config import Settings


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

    async def connect(self) -> None:
        client = self._client_factory()
        self._live_session = await client.aio.live.connect(
            model=self._settings.gemini_live_model,
            config=genai_types.LiveConnectConfig(response_modalities=["AUDIO"]),
        ).__aenter__()

    async def send_audio(self, chunk: bytes) -> None:
        if self._live_session is None:
            raise RuntimeError("call connect() before send_audio()")
        await self._live_session.send(input={"data": chunk, "mime_type": "audio/pcm"})

    async def receive_audio(self) -> AsyncIterator[bytes]:
        if self._live_session is None:
            raise RuntimeError("call connect() before receive_audio()")
        async for response in self._live_session.receive():
            if response.data is not None:
                yield response.data

    async def close(self) -> None:
        if self._live_session is not None:
            await self._live_session.close()
            self._live_session = None
