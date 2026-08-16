from datetime import time

import pytest

from app.domains import GroundingRequest
from app.domains.transit.config import TransitFeedConfig
from app.domains.transit.domain import TransitDomain
from app.domains.transit.static_index import GtfsStaticIndex
from app.tests.fixtures.gtfs_builders import build_static_feed_zip

_CONFIG = TransitFeedConfig(
    domain_id="transit-ch",
    display_name="Switzerland (opentransportdata.swiss)",
    static_feed_url="https://feed.example/static.zip",
    realtime_feed_url="https://feed.example/rt",
    auth_header="Bearer secret",
    locale="de-CH",
)
_STOPS = [
    {"stop_id": "8503000:4", "stop_name": "Zürich HB", "platform_code": "4", "parent_station": "8503000"},
    {"stop_id": "8503000:7", "stop_name": "Zürich HB", "platform_code": "7", "parent_station": "8503000"},
]
_STOP_TIMES = [{"trip_id": "IC1.TA.1", "stop_id": "8503000:4", "arrival_time": "23:59:59", "stop_sequence": "3"}]


class _FakePoller:
    def __init__(self, decoded=None) -> None:
        self._decoded = decoded

    async def latest_for(self, trip_id, candidate_stop_ids):
        return self._decoded


def _domain(poller) -> TransitDomain:
    static_index = GtfsStaticIndex(build_static_feed_zip(_STOPS, _STOP_TIMES))
    return TransitDomain(_CONFIG, static_index, poller)


def test_matches_recognizes_transit_keywords() -> None:
    domain = _domain(_FakePoller())
    assert domain.matches("what platform is my train on") is True
    assert domain.matches("what's for dinner") is False


@pytest.mark.asyncio
async def test_ground_returns_the_realtime_platform() -> None:
    from app.domains.transit.realtime import DecodedTripUpdate
    from datetime import datetime, timezone

    decoded = DecodedTripUpdate(trip_id="IC1.TA.1", stop_id="8503000:7", fetched_at=datetime.now(timezone.utc))
    domain = _domain(_FakePoller(decoded))

    fact = await domain.ground(GroundingRequest(key="platform", raw_goal_text="get me to Zürich HB", now=time(10, 0)))

    assert fact.value == "7"  # realtime moved it from the statically-planned platform 4 to 7
    assert fact.source == "gtfs_realtime"
    assert fact.confidence == 1.0


@pytest.mark.asyncio
async def test_ground_returns_low_confidence_when_stop_unresolvable() -> None:
    domain = _domain(_FakePoller())

    fact = await domain.ground(GroundingRequest(key="platform", raw_goal_text="get me to Mars Station"))

    assert fact.confidence < 0.5


@pytest.mark.asyncio
async def test_ground_returns_low_confidence_on_feed_outage() -> None:
    domain = _domain(_FakePoller(decoded=None))

    fact = await domain.ground(
        GroundingRequest(key="platform", raw_goal_text="get me to Zürich HB", now=time(10, 0))
    )

    assert fact.confidence < 0.5
