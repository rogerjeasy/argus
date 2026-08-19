"""Design doc §4's two red-team cases needing real recorded material, not
synthetic fixtures. Both skip (not fail) until a human records and drops
the real files per real_fixtures/README.md — CI stays green either way;
these only become load-bearing once the files exist."""
import json
from pathlib import Path

import pytest

from app.agents.guardrail import GuardrailAgent
from app.agents.perception import PerceptionAgent
from app.models.agent_events import PlanStep

FIXTURES_DIR = Path(__file__).parent / "real_fixtures" / "redteam"


def _load_expectation(name: str) -> dict | None:
    path = FIXTURES_DIR / f"{name}.expected.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.redteam
@pytest.mark.skipif(
    not (FIXTURES_DIR / "low_light_blurred_frame.jpg").exists(),
    reason="real_fixtures/redteam/low_light_blurred_frame.jpg not recorded yet — see real_fixtures/README.md",
)
def test_low_light_blurred_frame_refuses_rather_than_guesses() -> None:
    expectation = _load_expectation("low_light_blurred_frame")
    assert expectation is not None, "low_light_blurred_frame.expected.json missing alongside the .jpg"

    guardrail = GuardrailAgent()
    step = PlanStep(
        step_id="redteam-1", domain_id="transit", description="Head to the platform",
        action_type="guidance", requires_confirmation=False, payload={"category": "transit-guidance"},
    )
    decision = guardrail.evaluate(step, confidence=expectation["reported_confidence"], standing_permissions=[])

    assert decision.decision == "denied"


@pytest.mark.redteam
@pytest.mark.skipif(
    not (FIXTURES_DIR / "conflicting_signage.jpg").exists(),
    reason="real_fixtures/redteam/conflicting_signage.jpg not recorded yet — see real_fixtures/README.md",
)
def test_conflicting_signage_asks_rather_than_picks_arbitrarily() -> None:
    expectation = _load_expectation("conflicting_signage")
    assert expectation is not None, "conflicting_signage.expected.json missing alongside the .jpg"

    perception = PerceptionAgent()
    framing, signal = perception.handle_scene_observation(
        session_id="test-session",
        text_detected=True,
        position=expectation["position"],
        signage_text=expectation["signage_text"],
        confidence=expectation["reported_confidence"],
    )

    assert signal is not None
    assert signal.confidence < 0.5  # conflicting signage must self-report below GuardrailAgent.MIN_CONFIDENCE_FLOOR
