import pytest

from app.agents.guidance import GuidanceAgent
from app.models.agent_events import FramingAssessment, PlanStep
from app.tests.doubles.fake_llm_runner import FakeLlmAgentRunner


def _step() -> PlanStep:
    return PlanStep(
        step_id="step-1", domain_id="stub", description="Head to platform 4",
        action_type="guidance", requires_confirmation=False, payload={"category": "stub-guidance"},
    )


@pytest.mark.asyncio
async def test_shape_produces_concise_text_and_a_valid_haptic_earcon_pair() -> None:
    runner = FakeLlmAgentRunner(next_response="Head to platform 4, it's just ahead.")
    agent = GuidanceAgent(runner)

    output = await agent.shape("s1", "u1", _step())

    assert output.text == "Head to platform 4, it's just ahead."
    assert output.haptic_pattern == "pattern-forward"
    assert output.earcon == "earcon-plan-updated"


@pytest.mark.asyncio
async def test_shape_uses_urgent_vocabulary_when_flagged() -> None:
    runner = FakeLlmAgentRunner(next_response="Stop — platform changed.")
    agent = GuidanceAgent(runner)

    output = await agent.shape("s1", "u1", _step(), urgent=True)

    assert output.haptic_pattern == "pattern-urgent"
    assert output.earcon == "earcon-plan-updated"


def test_shape_framing_maps_position_to_a_fixed_spoken_vocabulary() -> None:
    agent = GuidanceAgent(runner=None)  # deterministic path — never calls the LLM runner
    assessment = FramingAssessment(session_id="s1", text_detected=True, position="right")

    output = agent.shape_framing("s1", assessment)

    assert output.text == "Move slightly right."
    assert output.earcon is None


def test_shape_framing_reports_low_confidence_earcon_when_no_text_detected() -> None:
    agent = GuidanceAgent(runner=None)
    assessment = FramingAssessment(session_id="s1", text_detected=False, position="none")

    output = agent.shape_framing("s1", assessment)

    assert output.earcon == "earcon-low-confidence"
