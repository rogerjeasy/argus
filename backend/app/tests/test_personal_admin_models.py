import pytest
from pydantic import ValidationError

from app.domains.personal_admin.models import CallGoal, CallOutcome, ExecutorOutcome, TriageResult


def test_triage_result_rejects_an_unrecognized_subflow() -> None:
    with pytest.raises(ValidationError):
        TriageResult(category="bill", urgency="normal", subflow="mail-it-yourself", confidence=0.9)


def test_triage_result_accepts_every_documented_subflow() -> None:
    for subflow in ("call", "form", "inform-only"):
        TriageResult(category="bill", urgency="normal", subflow=subflow, confidence=0.9)


def test_executor_outcome_rejects_an_unrecognized_status() -> None:
    with pytest.raises(ValidationError):
        ExecutorOutcome(step_id="s1", status="maybe", structured_data={}, summary_text="")


def test_call_outcome_rejects_an_unrecognized_status() -> None:
    with pytest.raises(ValidationError):
        CallOutcome(status="ringing-forever", structured_data={}, transcript_summary="", confidence=0.5)


def test_call_goal_round_trips_through_model_dump() -> None:
    goal = CallGoal(target_phone_number="+15551234567", purpose="confirm refill status", structured_question="Is the refill ready and what is the co-pay?")

    assert CallGoal(**goal.model_dump()) == goal
