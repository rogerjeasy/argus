import pytest

from app.domains.stub import FakeGroundingSource, StubDomain


def test_stub_domain_matches_any_goal_text() -> None:
    domain = StubDomain(FakeGroundingSource())
    assert domain.matches("get me to platform 4") is True
    assert domain.domain_id == "stub"


@pytest.mark.asyncio
async def test_stub_domain_grounds_against_the_fake_source() -> None:
    source = FakeGroundingSource()
    source.set_answer("platform", "4")
    domain = StubDomain(source)

    from app.domains import GroundingRequest

    fact = await domain.ground(GroundingRequest(key="platform"))
    assert fact.value == "4"
    assert fact.source == "stub_feed"
    assert fact.confidence == 1.0


@pytest.mark.asyncio
async def test_fake_grounding_source_answer_is_mutable_mid_test() -> None:
    source = FakeGroundingSource()
    source.set_answer("platform", "4")
    domain = StubDomain(source)
    from app.domains import GroundingRequest

    first = await domain.ground(GroundingRequest(key="platform"))
    source.set_answer("platform", "7")
    second = await domain.ground(GroundingRequest(key="platform"))

    assert first.value == "4"
    assert second.value == "7"


@pytest.mark.asyncio
async def test_grounding_unknown_key_returns_zero_confidence() -> None:
    domain = StubDomain(FakeGroundingSource())
    from app.domains import GroundingRequest

    fact = await domain.ground(GroundingRequest(key="unknown"))
    assert fact.confidence == 0.0
