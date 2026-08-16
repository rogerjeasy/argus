import pytest

from app.domains.personal_admin.call_session_registry import CallSessionRegistry
from app.domains.personal_admin.models import CallGoal, CallOutcome
from app.tests.doubles.fake_twilio_client import FakeTwilioClient


def _goal() -> CallGoal:
    return CallGoal(target_phone_number="+15559990000", purpose="confirm refill status", structured_question="Is it ready?")


def test_register_then_get_call_goal_and_twilio_client_round_trip() -> None:
    registry = CallSessionRegistry()
    twilio = FakeTwilioClient()

    registry.register("step-1", _goal(), twilio)

    assert registry.get_call_goal("step-1") == _goal()
    assert registry.get_twilio_client("step-1") is twilio


def test_get_call_goal_for_unknown_step_returns_none() -> None:
    assert CallSessionRegistry().get_call_goal("never-registered") is None


def test_set_and_get_call_sid() -> None:
    registry = CallSessionRegistry()
    registry.register("step-1", _goal(), FakeTwilioClient())

    registry.set_call_sid("step-1", "CA123")

    assert registry.get_call_sid("step-1") == "CA123"


@pytest.mark.asyncio
async def test_wait_for_outcome_returns_once_resolved() -> None:
    import asyncio

    registry = CallSessionRegistry()
    registry.register("step-1", _goal(), FakeTwilioClient())
    outcome = CallOutcome(status="connected_resolved", structured_data={}, transcript_summary="done", confidence=0.9)

    async def _resolve_soon():
        await asyncio.sleep(0.01)
        registry.resolve_outcome("step-1", outcome)

    asyncio.ensure_future(_resolve_soon())
    result = await registry.wait_for_outcome("step-1", timeout=1.0)

    assert result == outcome


@pytest.mark.asyncio
async def test_wait_for_outcome_times_out_when_never_resolved() -> None:
    registry = CallSessionRegistry()
    registry.register("step-1", _goal(), FakeTwilioClient())

    with pytest.raises(TimeoutError):
        await registry.wait_for_outcome("step-1", timeout=0.05)


def test_discard_removes_all_state_for_a_step() -> None:
    registry = CallSessionRegistry()
    registry.register("step-1", _goal(), FakeTwilioClient())
    registry.set_call_sid("step-1", "CA123")

    registry.discard("step-1")

    assert registry.get_call_goal("step-1") is None
    assert registry.get_call_sid("step-1") is None
