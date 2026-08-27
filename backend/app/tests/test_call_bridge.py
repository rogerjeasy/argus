from collections.abc import AsyncIterator
from unittest.mock import MagicMock

import pytest

from app.core.config import Settings
from app.domains.personal_admin.call_bridge import MAX_CALL_TURNS, CallReasoningBridge
from app.domains.personal_admin.models import CallGoal


class _FakeServerContent:
    def __init__(self) -> None:
        self.data = None
        self.turn_complete = False
        self.interrupted = False
        self.input_transcription = None


class _FakeMessage:
    def __init__(self, *, tool_call=None) -> None:
        self.server_content = _FakeServerContent()
        self.data = None
        self.tool_call = tool_call


class _FakeLiveSession:
    def __init__(self, replies: list[_FakeMessage]) -> None:
        self._replies = replies
        self.realtime_sent: list[dict] = []
        self.tool_responses_sent: list = []

    async def send_realtime_input(self, *, audio=None, video=None) -> None:
        if audio is not None:
            self.realtime_sent.append({"data": audio.data, "mime_type": audio.mime_type})

    async def send_tool_response(self, *, function_responses) -> None:
        self.tool_responses_sent.append(function_responses)

    async def receive(self) -> AsyncIterator[_FakeMessage]:
        # The real AsyncSession.receive() ends its iterator at each
        # turn_complete and run() calls it again per turn — hand out the
        # scripted replies once, then act like an exhausted session.
        replies, self._replies = self._replies, []
        for message in replies:
            yield message

    async def close(self) -> None:
        pass

    async def __aenter__(self) -> "_FakeLiveSession":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        pass


def _settings() -> Settings:
    return Settings(gcp_project_id="p", vertex_ai_location="us-central1", gemini_live_model="m")


def _call_goal() -> CallGoal:
    return CallGoal(target_phone_number="+15559990000", purpose="confirm refill status", structured_question="Is it ready, and what is the co-pay?")


def _bridge(replies: list[_FakeMessage]) -> tuple[CallReasoningBridge, _FakeLiveSession]:
    fake_session = _FakeLiveSession(replies)
    fake_client = MagicMock()
    fake_client.aio.live.connect.return_value = fake_session
    bridge = CallReasoningBridge(_settings(), _call_goal(), client_factory=lambda: fake_client)
    return bridge, fake_session


@pytest.mark.asyncio
async def test_connect_configures_text_only_response_and_both_call_tools() -> None:
    bridge, fake_session = _bridge([])
    await bridge.connect()

    fake_client = bridge._client_factory()  # already the same MagicMock via closure
    _, kwargs = fake_client.aio.live.connect.call_args
    config = kwargs["config"]
    assert config.response_modalities == ["TEXT"]
    names = [fd.name for tool in config.tools for fd in tool.function_declarations]
    assert names == ["press_dtmf", "report_call_outcome"]


@pytest.mark.asyncio
async def test_send_audio_forwards_pcm_at_the_gemini_live_input_rate() -> None:
    from app.ws.gemini_bridge import INPUT_MIME_TYPE

    bridge, fake_session = _bridge([])
    await bridge.connect()
    await bridge.send_audio(b"ivr-audio-chunk")

    assert fake_session.realtime_sent == [{"data": b"ivr-audio-chunk", "mime_type": INPUT_MIME_TYPE}]


@pytest.mark.asyncio
async def test_run_dispatches_press_dtmf_to_the_callback() -> None:
    from google.genai import types as genai_types

    fc = genai_types.FunctionCall(id="c1", name="press_dtmf", args={"digit": "1"})
    replies = [_FakeMessage(tool_call=genai_types.LiveServerToolCall(function_calls=[fc]))]
    bridge, fake_session = _bridge(replies)
    pressed: list[str] = []

    async def _on_dtmf(digit: str) -> None:
        pressed.append(digit)

    bridge.set_on_dtmf(_on_dtmf)
    await bridge.connect()

    await bridge.run()

    assert pressed == ["1"]
    assert len(fake_session.tool_responses_sent) == 1


@pytest.mark.asyncio
async def test_run_reports_outcome_and_stops() -> None:
    import json
    from google.genai import types as genai_types

    fc = genai_types.FunctionCall(
        id="c1", name="report_call_outcome",
        args={
            "status": "connected_resolved",
            "structured_data_json": json.dumps({"copay_cents": 1200}),
            "transcript_summary": "Refill confirmed, ready tomorrow.",
            "confidence": 0.9,
        },
    )
    # A second reply would prove run() stopped instead of consuming it.
    replies = [
        _FakeMessage(tool_call=genai_types.LiveServerToolCall(function_calls=[fc])),
        _FakeMessage(tool_call=genai_types.LiveServerToolCall(function_calls=[
            genai_types.FunctionCall(id="c2", name="press_dtmf", args={"digit": "9"})
        ])),
    ]
    bridge, fake_session = _bridge(replies)
    outcomes = []

    async def _on_outcome(outcome):
        outcomes.append(outcome)

    bridge.set_on_outcome(_on_outcome)
    await bridge.connect()
    await bridge.run()

    assert len(outcomes) == 1
    assert outcomes[0].status == "connected_resolved"
    assert outcomes[0].structured_data == {"copay_cents": 1200}
    assert len(fake_session.tool_responses_sent) == 1  # never processed the second reply


@pytest.mark.asyncio
async def test_run_reports_unresolved_when_the_turn_budget_is_exhausted() -> None:
    from google.genai import types as genai_types

    replies = [
        _FakeMessage(tool_call=genai_types.LiveServerToolCall(function_calls=[
            genai_types.FunctionCall(id=f"c{i}", name="press_dtmf", args={"digit": "1"})
        ]))
        for i in range(MAX_CALL_TURNS + 1)
    ]
    bridge, _ = _bridge(replies)
    outcomes = []

    async def _on_outcome(outcome):
        outcomes.append(outcome)

    bridge.set_on_outcome(_on_outcome)
    await bridge.connect()
    await bridge.run()

    assert len(outcomes) == 1
    assert outcomes[0].status == "connected_unresolved"
