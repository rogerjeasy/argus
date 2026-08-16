"""GtfsStaticIndex against the real GTFS static CSV schema (stops.txt,
stop_times.txt) — see gtfs_builders.py for why the bytes are built
in-process rather than checked in as an opaque binary."""
from datetime import time

from app.domains.transit.static_index import GtfsStaticIndex
from app.tests.fixtures.gtfs_builders import build_static_feed_zip

_STOPS = [
    {"stop_id": "8503000:4", "stop_name": "Zürich HB", "platform_code": "4", "parent_station": "8503000"},
    {"stop_id": "8503000:7", "stop_name": "Zürich HB", "platform_code": "7", "parent_station": "8503000"},
    {"stop_id": "place-north", "stop_name": "North Station", "platform_code": "", "parent_station": ""},
]
_STOP_TIMES = [
    {"trip_id": "IC1.TA.1", "stop_id": "8503000:4", "arrival_time": "14:32:00", "stop_sequence": "3"},
    {"trip_id": "commuter-rail-99", "stop_id": "place-north", "arrival_time": "09:15:00", "stop_sequence": "1"},
]


def _index() -> GtfsStaticIndex:
    return GtfsStaticIndex(build_static_feed_zip(_STOPS, _STOP_TIMES))


def test_resolve_stop_matches_a_station_name_mentioned_in_the_goal_text() -> None:
    stop = _index().resolve_stop("get me to the platform for my train at Zürich HB", now=time(10, 0))

    assert stop is not None
    assert stop.trip_id == "IC1.TA.1"
    assert stop.platform_code == "4"


def test_resolve_stop_returns_none_for_an_unknown_station() -> None:
    assert _index().resolve_stop("get me to Mars Station") is None


def test_resolve_stop_skips_a_departure_already_in_the_past() -> None:
    # now is after 14:32, so this stop_time row is no longer "next"
    assert _index().resolve_stop("Zürich HB", now=time(23, 0)) is None


def test_sibling_stop_ids_groups_by_parent_station() -> None:
    siblings = _index().sibling_stop_ids("8503000:4")

    assert siblings == frozenset({"8503000:4", "8503000:7"})


def test_platform_code_for_falls_back_to_stop_name_when_missing() -> None:
    assert _index().platform_code_for("place-north") == "North Station"
