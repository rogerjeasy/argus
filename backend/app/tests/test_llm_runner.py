import pytest

from app.agents.llm_runner import LlmAgentRunner


class _FakeADKEvent:
    def __init__(self, text: str, *, is_final: bool) -> None:
        self._text = text
        self._is_final = is_final
        self.content = _FakeContent(text)

    def is_final_response(self) -> bool:
        return self._is_final


class _FakeContent:
    def __init__(self, text: str) -> None:
        self.parts = [_FakePart(text)]


class _FakePart:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeSession:
    pass


class _FakeSessionService:
    def __init__(self) -> None:
        self.created: list[dict] = []

    async def create_session(self, *, app_name: str, user_id: str, session_id: str | None = None, state=None):
        self.created.append({"app_name": app_name, "user_id": user_id, "session_id": session_id})
        return _FakeSession()


class _FakeRunner:
    def __init__(self, events: list[_FakeADKEvent]) -> None:
        self._events = events
        self.calls: list[dict] = []

    async def run_async(self, *, user_id: str, session_id: str, new_message):
        self.calls.append({"user_id": user_id, "session_id": session_id, "new_message": new_message})
        for event in self._events:
            yield event


@pytest.mark.asyncio
async def test_invoke_returns_the_final_response_text() -> None:
    session_service = _FakeSessionService()
    runner = _FakeRunner([
        _FakeADKEvent("thinking...", is_final=False),
        _FakeADKEvent('{"domain_id": "stub"}', is_final=True),
    ])
    llm_runner = LlmAgentRunner(agent=object(), session_service=session_service, runner=runner, app_name="argus")

    result = await llm_runner.invoke(user_id="u1", session_id="s1", prompt="classify this goal")

    assert result == '{"domain_id": "stub"}'
    assert session_service.created == [{"app_name": "argus", "user_id": "u1", "session_id": "s1"}]
    assert runner.calls[0]["user_id"] == "u1"


@pytest.mark.asyncio
async def test_invoke_returns_empty_string_when_no_final_event_has_content() -> None:
    session_service = _FakeSessionService()
    runner = _FakeRunner([_FakeADKEvent("partial", is_final=False)])
    llm_runner = LlmAgentRunner(agent=object(), session_service=session_service, runner=runner, app_name="argus")

    result = await llm_runner.invoke(user_id="u1", session_id="s1", prompt="x")

    assert result == ""
