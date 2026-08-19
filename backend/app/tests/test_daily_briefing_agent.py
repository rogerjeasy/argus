import pytest

from app.agents.daily_briefing import DailyBriefingAgent
from app.agents.memory import MemoryAgent, RegularRoute
from app.domains.transit.config import TransitFeedConfig
from app.domains.transit.domain import TransitDomain
from app.domains.transit.static_index import GtfsStaticIndex
from app.tests.doubles.fake_firestore import FakeFirestoreClient
from app.tests.fixtures.gtfs_builders import build_static_feed_zip

_CONFIG = TransitFeedConfig(
    domain_id="transit-ch", display_name="Switzerland", static_feed_url="", realtime_feed_url="",
    auth_header=None, locale="de-CH",
)
_STOPS = [{"stop_id": "8503000:4", "stop_name": "Zürich HB", "platform_code": "4", "parent_station": "8503000"}]
_STOP_TIMES = [{"trip_id": "IC1.TA.1", "stop_id": "8503000:4", "arrival_time": "23:59:59", "stop_sequence": "1"}]


class _FakePoller:
    def __init__(self, alert=None) -> None:
        self._alert = alert

    async def latest_for(self, trip_id, candidate_stop_ids):
        return None

    async def latest_alert_for(self, trip_id, candidate_stop_ids):
        return self._alert


def _transit_domain(alert=None) -> TransitDomain:
    static_index = GtfsStaticIndex(build_static_feed_zip(_STOPS, _STOP_TIMES))
    return TransitDomain(_CONFIG, static_index, _FakePoller(alert))


@pytest.mark.asyncio
async def test_run_for_all_uids_creates_a_briefing_when_disrupted() -> None:
    from datetime import datetime, timezone
    from app.domains.transit.realtime import DecodedAlert

    alert = DecodedAlert(header_text="Delays", description_text="Signal fault", fetched_at=datetime.now(timezone.utc))
    db = FakeFirestoreClient()
    memory = MemoryAgent(db)
    await memory.add_regular_route("u1", RegularRoute(domain_id="transit-ch", goal_text="get me to Zürich HB"))

    agent = DailyBriefingAgent(memory, {"transit-ch": _transit_domain(alert)})
    created = await agent.run_for_all_uids(["u1"])

    assert created == 1
    pending = await memory.get_pending_daily_briefing("u1")
    assert pending is not None
    _, briefing = pending
    assert "delays" in briefing.summary_text.lower()
    assert briefing.route_description == "get me to Zürich HB"


@pytest.mark.asyncio
async def test_run_for_all_uids_creates_nothing_when_no_disruption() -> None:
    db = FakeFirestoreClient()
    memory = MemoryAgent(db)
    await memory.add_regular_route("u1", RegularRoute(domain_id="transit-ch", goal_text="get me to Zürich HB"))

    agent = DailyBriefingAgent(memory, {"transit-ch": _transit_domain(alert=None)})
    created = await agent.run_for_all_uids(["u1"])

    assert created == 0
    assert await memory.get_pending_daily_briefing("u1") is None


@pytest.mark.asyncio
async def test_run_for_all_uids_skips_users_with_no_regular_routes() -> None:
    db = FakeFirestoreClient()
    memory = MemoryAgent(db)

    agent = DailyBriefingAgent(memory, {"transit-ch": _transit_domain()})
    created = await agent.run_for_all_uids(["u1"])

    assert created == 0
