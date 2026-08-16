import pytest

from app.agents.router import DomainRouterAgent
from app.domains.stub import FakeGroundingSource, StubDomain
from app.models.agent_events import PerceivedGoal
from app.tests.doubles.fake_llm_runner import FakeLlmAgentRunner


@pytest.mark.asyncio
async def test_route_returns_the_only_registered_domain_without_asking_the_llm_when_unambiguous() -> None:
    stub = StubDomain(FakeGroundingSource())
    runner = FakeLlmAgentRunner(next_response="should never be called")
    agent = DomainRouterAgent(runner, domains=[stub])

    domain_id = await agent.route(PerceivedGoal(session_id="s1", uid="u1", raw_text="get me to platform 4"))

    assert domain_id == "stub"
    assert runner.calls == []  # single-candidate fast path — no LLM call needed


@pytest.mark.asyncio
async def test_route_raises_when_no_domain_matches() -> None:
    class NeverMatches:
        domain_id = "never"
        executors: dict = {}

        def matches(self, goal_text: str) -> bool:
            return False

    runner = FakeLlmAgentRunner()
    agent = DomainRouterAgent(runner, domains=[NeverMatches()])

    with pytest.raises(ValueError, match="no domain plugin matches"):
        await agent.route(PerceivedGoal(session_id="s1", uid="u1", raw_text="anything"))
