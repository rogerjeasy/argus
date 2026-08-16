import asyncio

import pytest

from app.domains.personal_admin.call_executor import CallExecutor
from app.domains.personal_admin.call_session_registry import CallSessionRegistry
from app.domains.personal_admin.models import CallOutcome
from app.tests.doubles.fake_twilio_client import FakeTwilioClient


def _payload() -> dict:
    return {
        "step_id": "step-1", "category": "pharmacy_refill_under_20", "provider": "Example Pharmacy",
        "executor": "call",
        "call_goal": {
            "target_phone_number": "+15559990000",
            "purpose": "confirm refill status",
            "structured_question": "Is it ready, and what is the co-pay?",
        },
    }


@pytest.mark.asyncio
async def test_execute_places_the_call_and_returns_success_on_resolved_outcome() -> None:
    twilio = FakeTwilioClient()
    registry = CallSessionRegistry()
    executor = CallExecutor(twilio, registry, from_number="+15551234567", public_base_url="https://argus.example", call_timeout_seconds=1.0)

    async def _resolve_soon():
        await asyncio.sleep(0.01)
        registry.resolve_outcome(
            "step-1",
            CallOutcome(status="connected_resolved", structured_data={"copay_cents": 1200}, transcript_summary="Refill confirmed, ready tomorrow.", confidence=0.9),
        )

    asyncio.ensure_future(_resolve_soon())
    result = await executor.execute(_payload())

    assert result["status"] == "success"
    assert result["structured_data"] == {"copay_cents": 1200}
    assert result["summary_text"] == "Refill confirmed, ready tomorrow."
    assert twilio.placed_calls[0]["to"] == "+15559990000"
    assert twilio.placed_calls[0]["from_"] == "+15551234567"
    assert "step-1" in twilio.placed_calls[0]["twiml"]


@pytest.mark.asyncio
async def test_execute_maps_busy_to_needs_retry() -> None:
    twilio = FakeTwilioClient()
    registry = CallSessionRegistry()
    executor = CallExecutor(twilio, registry, from_number="+15551234567", public_base_url="https://argus.example", call_timeout_seconds=1.0)

    async def _resolve_soon():
        await asyncio.sleep(0.01)
        registry.resolve_outcome("step-1", CallOutcome(status="busy", structured_data={}, transcript_summary="Line was busy.", confidence=1.0))

    asyncio.ensure_future(_resolve_soon())
    result = await executor.execute(_payload())

    assert result["status"] == "needs_retry"


@pytest.mark.asyncio
async def test_execute_maps_failed_call_to_failed_status() -> None:
    twilio = FakeTwilioClient()
    registry = CallSessionRegistry()
    executor = CallExecutor(twilio, registry, from_number="+15551234567", public_base_url="https://argus.example", call_timeout_seconds=1.0)

    async def _resolve_soon():
        await asyncio.sleep(0.01)
        registry.resolve_outcome("step-1", CallOutcome(status="failed", structured_data={}, transcript_summary="", confidence=0.0))

    asyncio.ensure_future(_resolve_soon())
    result = await executor.execute(_payload())

    assert result["status"] == "failed"


@pytest.mark.asyncio
async def test_execute_times_out_and_reports_failed() -> None:
    twilio = FakeTwilioClient()
    registry = CallSessionRegistry()
    executor = CallExecutor(twilio, registry, from_number="+15551234567", public_base_url="https://argus.example", call_timeout_seconds=0.05)

    result = await executor.execute(_payload())

    assert result["status"] == "failed"
    assert "timed out" in result["summary_text"].lower()


@pytest.mark.asyncio
async def test_execute_reports_failed_when_place_call_raises() -> None:
    class _RaisingTwilioClient(FakeTwilioClient):
        async def place_call(self, **kwargs):
            raise RuntimeError("Twilio account suspended")

    executor = CallExecutor(_RaisingTwilioClient(), CallSessionRegistry(), from_number="+15551234567", public_base_url="https://argus.example")

    result = await executor.execute(_payload())

    assert result["status"] == "failed"
