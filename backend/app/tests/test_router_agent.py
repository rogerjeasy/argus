import pytest

from app.agents.router import DomainRouterAgent
from app.domains.stub import FakeGroundingSource, StubDomain
from app.models.agent_events import PerceivedGoal
from app.tests.doubles.fake_llm_runner import FakeLlmAgentRunner


class _KeywordDomain:
    """A plugin whose matches() is a literal keyword check, so a test can
    control exactly which plugins the pre-filter selects."""

    executors: dict = {}

    def __init__(self, domain_id: str, keyword: str) -> None:
        self.domain_id = domain_id
        self._keyword = keyword

    def matches(self, goal_text: str) -> bool:
        return self._keyword in goal_text.lower()


@pytest.mark.asyncio
async def test_route_returns_the_only_registered_domain_without_asking_the_llm_when_unambiguous() -> None:
    stub = StubDomain(FakeGroundingSource())
    runner = FakeLlmAgentRunner(next_response="should never be called")
    agent = DomainRouterAgent(runner, domains=[stub])

    domain_id = await agent.route(PerceivedGoal(session_id="s1", uid="u1", raw_text="get me to platform 4"))

    assert domain_id == "stub"
    assert runner.calls == []  # single-candidate fast path — no LLM call needed


@pytest.mark.asyncio
async def test_route_asks_the_llm_across_all_domains_when_no_keyword_matches() -> None:
    transit = _KeywordDomain("transit", "platform")
    admin = _KeywordDomain("personal_admin", "bill")
    runner = FakeLlmAgentRunner(next_response="transit")
    agent = DomainRouterAgent(runner, domains=[transit, admin])

    domain_id = await agent.route(
        PerceivedGoal(session_id="s1", uid="u1", raw_text="how do I get to the airport")
    )

    assert domain_id == "transit"
    assert len(runner.calls) == 1
    assert "transit, personal_admin" in runner.calls[0]["prompt"]  # the whole pool was offered


@pytest.mark.asyncio
async def test_route_raises_when_the_llm_says_none() -> None:
    transit = _KeywordDomain("transit", "platform")
    admin = _KeywordDomain("personal_admin", "bill")
    runner = FakeLlmAgentRunner(next_response="NONE")
    agent = DomainRouterAgent(runner, domains=[transit, admin])

    with pytest.raises(ValueError, match="no domain plugin matches"):
        await agent.route(PerceivedGoal(session_id="s1", uid="u1", raw_text="tell me a joke"))


@pytest.mark.asyncio
async def test_route_disambiguates_a_multi_keyword_match_with_the_llm() -> None:
    transit = _KeywordDomain("transit", "gate")
    wayfinding = _KeywordDomain("indoor_wayfinding", "gate")
    runner = FakeLlmAgentRunner(next_response="indoor_wayfinding")
    agent = DomainRouterAgent(runner, domains=[transit, wayfinding])

    domain_id = await agent.route(
        PerceivedGoal(session_id="s1", uid="u1", raw_text="take me to gate B12")
    )

    assert domain_id == "indoor_wayfinding"
