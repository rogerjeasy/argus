import json
from datetime import datetime, timezone

import pytest

from app.agents.planner import PlannerAgent
from app.models.agent_events import GroundedFact, PerceivedGoal
from app.tests.doubles.fake_llm_runner import FakeLlmAgentRunner


@pytest.mark.asyncio
async def test_plan_parses_the_llm_response_into_a_plan_step() -> None:
    runner = FakeLlmAgentRunner(
        next_response=json.dumps(
            {
                "description": "Head to platform 4",
                "action_type": "guidance",
                "requires_confirmation": False,
                "category": "stub-guidance",
            }
        )
    )
    agent = PlannerAgent(runner)
    goal = PerceivedGoal(session_id="s1", uid="u1", raw_text="get me to platform 4")
    facts = [GroundedFact(key="platform", value="4", source="stub_feed", confidence=1.0, as_of=datetime.now(timezone.utc))]

    step = await agent.plan(goal, facts, domain_id="stub")

    assert step.description == "Head to platform 4"
    assert step.action_type == "guidance"
    assert step.payload["category"] == "stub-guidance"
    assert "provider" not in step.payload  # not present in the scripted response, must not be invented
    assert step.domain_id == "stub"
    assert step.step_id  # non-empty, generated


@pytest.mark.asyncio
async def test_plan_carries_provider_through_when_the_llm_response_includes_it() -> None:
    """Real gap this plan's own research found while executing Phase 4b
    Task 2: PlannerAgent.plan() only ever set payload={"category": ...},
    silently dropping any "provider" the LLM's JSON response might carry —
    which meant GuardrailAgent.evaluate()'s own `step.payload.get("provider")`
    read was unreachable dead code for any flow that isn't Personal Admin's
    document-triage build_executor_payload override. Fixed here, generally,
    not worked around in just one call site."""
    runner = FakeLlmAgentRunner(
        next_response=json.dumps(
            {
                "description": "Refill your prescription",
                "action_type": "guidance",
                "requires_confirmation": False,
                "category": "pharmacy_refill",
                "provider": "cvs-main-st",
            }
        )
    )
    agent = PlannerAgent(runner)
    goal = PerceivedGoal(session_id="s1", uid="u1", raw_text="refill my prescription")

    step = await agent.plan(goal, [], domain_id="stub")

    assert step.payload["provider"] == "cvs-main-st"


@pytest.mark.asyncio
async def test_plan_raises_on_unparseable_response() -> None:
    runner = FakeLlmAgentRunner(next_response="not json")
    agent = PlannerAgent(runner)
    goal = PerceivedGoal(session_id="s1", uid="u1", raw_text="get me to platform 4")

    with pytest.raises(ValueError, match="could not parse planner response"):
        await agent.plan(goal, [], domain_id="stub")
