from datetime import datetime, timezone

import pytest

from app.models.agent_events import GroundedFact
from app.ws.agent_tools import ArgusToolbox


class _FakeTransitDomain:
    domain_id = "transit-mbta"
    executors: dict = {}

    def __init__(self, *, platform: str | None, disruption=None) -> None:
        self._platform = platform
        self._disruption = disruption

    def matches(self, goal_text: str) -> bool:
        return True

    async def ground(self, request) -> GroundedFact:
        if self._platform is None:
            return GroundedFact(key=request.key, value="", source="gtfs_realtime", confidence=0.0,
                                as_of=datetime.now(timezone.utc))
        return GroundedFact(key=request.key, value=self._platform, source="gtfs_realtime", confidence=1.0,
                            as_of=datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc))

    async def check_disruption(self, goal_text: str):
        return self._disruption


class _FakeMemory:
    def __init__(self) -> None:
        self.notes: dict[str, str] = {}

    async def remember(self, uid: str, key: str, value: str) -> None:
        self.notes[key] = value

    async def recall(self, uid: str, key: str) -> str | None:
        return self.notes.get(key)


class _FakeCallExecutor:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def execute(self, payload: dict) -> dict:
        self.calls.append(payload)
        return {"status": "success", "summary_text": "Refill confirmed, ready tomorrow.", "structured_data": {"copay": 12}}


async def _noop_speak(text: str) -> None:
    return None


def _toolbox(*, platform="3", disruption=None, memory=None, call_executor=None) -> ArgusToolbox:
    return ArgusToolbox(
        uid="u1",
        transit_domains=[_FakeTransitDomain(platform=platform, disruption=disruption)],
        memory=memory or _FakeMemory(),
        call_executor=call_executor,
        speak=_noop_speak,
    )


@pytest.mark.asyncio
async def test_get_transit_directions_returns_the_grounded_platform() -> None:
    result = await _toolbox(platform="7").dispatch("get_transit_directions", {"station": "North Station"})
    assert result["platform"] == "7"
    assert result["source"] == "gtfs_realtime"


@pytest.mark.asyncio
async def test_get_transit_directions_reports_when_nothing_is_grounded() -> None:
    result = await _toolbox(platform=None).dispatch("get_transit_directions", {"station": "Nowhere"})
    assert "error" in result


@pytest.mark.asyncio
async def test_check_transit_disruptions_reports_no_disruptions_cleanly() -> None:
    result = await _toolbox(disruption=None).dispatch("check_transit_disruptions", {"station": "North Station"})
    assert result == {"no_disruptions": True, "station": "North Station"}


@pytest.mark.asyncio
async def test_remember_and_recall_round_trip() -> None:
    toolbox = _toolbox()
    await toolbox.dispatch("remember", {"key": "home_address", "value": "42 Oak Street"})
    result = await toolbox.dispatch("recall", {"key": "home_address"})
    assert result == {"value": "42 Oak Street"}


@pytest.mark.asyncio
async def test_recall_of_an_unknown_key_is_an_error_not_a_crash() -> None:
    result = await _toolbox().dispatch("recall", {"key": "nope"})
    assert "error" in result


@pytest.mark.asyncio
async def test_place_phone_call_queues_a_confirmation_and_does_not_dial() -> None:
    executor = _FakeCallExecutor()
    toolbox = _toolbox(call_executor=executor)

    queued = await toolbox.dispatch("place_phone_call", {"phone_number": "+16175551234", "purpose": "confirm a refill"})

    assert queued["status"] == "confirmation_required"
    assert "+16175551234" in queued["read_back"]
    assert executor.calls == []  # nothing dialed yet
    assert toolbox.has_pending_action


@pytest.mark.asyncio
async def test_confirm_pending_action_true_places_the_real_call() -> None:
    executor = _FakeCallExecutor()
    toolbox = _toolbox(call_executor=executor)
    await toolbox.dispatch("place_phone_call", {"phone_number": "+16175551234", "purpose": "confirm a refill"})

    result = await toolbox.dispatch("confirm_pending_action", {"confirmed": True})

    assert result["status"] == "success"
    assert len(executor.calls) == 1
    assert not toolbox.has_pending_action


@pytest.mark.asyncio
async def test_confirm_pending_action_false_cancels_without_dialing() -> None:
    executor = _FakeCallExecutor()
    toolbox = _toolbox(call_executor=executor)
    await toolbox.dispatch("place_phone_call", {"phone_number": "+16175551234", "purpose": "confirm a refill"})

    result = await toolbox.dispatch("confirm_pending_action", {"confirmed": False})

    assert result == {"status": "cancelled"}
    assert executor.calls == []


@pytest.mark.asyncio
async def test_place_phone_call_without_a_configured_executor_says_so() -> None:
    result = await _toolbox(call_executor=None).dispatch(
        "place_phone_call", {"phone_number": "+1", "purpose": "x"}
    )
    assert "isn't set up" in result["error"]


@pytest.mark.asyncio
async def test_a_tool_that_raises_is_reported_not_propagated() -> None:
    class _Boom(_FakeMemory):
        async def recall(self, uid, key):
            raise RuntimeError("firestore down")

    result = await _toolbox(memory=_Boom()).dispatch("recall", {"key": "x"})
    assert "error" in result
