from datetime import datetime, timezone

from app.models.agent_events import (
    DivergenceSignal,
    EscalationEvent,
    GroundedFact,
    GuardrailDecision,
    GuidanceOutput,
    PerceivedGoal,
    PlanStep,
    SceneSignal,
)


def test_perceived_goal_round_trips() -> None:
    goal = PerceivedGoal(session_id="s1", uid="u1", raw_text="get me to platform 4")
    assert goal.model_dump()["raw_text"] == "get me to platform 4"


def test_plan_step_action_type_is_free_text_but_documented() -> None:
    step = PlanStep(
        step_id="step-1",
        domain_id="stub",
        description="Head to platform 4",
        action_type="guidance",
        requires_confirmation=False,
        payload={"category": "stub-guidance"},
    )
    assert step.payload["category"] == "stub-guidance"


def test_guardrail_decision_states() -> None:
    for decision in ("approved", "requires_confirmation", "denied"):
        GuardrailDecision(step_id="step-1", decision=decision, reason="test")


def test_guidance_output_haptic_and_earcon_are_optional() -> None:
    output = GuidanceOutput(session_id="s1", text="Head to platform 4")
    assert output.haptic_pattern is None
    assert output.earcon is None


def test_grounded_fact_requires_as_of() -> None:
    fact = GroundedFact(key="platform", value="4", source="stub_feed", confidence=0.95, as_of=datetime.now(timezone.utc))
    assert fact.source == "stub_feed"


def test_divergence_signal_carries_expected_and_observed() -> None:
    signal = DivergenceSignal(session_id="s1", plan_step_id="step-1", expected="4", observed="7", source="stub_feed")
    assert signal.expected != signal.observed


def test_escalation_event_carries_signals_list() -> None:
    event = EscalationEvent(
        session_id="s1", uid="u1", reason="bounded replan exhausted",
        signals=["replan_exhausted"], triggered_at=datetime.now(timezone.utc),
    )
    assert event.signals == ["replan_exhausted"]


def test_scene_signal_kind_is_free_text() -> None:
    signal = SceneSignal(session_id="s1", kind="signage_text", text="Platform 4", confidence=0.8)
    assert signal.kind == "signage_text"
