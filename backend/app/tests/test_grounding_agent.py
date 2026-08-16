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
