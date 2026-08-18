import json

import pytest

from app.agents.calibration import CalibrationAgent
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


def _orchestrator(db) -> TaskOrchestrator:
    source = FakeGroundingSource()
    source.set_answer("platform", "4")
    stub = StubDomain(source)
    planner_response = json.dumps({
        "description": "Refill your prescription", "action_type": "guidance",
        "requires_confirmation": False, "category": "pharmacy_refill", "provider": "cvs-main-st",
    })
    return TaskOrchestrator(
        perception=PerceptionAgent(),
        router=DomainRouterAgent(FakeLlmAgentRunner(), domains=[stub]),
        grounding_agents={"stub": GroundingAgent(stub)},
        domains={"stub": stub},
        planner=PlannerAgent(FakeLlmAgentRunner(next_response=planner_response)),
        guardrail=GuardrailAgent(),
        replanning=ReplanningAgent(),
        guidance=GuidanceAgent(FakeLlmAgentRunner(next_response="Refilling now.")),
        memory=MemoryAgent(db),
        escalation=EscalationAgent(db, _FakePublisher(), LoggingNotificationSender()),
    )


@pytest.mark.asyncio
async def test_full_pipeline_accept_makes_the_next_confirmation_automatic() -> None:
    db = FakeFirestoreClient()
    memory = MemoryAgent(db)

    # 15 prior sessions, each ending in an explicit "yes" to the same
    # category/provider — the fixture history DoD #2 asks for.
    for _ in range(15):
        await memory.record_confirmation_outcome(
            "u1", category="pharmacy_refill", provider="cvs-main-st", decision="approved"
        )

    calibration = CalibrationAgent(memory)
    created = await calibration.run_for_all_users([("u1", "pharmacy_refill", "cvs-main-st")])
    assert created == 1

    orchestrator = _orchestrator(db)
    offer = await orchestrator.check_for_pending_calibration_proposal("s1", "u1")
    assert offer is not None
    assert offer.guardrail.decision == "requires_confirmation"

    await orchestrator.resolve_confirmation("s1", "u1", accepted=True)

    # The 16th "confirmation" never happens — Guardrail approves outright now.
    goal = PerceivedGoal(session_id="s2", uid="u1", raw_text="refill my prescription")
    result = await orchestrator.handle_goal(goal)
    assert result.guardrail.decision == "approved"


@pytest.mark.asyncio
async def test_full_pipeline_decline_never_touches_standing_permissions() -> None:
    db = FakeFirestoreClient()
    memory = MemoryAgent(db)
    for _ in range(15):
        await memory.record_confirmation_outcome(
            "u1", category="pharmacy_refill", provider="cvs-main-st", decision="approved"
        )
    calibration = CalibrationAgent(memory)
    await calibration.run_for_all_users([("u1", "pharmacy_refill", "cvs-main-st")])

    orchestrator = _orchestrator(db)
    await orchestrator.check_for_pending_calibration_proposal("s1", "u1")
    await orchestrator.resolve_confirmation("s1", "u1", accepted=False)

    assert await memory.get_standing_permissions("u1") == []

    # The 16th request still asks for confirmation — nothing was calibrated.
    goal = PerceivedGoal(session_id="s2", uid="u1", raw_text="refill my prescription")
    result = await orchestrator.handle_goal(goal)
    assert result.guardrail.decision == "requires_confirmation"
