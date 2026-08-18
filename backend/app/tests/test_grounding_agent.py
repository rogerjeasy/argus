import pytest

from app.agents.grounding import GroundingAgent
from app.domains.stub import FakeGroundingSource, StubDomain


@pytest.mark.asyncio
async def test_ground_delegates_to_the_domain_plugin() -> None:
    source = FakeGroundingSource()
    source.set_answer("platform", "4")
    agent = GroundingAgent(StubDomain(source))

    fact = await agent.ground("platform")

    assert fact.value == "4"


def test_check_divergence_returns_none_when_facts_agree() -> None:
    from datetime import datetime, timezone
    from app.models.agent_events import GroundedFact

    agent = GroundingAgent(StubDomain(FakeGroundingSource()))
    fact = GroundedFact(key="platform", value="4", source="stub_feed", confidence=1.0, as_of=datetime.now(timezone.utc))

    result = agent.check_divergence(plan_step_id="step-1", expected=fact, new_fact=fact)

    assert result is None


def test_check_divergence_returns_a_signal_when_values_differ() -> None:
    from datetime import datetime, timezone
    from app.models.agent_events import GroundedFact

    agent = GroundingAgent(StubDomain(FakeGroundingSource()))
    expected = GroundedFact(key="platform", value="4", source="stub_feed", confidence=1.0, as_of=datetime.now(timezone.utc))
    observed = GroundedFact(key="platform", value="7", source="stub_feed", confidence=1.0, as_of=datetime.now(timezone.utc))

    signal = agent.check_divergence(plan_step_id="step-1", expected=expected, new_fact=observed)

    assert signal is not None
    assert signal.expected == "4"
    assert signal.observed == "7"
    assert signal.plan_step_id == "step-1"


@pytest.mark.asyncio
async def test_ground_forwards_raw_goal_text_to_the_domain() -> None:
    class _RecordingDomain:
        domain_id = "recording"
        executors: dict = {}

        def __init__(self) -> None:
            self.received: str | None = None

        def matches(self, goal_text: str) -> bool:
            return True

        async def ground(self, request):
            self.received = request.raw_goal_text
            from datetime import datetime, timezone
            from app.models.agent_events import GroundedFact
            return GroundedFact(key=request.key, value="x", source="test", confidence=1.0, as_of=datetime.now(timezone.utc))

    domain = _RecordingDomain()
    agent = GroundingAgent(domain)

    await agent.ground("platform", "get me to Zürich HB")

    assert domain.received == "get me to Zürich HB"


def test_scene_signal_suggests_divergence_when_a_different_platform_digit_is_read() -> None:
    from datetime import datetime, timezone
    from app.models.agent_events import GroundedFact, SceneSignal

    agent = GroundingAgent(StubDomain(FakeGroundingSource()))
    expected = GroundedFact(key="platform", value="4", source="stub_feed", confidence=1.0, as_of=datetime.now(timezone.utc))
    signal = SceneSignal(session_id="s1", kind="signage_text", text="Platform 7", confidence=0.9)

    assert agent.scene_signal_suggests_divergence(expected=expected, signal=signal) is True


def test_scene_signal_does_not_suggest_divergence_when_it_confirms_the_plan() -> None:
    from datetime import datetime, timezone
    from app.models.agent_events import GroundedFact, SceneSignal

    agent = GroundingAgent(StubDomain(FakeGroundingSource()))
    expected = GroundedFact(key="platform", value="4", source="stub_feed", confidence=1.0, as_of=datetime.now(timezone.utc))
    signal = SceneSignal(session_id="s1", kind="signage_text", text="Platform 4", confidence=0.9)

    assert agent.scene_signal_suggests_divergence(expected=expected, signal=signal) is False


def test_scene_signal_below_confidence_floor_never_suggests_divergence() -> None:
    # Red-team case (design doc §9): a blurry/low-light camera read must
    # never act, even if it superficially contradicts the plan.
    from datetime import datetime, timezone
    from app.models.agent_events import GroundedFact, SceneSignal

    agent = GroundingAgent(StubDomain(FakeGroundingSource()))
    expected = GroundedFact(key="platform", value="4", source="stub_feed", confidence=1.0, as_of=datetime.now(timezone.utc))
    signal = SceneSignal(session_id="s1", kind="signage_text", text="Platform 7", confidence=0.2)

    assert agent.scene_signal_suggests_divergence(expected=expected, signal=signal) is False


def test_scene_signal_with_no_digit_never_suggests_divergence() -> None:
    # Red-team case (design doc §9): a stale advertising sign in frame must
    # not be treated as authoritative just because it's readable text.
    from datetime import datetime, timezone
    from app.models.agent_events import GroundedFact, SceneSignal

    agent = GroundingAgent(StubDomain(FakeGroundingSource()))
    expected = GroundedFact(key="platform", value="4", source="stub_feed", confidence=1.0, as_of=datetime.now(timezone.utc))
    signal = SceneSignal(session_id="s1", kind="signage_text", text="Drink Coffee!", confidence=0.95)

    assert agent.scene_signal_suggests_divergence(expected=expected, signal=signal) is False


@pytest.mark.asyncio
async def test_ground_forwards_uid_to_the_domain() -> None:
    class _RecordingDomain:
        domain_id = "recording"
        executors: dict = {}

        def __init__(self) -> None:
            self.received_uid: str | None = None

        def matches(self, goal_text: str) -> bool:
            return True

        async def ground(self, request):
            self.received_uid = request.uid
            from datetime import datetime, timezone
            from app.models.agent_events import GroundedFact
            return GroundedFact(key=request.key, value="x", source="test", confidence=1.0, as_of=datetime.now(timezone.utc))

    domain = _RecordingDomain()
    agent = GroundingAgent(domain)

    await agent.ground("profile", uid="user-42")

    assert domain.received_uid == "user-42"


@pytest.mark.asyncio
async def test_ground_forwards_scene_signal_text_to_the_domain() -> None:
    class _RecordingDomain:
        domain_id = "recording"
        executors: dict = {}

        def __init__(self) -> None:
            self.received_scene_signal_text: str | None = None

        def matches(self, goal_text: str) -> bool:
            return True

        async def ground(self, request):
            self.received_scene_signal_text = request.scene_signal_text
            from datetime import datetime, timezone
            from app.models.agent_events import GroundedFact
            return GroundedFact(key=request.key, value="x", source="test", confidence=1.0, as_of=datetime.now(timezone.utc))

    domain = _RecordingDomain()
    agent = GroundingAgent(domain)

    await agent.ground("directory_entry", scene_signal_text="Room 204")

    assert domain.received_scene_signal_text == "Room 204"


@pytest.mark.asyncio
async def test_ground_defaults_scene_signal_text_to_empty_string() -> None:
    source = FakeGroundingSource()
    source.set_answer("platform", "4")
    agent = GroundingAgent(StubDomain(source))

    # Existing callers (e.g. TransitDomain's polling-triggered re-ground)
    # never pass scene_signal_text — this must keep working unmodified.
    fact = await agent.ground("platform")

    assert fact.value == "4"


def test_scene_signal_suggests_divergence_falls_back_to_digit_pattern_when_domain_has_no_hook() -> None:
    # StubDomain defines no extract_signage_candidate — must behave exactly
    # as it does today (this duplicates test_scene_signal_suggests_divergence_
    # when_a_different_platform_digit_is_read above, as an explicit
    # regression pin on the fallback path specifically).
    from datetime import datetime, timezone
    from app.models.agent_events import GroundedFact, SceneSignal

    agent = GroundingAgent(StubDomain(FakeGroundingSource()))
    expected = GroundedFact(key="platform", value="4", source="stub_feed", confidence=1.0, as_of=datetime.now(timezone.utc))
    signal = SceneSignal(session_id="s1", kind="signage_text", text="Platform 7", confidence=0.9)

    assert agent.scene_signal_suggests_divergence(expected=expected, signal=signal) is True


@pytest.mark.asyncio
async def test_scene_signal_suggests_divergence_uses_the_domain_hook_when_present() -> None:
    from datetime import datetime, timezone
    from app.models.agent_events import GroundedFact, SceneSignal

    class _HookDomain:
        domain_id = "hooked"
        executors: dict = {}

        def matches(self, goal_text: str) -> bool:
            return True

        async def ground(self, request):
            raise NotImplementedError

        def extract_signage_candidate(self, text: str) -> str | None:
            return text.strip() or None

    agent = GroundingAgent(_HookDomain())
    expected = GroundedFact(key="directory_entry", value="unknown", source="signage_only", confidence=0.0, as_of=datetime.now(timezone.utc))
    signal = SceneSignal(session_id="s1", kind="signage_text", text="Breakfast Room", confidence=0.9)

    # No digit anywhere in "Breakfast Room" — the digit-pattern fallback
    # would return False here; the hook must be what actually decides.
    assert agent.scene_signal_suggests_divergence(expected=expected, signal=signal) is True
