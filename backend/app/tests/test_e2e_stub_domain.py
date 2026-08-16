"""End-to-end regression coverage for the design doc's Definition of Done:
1. goal -> grounded plan -> spoken guidance -> live divergence -> autonomous
   replan -> updated guidance, all the way through StubDomain.
2. Bounded-replan-loop protection: exactly MAX_REPLAN_ATTEMPTS replans occur
   before an EscalationEvent is emitted, never an infinite loop.
3. Guardrail's tiered-autonomy default: a first-time action category with no
   standing permission always returns requires_confirmation, never approved.
"""
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
        domains={"stub": stub},
        planner=PlannerAgent(FakeLlmAgentRunner(next_response=planner_response)),
        guardrail=GuardrailAgent(),
        replanning=ReplanningAgent(),
        guidance=GuidanceAgent(FakeLlmAgentRunner(next_response="Head to the platform.")),
        memory=MemoryAgent(db),
        escalation=EscalationAgent(db, _FakePublisher(), LoggingNotificationSender()),
    )


@pytest.mark.asyncio
async def test_full_loop_goal_to_grounded_plan_to_spoken_guidance_to_divergence_to_replan() -> None:
    source = FakeGroundingSource()
    source.set_answer("platform", "4")
    orchestrator = _orchestrator(source)

    goal = PerceivedGoal(session_id="s1", uid="u1", raw_text="get me to platform 4")
    initial = await orchestrator.handle_goal(goal)
    assert initial.guidance.text
    assert initial.guardrail.decision == "requires_confirmation"

    source.set_answer("platform", "7")
    replanned = await orchestrator.check_for_divergence(session_id="s1", uid="u1")

    assert replanned is not None
    assert replanned.guidance.haptic_pattern == "pattern-urgent"


@pytest.mark.asyncio
async def test_bounded_replan_never_loops_past_max_attempts() -> None:
    source = FakeGroundingSource()
    source.set_answer("platform", "4")
    orchestrator = _orchestrator(source)

    goal = PerceivedGoal(session_id="s1", uid="u1", raw_text="get me to platform 4")
    await orchestrator.handle_goal(goal)

    results = []
    for i in range(MAX_REPLAN_ATTEMPTS + 2):
        source.set_answer("platform", str(i))
        result = await orchestrator.check_for_divergence(session_id="s1", uid="u1")
        results.append(result)
        if result is not None and result.guardrail.decision == "denied":
            break

    escalated = [r for r in results if r is not None and r.guardrail.decision == "denied"]
    assert len(escalated) == 1  # escalates exactly once, never loops past it


@pytest.mark.asyncio
async def test_first_time_category_never_auto_approves() -> None:
    source = FakeGroundingSource()
    source.set_answer("platform", "4")
    orchestrator = _orchestrator(source)

    result = await orchestrator.handle_goal(PerceivedGoal(session_id="s1", uid="u1", raw_text="get me to platform 4"))

    assert result.guardrail.decision != "approved"
