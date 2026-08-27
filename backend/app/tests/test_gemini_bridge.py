from collections.abc import AsyncIterator
from unittest.mock import MagicMock

import pytest
from google.genai import errors as genai_errors
from google.genai import types as genai_types

from app.core.config import Settings
from app.ws.gemini_bridge import INPUT_MIME_TYPE, GeminiLiveBridge


class _FakeServerContent:
    def __init__(self, *, input_transcript: tuple[str, bool] | None = None,
                 turn_complete: bool = False, interrupted: bool = False) -> None:
        self.turn_complete = turn_complete
        self.interrupted = interrupted
        if input_transcript is not None:
            text, finished = input_transcript
            self.input_transcription = MagicMock(text=text, finished=finished)
        else:
            self.input_transcription = None


class _FakeMessage:
    def __init__(self, *, server_content=None, data=None, tool_call=None) -> None:
        self.server_content = server_content
        self.data = data
        self.tool_call = tool_call


class _FakeLiveSession:
    def __init__(self, replies: list[_FakeMessage]) -> None:
        self._replies = replies
        self.realtime_sent: list[dict] = []
        self.video_sent: list[dict] = []
        self.client_content_sent: list[dict] = []
        self.tool_responses_sent: list = []
        self.aexit_calls = 0

    async def send_realtime_input(self, *, audio=None, video=None) -> None:
        if audio is not None:
            self.realtime_sent.append({"data": audio.data, "mime_type": audio.mime_type})
        if video is not None:
            self.video_sent.append({"data": video.data, "mime_type": video.mime_type})

    async def send_client_content(self, *, turns, turn_complete: bool) -> None:
        self.client_content_sent.append({"text": turns.parts[0].text, "turn_complete": turn_complete})

    async def send_tool_response(self, *, function_responses) -> None:
        self.tool_responses_sent.append(function_responses)

    async def receive(self) -> AsyncIterator[_FakeMessage]:
        # Real receive() ends its iterator at turn_complete and is called
        # again per turn — hand out the scripted replies once, then act
        # exhausted so the bridge's per-turn loop terminates.
        replies, self._replies = self._replies, []
        for message in replies:
            yield message

    async def __aenter__(self) -> "_FakeLiveSession":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        self.aexit_calls += 1


def _settings() -> Settings:
    return Settings(gcp_project_id="p", vertex_ai_location="us-central1", gemini_live_model="m")


def _bridge(replies: list[_FakeMessage]) -> tuple[GeminiLiveBridge, _FakeLiveSession]:
    session = _FakeLiveSession(replies)
    client = MagicMock()
    client.aio.live.connect.return_value = session
    return GeminiLiveBridge(_settings(), client_factory=lambda: client), session


@pytest.mark.asyncio
async def test_send_audio_declares_the_sample_rate_gemini_live_expects() -> None:
    assert INPUT_MIME_TYPE == "audio/pcm;rate=16000"
    bridge, session = _bridge([])
    await bridge.connect()
    await bridge.send_audio(b"pcm")
    assert session.realtime_sent == [{"data": b"pcm", "mime_type": INPUT_MIME_TYPE}]


@pytest.mark.asyncio
async def test_send_video_frame_sends_a_jpeg_blob() -> None:
    bridge, session = _bridge([])
    await bridge.connect()
    await bridge.send_video_frame(b"jpeg")
    assert session.video_sent == [{"data": b"jpeg", "mime_type": "image/jpeg"}]


@pytest.mark.asyncio
async def test_receive_audio_relays_every_audio_chunk_gemini_sends() -> None:
    replies = [
        _FakeMessage(data=b"chunk-1"),
        _FakeMessage(data=b"chunk-2", server_content=_FakeServerContent(turn_complete=True)),
    ]
    bridge, _ = _bridge(replies)
    await bridge.connect()

    assert [c async for c in bridge.receive_audio()] == [b"chunk-1", b"chunk-2"]


@pytest.mark.asyncio
async def test_receive_audio_forwards_a_finished_transcript_to_the_callback() -> None:
    replies = [
        _FakeMessage(server_content=_FakeServerContent(input_transcript=("hello", False))),
        _FakeMessage(server_content=_FakeServerContent(input_transcript=(" there", True))),
    ]
    bridge, _ = _bridge(replies)
    heard: list[str] = []

    async def _cb(text: str) -> None:
        heard.append(text)

    bridge.set_on_input_transcript(_cb)
    await bridge.connect()
    _ = [c async for c in bridge.receive_audio()]

    assert heard == ["hello there"]


@pytest.mark.asyncio
async def test_tool_calls_are_dispatched_to_the_handler_and_the_result_is_returned() -> None:
    fc = genai_types.FunctionCall(id="c1", name="get_transit_directions", args={"station": "North Station"})
    replies = [_FakeMessage(tool_call=genai_types.LiveServerToolCall(function_calls=[fc]))]
    bridge, session = _bridge(replies)

    calls: list[tuple[str, dict]] = []

    async def _handler(name: str, args: dict) -> dict:
        calls.append((name, args))
        return {"platform": "7"}

    bridge.configure(system_instruction="be helpful", tool_declarations=[], tool_handler=_handler)
    await bridge.connect()
    _ = [c async for c in bridge.receive_audio()]

    assert calls == [("get_transit_directions", {"station": "North Station"})]
    assert session.tool_responses_sent[0].response == {"platform": "7"}


@pytest.mark.asyncio
async def test_configure_puts_the_system_instruction_and_tools_on_the_connect_config() -> None:
    bridge, _ = _bridge([])
    decl = genai_types.FunctionDeclaration(name="t", description="d", parameters={"type": "OBJECT", "properties": {}})

    async def _handler(name, args):
        return {}

    bridge.configure(system_instruction="You are Argus.", tool_declarations=[decl], tool_handler=_handler)
    await bridge.connect()

    client = bridge._client_factory()
    _, kwargs = client.aio.live.connect.call_args
    config = kwargs["config"]
    assert config.system_instruction == "You are Argus."
    assert config.tools[0].function_declarations[0].name == "t"


@pytest.mark.asyncio
async def test_speak_injects_a_model_turn() -> None:
    bridge, session = _bridge([])
    await bridge.connect()
    await bridge.speak("Head to platform 4.")
    assert session.client_content_sent == [{"text": "Head to platform 4.", "turn_complete": True}]


@pytest.mark.asyncio
async def test_receive_audio_keeps_pulling_turns_until_the_session_is_exhausted() -> None:
    class _MultiTurn(_FakeLiveSession):
        def __init__(self, turns: list[list[_FakeMessage]]) -> None:
            super().__init__(replies=[])
            self._turns = list(turns)

        async def receive(self):
            if not self._turns:
                return
            for m in self._turns.pop(0):
                yield m

    session = _MultiTurn([
        [_FakeMessage(data=b"turn-1", server_content=_FakeServerContent(turn_complete=True))],
        [_FakeMessage(data=b"turn-2", server_content=_FakeServerContent(turn_complete=True))],
    ])
    client = MagicMock()
    client.aio.live.connect.return_value = session
    bridge = GeminiLiveBridge(_settings(), client_factory=lambda: client)
    await bridge.connect()

    assert [c async for c in bridge.receive_audio()] == [b"turn-1", b"turn-2"]


@pytest.mark.asyncio
async def test_receive_audio_ends_cleanly_on_a_websocket_close() -> None:
    class _Closing(_FakeLiveSession):
        async def receive(self):
            raise genai_errors.APIError(1011, {"message": "going away"}, None)
            yield  # keeps this an async generator

    session = _Closing(replies=[])
    client = MagicMock()
    client.aio.live.connect.return_value = session
    bridge = GeminiLiveBridge(_settings(), client_factory=lambda: client)
    await bridge.connect()

    assert [c async for c in bridge.receive_audio()] == []


@pytest.mark.asyncio
async def test_close_finalizes_the_connect_context_manager_idempotently() -> None:
    bridge, session = _bridge([])
    await bridge.connect()
    await bridge.close()
    await bridge.close()
    assert session.aexit_calls == 1
