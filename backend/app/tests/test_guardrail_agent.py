from app.agents.guardrail import MIN_CONFIDENCE_FLOOR, GuardrailAgent
from app.agents.memory import StandingPermission
from app.models.agent_events import PlanStep


def _step(**overrides) -> PlanStep:
    defaults = dict(
        step_id="step-1", domain_id="stub", description="Head to platform 4",
        action_type="guidance", requires_confirmation=False, payload={"category": "stub-guidance"},
    )
    defaults.update(overrides)
    return PlanStep(**defaults)


def test_first_time_category_with_no_standing_permission_always_requires_confirmation() -> None:
    agent = GuardrailAgent()
    decision = agent.evaluate(_step(), confidence=0.99, standing_permissions=[])
    assert decision.decision == "requires_confirmation"


def test_below_confidence_floor_is_denied_regardless_of_permissions() -> None:
    agent = GuardrailAgent()
    permissions = [StandingPermission(category="stub-guidance", threshold=0.5)]
    decision = agent.evaluate(_step(), confidence=MIN_CONFIDENCE_FLOOR - 0.01, standing_permissions=permissions)
    assert decision.decision == "denied"


def test_matching_standing_permission_above_threshold_is_approved() -> None:
    agent = GuardrailAgent()
    permissions = [StandingPermission(category="stub-guidance", threshold=0.8)]
    decision = agent.evaluate(_step(), confidence=0.9, standing_permissions=permissions)
    assert decision.decision == "approved"


def test_matching_standing_permission_below_its_own_threshold_requires_confirmation() -> None:
    agent = GuardrailAgent()
    permissions = [StandingPermission(category="stub-guidance", threshold=0.95)]
    decision = agent.evaluate(_step(), confidence=0.9, standing_permissions=permissions)
    assert decision.decision == "requires_confirmation"


def test_domain_declared_requires_confirmation_overrides_standing_permission() -> None:
    agent = GuardrailAgent()
    permissions = [StandingPermission(category="stub-guidance", threshold=0.5)]
    decision = agent.evaluate(_step(requires_confirmation=True), confidence=0.99, standing_permissions=permissions)
    assert decision.decision == "requires_confirmation"
