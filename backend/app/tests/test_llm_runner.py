import pytest

from google.adk.errors.already_exists_error import AlreadyExistsError

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

    async def get_session(self, *, app_name: str, user_id: str, session_id: str, config=None):
        return None

    async def create_session(self, *, app_name: str, user_id: str, session_id: str | None = None, state=None):
        self.created.append({"app_name": app_name, "user_id": user_id, "session_id": session_id})
        return _FakeSession()


class _FakeSessionServiceThatRejectsDuplicateCreate:
    """Mirrors the real `InMemorySessionService`: `get_session` returns
    `None` until a session has been created for that
    (app_name, user_id, session_id) key, and `create_session` raises the
    real ADK `AlreadyExistsError` if called again for a key that already
    exists — exactly as `InMemorySessionService._create_session_impl` does."""

    def __init__(self) -> None:
        self._sessions: dict[tuple[str, str, str], _FakeSession] = {}
        self.get_calls: list[dict] = []
        self.create_calls: list[dict] = []

    async def get_session(self, *, app_name: str, user_id: str, session_id: str, config=None):
        self.get_calls.append({"app_name": app_name, "user_id": user_id, "session_id": session_id})
        return self._sessions.get((app_name, user_id, session_id))

    async def create_session(self, *, app_name: str, user_id: str, session_id: str | None = None, state=None):
        self.create_calls.append({"app_name": app_name, "user_id": user_id, "session_id": session_id})
        key = (app_name, user_id, session_id)
        if key in self._sessions:
            raise AlreadyExistsError(f"Session with id {session_id} already exists.")
        session = _FakeSession()
        self._sessions[key] = session
        return session


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


@pytest.mark.asyncio
async def test_invoke_reuses_an_existing_session_across_calls_without_crashing() -> None:
    """A single Argus conversation session_id is reused across every
    reasoning-agent invoke() call for the lifetime of that session
    (Router, Planner, and especially Guidance, which is called once per
    spoken instruction). The second invoke() for the same session_id must
    not blow up on ADK's real `AlreadyExistsError`."""
    session_service = _FakeSessionServiceThatRejectsDuplicateCreate()
    runner = _FakeRunner([_FakeADKEvent("reply", is_final=True)])
    llm_runner = LlmAgentRunner(agent=object(), session_service=session_service, runner=runner, app_name="argus")

    first = await llm_runner.invoke(user_id="u1", session_id="s1", prompt="one")
    second = await llm_runner.invoke(user_id="u1", session_id="s1", prompt="two")

    assert first == "reply"
    assert second == "reply"
    assert len(session_service.create_calls) == 1
    assert len(session_service.get_calls) == 2
    assert runner.calls[1]["session_id"] == "s1"
