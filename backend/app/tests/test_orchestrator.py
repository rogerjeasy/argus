import pytest

from app.agents.escalation import EscalationAgent, LoggingNotificationSender
from app.agents.grounding import GroundingAgent
from app.agents.guardrail import GuardrailAgent
from app.agents.guidance import GuidanceAgent
from app.agents.memory import MemoryAgent
from app.agents.orchestrator import TaskOrchestrator
from app.agents.perception import PerceptionAgent
from app.agents.planner import PlannerAgent
from app.agents.replanning import MAX_REPLAN_ATTEMPTS, ReplanningAgent
from app.agents.router import DomainRouterAgent
from app.domains.stub import FakeGroundingSource, StubDomain
from app.models.agent_events import PerceivedGoal
from app.tests.doubles.fake_firestore import FakeFirestoreClient
from app.tests.doubles.fake_llm_runner import FakeLlmAgentRunner


class _FakePublisher:
    def publish(self, topic_path, data):
        class _F:
            def result(self):
                return "id"
        return _F()

    def topic_path(self, project, topic):
        return f"projects/{project}/topics/{topic}"


def _build_orchestrator(source: FakeGroundingSource, *, planner_response: str) -> TaskOrchestrator:
    stub = StubDomain(source)
    router_runner = FakeLlmAgentRunner()  # single candidate — never actually called
    planner_runner = FakeLlmAgentRunner(next_response=planner_response)
    guidance_runner = FakeLlmAgentRunner(next_response="Head to the platform.")

    grounding = GroundingAgent(stub)
    db = FakeFirestoreClient()
    return TaskOrchestrator(
        perception=PerceptionAgent(),
        router=DomainRouterAgent(router_runner, domains=[stub]),
        grounding_agents={"stub": grounding},
        planner=PlannerAgent(planner_runner),
        guardrail=GuardrailAgent(),
        replanning=ReplanningAgent(),
        guidance=GuidanceAgent(guidance_runner),
        memory=MemoryAgent(db),
        escalation=EscalationAgent(db, _FakePublisher(), LoggingNotificationSender()),
    )


def _planner_json(category: str = "stub-guidance") -> str:
    import json
    return json.dumps({
        "description": "Head to platform 4",
        "action_type": "guidance",
        "requires_confirmation": False,
        "category": category,
    })


@pytest.mark.asyncio
async def test_handle_goal_returns_guidance_gated_by_guardrail() -> None:
    source = FakeGroundingSource()
    source.set_answer("platform", "4")
    orchestrator = _build_orchestrator(source, planner_response=_planner_json())

    goal = PerceivedGoal(session_id="s1", uid="u1", raw_text="get me to platform 4")
    result = await orchestrator.handle_goal(goal)

    assert result.guidance.text == "Head to the platform."
    # No standing permission seeded — first-time category always requires confirmation.
    assert result.guardrail.decision == "requires_confirmation"


@pytest.mark.asyncio
async def test_divergence_triggers_autonomous_replan_with_updated_guidance() -> None:
    source = FakeGroundingSource()
    source.set_answer("platform", "4")
    orchestrator = _build_orchestrator(source, planner_response=_planner_json())

    goal = PerceivedGoal(session_id="s1", uid="u1", raw_text="get me to platform 4")
    await orchestrator.handle_goal(goal)

    # Reality changes mid-task.
    source.set_answer("platform", "7")

    result = await orchestrator.check_for_divergence(session_id="s1", uid="u1")

    assert result is not None
    assert result.guidance.text == "Head to the platform."  # re-shaped from the updated fact


@pytest.mark.asyncio
async def test_check_for_divergence_returns_none_when_nothing_changed() -> None:
    source = FakeGroundingSource()
    source.set_answer("platform", "4")
    orchestrator = _build_orchestrator(source, planner_response=_planner_json())

    goal = PerceivedGoal(session_id="s1", uid="u1", raw_text="get me to platform 4")
    await orchestrator.handle_goal(goal)

    result = await orchestrator.check_for_divergence(session_id="s1", uid="u1")

    assert result is None


@pytest.mark.asyncio
async def test_bounded_replan_escalates_instead_of_looping_forever() -> None:
    source = FakeGroundingSource()
    source.set_answer("platform", "4")
    orchestrator = _build_orchestrator(source, planner_response=_planner_json())

    goal = PerceivedGoal(session_id="s1", uid="u1", raw_text="get me to platform 4")
    await orchestrator.handle_goal(goal)

    # Every replan attempt gets contradicted again — never converges.
    for i in range(MAX_REPLAN_ATTEMPTS + 1):
        source.set_answer("platform", str(i))
        result = await orchestrator.check_for_divergence(session_id="s1", uid="u1")

    assert result is not None
    assert result.guardrail.decision == "denied"
    assert "escalat" in result.guidance.text.lower()
    assert result.guidance.earcon == "earcon-escalation"


@pytest.mark.asyncio
async def test_handle_scene_signal_triggers_replan_when_feed_confirms_the_camera() -> None:
    from app.models.agent_events import SceneSignal

    source = FakeGroundingSource()
    source.set_answer("platform", "4")
    orchestrator = _build_orchestrator(source, planner_response=_planner_json())

    goal = PerceivedGoal(session_id="s1", uid="u1", raw_text="get me to platform 4")
    await orchestrator.handle_goal(goal)

    # The camera and the feed now agree the plan is stale.
    source.set_answer("platform", "7")
    signal = SceneSignal(session_id="s1", kind="signage_text", text="Platform 7", confidence=0.9)

    result = await orchestrator.handle_scene_signal(signal)

    assert result is not None
    assert result.guidance.haptic_pattern == "pattern-urgent"


@pytest.mark.asyncio
async def test_handle_scene_signal_does_nothing_when_the_feed_disagrees_with_the_camera() -> None:
    from app.models.agent_events import SceneSignal

    source = FakeGroundingSource()
    source.set_answer("platform", "4")
    orchestrator = _build_orchestrator(source, planner_response=_planner_json())

    goal = PerceivedGoal(session_id="s1", uid="u1", raw_text="get me to platform 4")
    await orchestrator.handle_goal(goal)

    # Camera claims platform 7, but the real feed (tie-breaker) still says 4
    # — a noisy/wrong camera read must not override it.
    signal = SceneSignal(session_id="s1", kind="signage_text", text="Platform 7", confidence=0.9)

    result = await orchestrator.handle_scene_signal(signal)

    assert result is None


@pytest.mark.asyncio
async def test_handle_scene_signal_ignores_a_low_confidence_signal_without_ever_regrounding() -> None:
    from app.models.agent_events import SceneSignal

    source = FakeGroundingSource()
    source.set_answer("platform", "4")
    orchestrator = _build_orchestrator(source, planner_response=_planner_json())

    goal = PerceivedGoal(session_id="s1", uid="u1", raw_text="get me to platform 4")
    await orchestrator.handle_goal(goal)

    signal = SceneSignal(session_id="s1", kind="signage_text", text="Platform 7", confidence=0.1)

    result = await orchestrator.handle_scene_signal(signal)

    assert result is None


@pytest.mark.asyncio
async def test_handle_scene_signal_for_an_unknown_session_returns_none() -> None:
    from app.models.agent_events import SceneSignal

    orchestrator = _build_orchestrator(FakeGroundingSource(), planner_response=_planner_json())
    signal = SceneSignal(session_id="never-started", kind="signage_text", text="Platform 7", confidence=0.9)

    assert await orchestrator.handle_scene_signal(signal) is None
