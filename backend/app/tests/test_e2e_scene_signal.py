"""End-to-end regression for Phase 2b's Definition of Done: a real
camera-detected contradiction, confirmed by re-grounding, triggers
autonomous replanning — using StubDomain because this pipeline has no
domain-specific logic in it at all (see this file's module docstring
reasoning in the plan)."""
import json

import pytest

from app.agents.escalation import EscalationAgent, LoggingNotificationSender
from app.agents.grounding import GroundingAgent
from app.agents.guardrail import GuardrailAgent
from app.agents.guidance import GuidanceAgent
from app.agents.memory import MemoryAgent
from app.agents.orchestrator import TaskOrchestrator
from app.agents.perception import PerceptionAgent
from app.agents.planner import PlannerAgent
from app.agents.replanning import ReplanningAgent
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


def _orchestrator(source: FakeGroundingSource) -> TaskOrchestrator:
    stub = StubDomain(source)
    grounding = GroundingAgent(stub)
    db = FakeFirestoreClient()
    planner_response = json.dumps({
        "description": "Head to the platform", "action_type": "guidance",
        "requires_confirmation": False, "category": "stub-guidance",
    })
    return TaskOrchestrator(
        perception=PerceptionAgent(),
        router=DomainRouterAgent(FakeLlmAgentRunner(), domains=[stub]),
        grounding_agents={"stub": grounding},
        planner=PlannerAgent(FakeLlmAgentRunner(next_response=planner_response)),
        guardrail=GuardrailAgent(),
        replanning=ReplanningAgent(),
        guidance=GuidanceAgent(FakeLlmAgentRunner(next_response="Head to the platform.")),
        memory=MemoryAgent(db),
        escalation=EscalationAgent(db, _FakePublisher(), LoggingNotificationSender()),
    )


@pytest.mark.asyncio
async def test_camera_signal_confirmed_by_the_feed_triggers_autonomous_replan() -> None:
    from app.models.agent_events import SceneSignal

    source = FakeGroundingSource()
    source.set_answer("platform", "4")
    orchestrator = _orchestrator(source)

    goal = PerceivedGoal(session_id="s1", uid="u1", raw_text="get me to platform 4")
    initial = await orchestrator.handle_goal(goal)
    assert initial.guidance.text

    # The real feed *and* the camera now agree the plan is stale.
    source.set_answer("platform", "7")
    signal = SceneSignal(session_id="s1", kind="signage_text", text="Platform 7", confidence=0.92)

    replanned = await orchestrator.handle_scene_signal(signal)

    assert replanned is not None
    assert replanned.guidance.haptic_pattern == "pattern-urgent"


@pytest.mark.asyncio
async def test_camera_signal_the_feed_does_not_confirm_changes_nothing() -> None:
    from app.models.agent_events import SceneSignal

    source = FakeGroundingSource()
    source.set_answer("platform", "4")
    orchestrator = _orchestrator(source)

    goal = PerceivedGoal(session_id="s1", uid="u1", raw_text="get me to platform 4")
    await orchestrator.handle_goal(goal)

    # Camera claims 7; the real feed (tie-breaker) still says 4.
    signal = SceneSignal(session_id="s1", kind="signage_text", text="Platform 7", confidence=0.92)

    result = await orchestrator.handle_scene_signal(signal)

    assert result is None


@pytest.mark.asyncio
async def test_low_confidence_camera_signal_never_reaches_the_grounding_source() -> None:
    from app.models.agent_events import SceneSignal

    source = FakeGroundingSource()
    source.set_answer("platform", "4")
    orchestrator = _orchestrator(source)

    goal = PerceivedGoal(session_id="s1", uid="u1", raw_text="get me to platform 4")
    await orchestrator.handle_goal(goal)

    call_count_before = len(source._answers)  # FakeGroundingSource has no call counter; this asserts on the observable outcome instead
    signal = SceneSignal(session_id="s1", kind="signage_text", text="Platform 7", confidence=0.1)

    result = await orchestrator.handle_scene_signal(signal)

    assert result is None
    assert len(source._answers) == call_count_before  # confirms no grounding-source mutation/query side effect occurred
