from collections.abc import AsyncIterator
from unittest.mock import MagicMock

import pytest

from app.core.config import Settings
from app.ws.gemini_bridge import INPUT_MIME_TYPE, GeminiLiveBridge


class _FakeServerContent:
    def __init__(
        self,
        *,
        data: bytes | None = None,
        input_transcript: tuple[str, bool] | None = None,
        turn_complete: bool = False,
        interrupted: bool = False,
    ) -> None:
        self.data = data
        self.turn_complete = turn_complete
        self.interrupted = interrupted
        if input_transcript is not None:
            text, finished = input_transcript
            self.input_transcription = MagicMock(text=text, finished=finished)
        else:
            self.input_transcription = None


class _FakeMessage:
    def __init__(
        self, *, server_content: _FakeServerContent | None = None, data: bytes | None = None, tool_call=None
    ) -> None:
        self.server_content = server_content
        self.data = data
        self.tool_call = tool_call


class _FakeLiveSession:
    """Stands in for `google.genai.live.AsyncSession`. `close()` and
    `__aexit__` are tracked separately so a test can tell which one the
    bridge actually invoked."""

    def __init__(self, replies: list[_FakeMessage]) -> None:
        self._replies = replies
        self.realtime_sent: list[dict] = []
        self.video_sent: list[dict] = []
        self.client_content_sent: list[dict] = []
        self.tool_responses_sent: list = []
        self.close_calls = 0
        self.aexit_calls = 0

    @property
    def closed(self) -> bool:
        return self.close_calls > 0 or self.aexit_calls > 0

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
        for message in self._replies:
            yield message

    async def close(self) -> None:
        self.close_calls += 1

    async def __aenter__(self) -> "_FakeLiveSession":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        self.aexit_calls += 1


def _settings() -> Settings:
    return Settings(gcp_project_id="p", vertex_ai_location="us-central1", gemini_live_model="m")


@pytest.mark.asyncio
async def test_send_audio_forwards_bytes_via_realtime_input() -> None:
    fake_session = _FakeLiveSession(replies=[])
    fake_client = MagicMock()
    fake_client.aio.live.connect.return_value = fake_session

    bridge = GeminiLiveBridge(_settings(), client_factory=lambda: fake_client)
    await bridge.connect()
    await bridge.send_audio(b"hello-pcm")

    assert fake_session.realtime_sent == [{"data": b"hello-pcm", "mime_type": INPUT_MIME_TYPE}]


@pytest.mark.asyncio
async def test_send_audio_declares_the_sample_rate_gemini_live_expects() -> None:
    assert INPUT_MIME_TYPE == "audio/pcm;rate=16000"


@pytest.mark.asyncio
async def test_receive_audio_discards_chunks_outside_a_speak_turn() -> None:
    # Simulates Gemini's automatic reply to raw mic input: audio arrives with
    # no preceding speak() call, so it must never reach the consumer.
    replies = [
        _FakeMessage(server_content=_FakeServerContent(data=b"auto-reply", turn_complete=True), data=b"auto-reply"),
    ]
    fake_session = _FakeLiveSession(replies=replies)
    fake_client = MagicMock()
    fake_client.aio.live.connect.return_value = fake_session

    bridge = GeminiLiveBridge(_settings(), client_factory=lambda: fake_client)
    await bridge.connect()

    received = [chunk async for chunk in bridge.receive_audio()]
    assert received == []


@pytest.mark.asyncio
async def test_receive_audio_forwards_chunks_during_a_speak_turn() -> None:
    fake_session = _FakeLiveSession(
        replies=[_FakeMessage(server_content=_FakeServerContent(data=b"vetted-reply", turn_complete=True), data=b"vetted-reply")]
    )
    fake_client = MagicMock()
    fake_client.aio.live.connect.return_value = fake_session

    bridge = GeminiLiveBridge(_settings(), client_factory=lambda: fake_client)
    await bridge.connect()
    await bridge.speak("turn left at the platform")

    received = [chunk async for chunk in bridge.receive_audio()]
    assert received == [b"vetted-reply"]
    assert fake_session.client_content_sent == [{"text": "turn left at the platform", "turn_complete": True}]


@pytest.mark.asyncio
async def test_receive_audio_stops_relaying_after_turn_complete() -> None:
    replies = [
        _FakeMessage(server_content=_FakeServerContent(data=b"vetted-1", turn_complete=True), data=b"vetted-1"),
        _FakeMessage(server_content=_FakeServerContent(data=b"unvetted-2", turn_complete=False), data=b"unvetted-2"),
    ]
    fake_session = _FakeLiveSession(replies=replies)
    fake_client = MagicMock()
    fake_client.aio.live.connect.return_value = fake_session

    bridge = GeminiLiveBridge(_settings(), client_factory=lambda: fake_client)
    await bridge.connect()
    await bridge.speak("go")

    received = [chunk async for chunk in bridge.receive_audio()]
    assert received == [b"vetted-1"]


@pytest.mark.asyncio
async def test_receive_audio_defers_relay_until_an_in_flight_turn_closes() -> None:
    # Task 15's exact wiring: the transcript callback calls bridge.speak()
    # from *inside* receive_audio()'s loop, while Gemini's automatic reply to
    # the same raw-mic turn may still be delivering chunks (turn_complete not
    # yet seen). speak() must not start relaying until that unrelated,
    # already-in-flight turn genuinely closes — otherwise its remaining
    # unvetted chunks would be yielded as if they were vetted.
    replies = [
        _FakeMessage(server_content=_FakeServerContent(data=b"auto-1", turn_complete=False), data=b"auto-1"),
        _FakeMessage(server_content=_FakeServerContent(input_transcript=("hi", True)), data=None),
        _FakeMessage(server_content=_FakeServerContent(data=b"auto-2", turn_complete=True), data=b"auto-2"),
        _FakeMessage(server_content=_FakeServerContent(data=b"vetted-1", turn_complete=True), data=b"vetted-1"),
    ]
    fake_session = _FakeLiveSession(replies=replies)
    fake_client = MagicMock()
    fake_client.aio.live.connect.return_value = fake_session

    bridge = GeminiLiveBridge(_settings(), client_factory=lambda: fake_client)

    async def on_transcript(text: str) -> None:
        await bridge.speak("reply")

    bridge.set_on_input_transcript(on_transcript)
    await bridge.connect()

    received = [chunk async for chunk in bridge.receive_audio()]
    assert received == [b"vetted-1"]
    assert fake_session.client_content_sent == [{"text": "reply", "turn_complete": True}]


@pytest.mark.asyncio
async def test_receive_audio_resets_relay_when_a_speak_turn_is_interrupted() -> None:
    # Barge-in can interrupt a speak()-triggered turn before it reaches
    # turn_complete. If relay state doesn't reset on `interrupted` too, it
    # leaks forever and forwards whatever unrelated turn comes next.
    replies = [
        _FakeMessage(server_content=_FakeServerContent(data=b"vetted-partial", interrupted=True), data=b"vetted-partial"),
        _FakeMessage(server_content=_FakeServerContent(data=b"unrelated-auto", turn_complete=True), data=b"unrelated-auto"),
    ]
    fake_session = _FakeLiveSession(replies=replies)
    fake_client = MagicMock()
    fake_client.aio.live.connect.return_value = fake_session

    bridge = GeminiLiveBridge(_settings(), client_factory=lambda: fake_client)
    await bridge.connect()
    await bridge.speak("go")

    received = [chunk async for chunk in bridge.receive_audio()]
    assert received == [b"vetted-partial"]


@pytest.mark.asyncio
async def test_receive_audio_invokes_callback_on_finished_transcript() -> None:
    replies = [
        _FakeMessage(server_content=_FakeServerContent(input_transcript=("get me to ", False)), data=None),
        _FakeMessage(server_content=_FakeServerContent(input_transcript=("platform 4", True)), data=None),
    ]
    fake_session = _FakeLiveSession(replies=replies)
    fake_client = MagicMock()
    fake_client.aio.live.connect.return_value = fake_session

    seen: list[str] = []

    async def on_transcript(text: str) -> None:
        seen.append(text)

    bridge = GeminiLiveBridge(_settings(), client_factory=lambda: fake_client)
    bridge.set_on_input_transcript(on_transcript)
    await bridge.connect()

    [_ async for _ in bridge.receive_audio()]
    assert seen == ["get me to platform 4"]


@pytest.mark.asyncio
async def test_receive_audio_is_a_no_op_when_no_transcript_callback_is_set() -> None:
    # set_on_input_transcript() is optional — a bridge used without ever
    # calling it (e.g. a test exercising only audio relay) must not raise.
    replies = [_FakeMessage(server_content=_FakeServerContent(input_transcript=("hello", True)), data=None)]
    fake_session = _FakeLiveSession(replies=replies)
    fake_client = MagicMock()
    fake_client.aio.live.connect.return_value = fake_session

    bridge = GeminiLiveBridge(_settings(), client_factory=lambda: fake_client)
    await bridge.connect()

    received = [chunk async for chunk in bridge.receive_audio()]
    assert received == []


@pytest.mark.asyncio
async def test_close_finalizes_the_connect_context_manager() -> None:
    fake_session = _FakeLiveSession(replies=[])
    fake_client = MagicMock()
    fake_client.aio.live.connect.return_value = fake_session

    bridge = GeminiLiveBridge(_settings(), client_factory=lambda: fake_client)
    await bridge.connect()
    await bridge.close()

    assert fake_session.aexit_calls == 1
    assert fake_session.closed is True


@pytest.mark.asyncio
async def test_close_is_idempotent_and_safe_before_connect() -> None:
    fake_session = _FakeLiveSession(replies=[])
    fake_client = MagicMock()
    fake_client.aio.live.connect.return_value = fake_session

    bridge = GeminiLiveBridge(_settings(), client_factory=lambda: fake_client)
    await bridge.close()  # never connected — must not raise

    await bridge.connect()
    await bridge.close()
    await bridge.close()

    assert fake_session.aexit_calls == 1


@pytest.mark.asyncio
async def test_connect_configures_the_scene_observation_tool() -> None:
    fake_session = _FakeLiveSession(replies=[])
    fake_client = MagicMock()
    fake_client.aio.live.connect.return_value = fake_session

    bridge = GeminiLiveBridge(_settings(), client_factory=lambda: fake_client)
    await bridge.connect()

    _, kwargs = fake_client.aio.live.connect.call_args
    tools = kwargs["config"].tools
    assert tools is not None
    names = [fd.name for tool in tools for fd in tool.function_declarations]
    assert "report_scene_observation" in names


@pytest.mark.asyncio
async def test_send_video_frame_sends_a_video_blob() -> None:
    fake_session = _FakeLiveSession(replies=[])
    fake_client = MagicMock()
    fake_client.aio.live.connect.return_value = fake_session

    bridge = GeminiLiveBridge(_settings(), client_factory=lambda: fake_client)
    await bridge.connect()
    await bridge.send_video_frame(b"fake-jpeg-bytes")

    assert fake_session.video_sent == [{"data": b"fake-jpeg-bytes", "mime_type": "image/jpeg"}]


@pytest.mark.asyncio
async def test_receive_audio_dispatches_tool_calls_and_acks_them() -> None:
    from google.genai import types as genai_types

    function_call = genai_types.FunctionCall(id="call-1", name="report_scene_observation", args={"text_detected": True})
    replies = [_FakeMessage(tool_call=genai_types.LiveServerToolCall(function_calls=[function_call]))]
    fake_session = _FakeLiveSession(replies=replies)
    fake_client = MagicMock()
    fake_client.aio.live.connect.return_value = fake_session

    bridge = GeminiLiveBridge(_settings(), client_factory=lambda: fake_client)
    received_args = []

    async def _on_observation(args: dict) -> None:
        received_args.append(args)

    bridge.set_on_scene_observation(_on_observation)
    await bridge.connect()

    received = [chunk async for chunk in bridge.receive_audio()]

    assert received == []  # no server_content/data on this reply — only the tool-call side effect matters
    assert received_args == [{"text_detected": True}]
    assert len(fake_session.tool_responses_sent) == 1
    assert fake_session.tool_responses_sent[0].id == "call-1"


@pytest.mark.asyncio
async def test_receive_audio_ignores_tool_calls_when_no_callback_is_set() -> None:
    # Mirrors test_receive_audio_is_a_no_op_when_no_transcript_callback_is_set
    # — set_on_scene_observation() is likewise optional, and an unset
    # callback must still ack the tool call (Gemini blocks the turn on an
    # un-acked function call) without raising.
    from google.genai import types as genai_types

    function_call = genai_types.FunctionCall(id="call-1", name="report_scene_observation", args={})
    replies = [_FakeMessage(tool_call=genai_types.LiveServerToolCall(function_calls=[function_call]))]
    fake_session = _FakeLiveSession(replies=replies)
    fake_client = MagicMock()
    fake_client.aio.live.connect.return_value = fake_session

    bridge = GeminiLiveBridge(_settings(), client_factory=lambda: fake_client)
    await bridge.connect()

    received = [chunk async for chunk in bridge.receive_audio()]

    assert received == []
    assert len(fake_session.tool_responses_sent) == 1
