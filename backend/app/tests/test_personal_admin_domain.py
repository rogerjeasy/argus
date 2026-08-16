import json

import pytest

from app.domains import GroundingRequest
from app.domains.personal_admin.domain import PersonalAdminDomain
from app.models.agent_events import SceneSignal
from app.tests.doubles.fake_firestore import FakeFirestoreClient
from app.tests.doubles.fake_llm_runner import FakeLlmAgentRunner


def _domain(triage_response: str = "") -> tuple[PersonalAdminDomain, FakeLlmAgentRunner]:
    from app.agents.memory import MemoryAgent

    runner = FakeLlmAgentRunner(next_response=triage_response)
    memory = MemoryAgent(FakeFirestoreClient(), kms=None)
    return PersonalAdminDomain(runner, memory), runner


def test_matches_recognizes_personal_admin_phrasing() -> None:
    domain, _ = _domain()
    assert domain.matches("deal with this piece of mail") is True
    assert domain.matches("call the pharmacy about my refill") is True
    assert domain.matches("what platform is my train on") is False


@pytest.mark.asyncio
async def test_triage_parses_the_llm_response_into_a_triage_result() -> None:
    response = json.dumps({"category": "bill", "urgency": "high", "subflow": "call", "confidence": 0.85})
    domain, runner = _domain(triage_response=response)
    signal = SceneSignal(session_id="s1", kind="signage_text", text="Example Pharmacy — Refill Notice", confidence=0.9)

    result = await domain.triage(signal)

    assert result.category == "bill"
    assert result.subflow == "call"
    assert runner.calls[0]["prompt"].find("Example Pharmacy") != -1


@pytest.mark.asyncio
async def test_triage_raises_on_unparseable_llm_response() -> None:
    domain, _ = _domain(triage_response="not json")
    signal = SceneSignal(session_id="s1", kind="signage_text", text="some text", confidence=0.9)

    with pytest.raises(ValueError):
        await domain.triage(signal)


@pytest.mark.asyncio
async def test_ground_returns_known_provider_from_the_profile() -> None:
    from app.agents.memory import PersonalAdminProfile, ProviderContact

    domain, _ = _domain()
    profile = PersonalAdminProfile(
        known_providers=[ProviderContact(name="Example Pharmacy", phone_number="+15551234567", category="pharmacy_refill_under_20")]
    )
    await domain._memory.update_profile("user-1", profile)

    fact = await domain.ground(GroundingRequest(key="pharmacy_refill_under_20", uid="user-1"))

    assert fact.value == "+15551234567"
    assert fact.source == "user_profile"
    assert fact.confidence == 1.0


@pytest.mark.asyncio
async def test_ground_returns_low_confidence_when_no_matching_provider_known() -> None:
    domain, _ = _domain()

    fact = await domain.ground(GroundingRequest(key="pharmacy_refill_under_20", uid="user-with-no-profile"))

    assert fact.confidence < 0.5
