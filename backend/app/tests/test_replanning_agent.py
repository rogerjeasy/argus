import pytest

from app.agents.grounding import GroundingAgent
from app.agents.replanning import MAX_REPLAN_ATTEMPTS, ReplanningAgent
from app.domains.stub import FakeGroundingSource, StubDomain


@pytest.mark.asyncio
async def test_replan_re_queries_the_grounding_source() -> None:
    source = FakeGroundingSource()
    source.set_answer("platform", "7")
    grounding = GroundingAgent(StubDomain(source))
    agent = ReplanningAgent(grounding)

    fact = await agent.replan(key="platform", attempt=1)

    assert fact.value == "7"


def test_should_escalate_only_past_max_attempts() -> None:
    grounding = GroundingAgent(StubDomain(FakeGroundingSource()))
    agent = ReplanningAgent(grounding)

    assert agent.should_escalate(MAX_REPLAN_ATTEMPTS) is False
    assert agent.should_escalate(MAX_REPLAN_ATTEMPTS + 1) is True
