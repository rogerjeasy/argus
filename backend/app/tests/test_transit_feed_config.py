from app.core.config import Settings
from app.domains.transit.config import build_transit_feed_configs


def test_build_transit_feed_configs_produces_switzerland_and_mbta() -> None:
    settings = Settings(
        gtfs_ch_static_feed_url="https://opentransportdata.swiss/static.zip",
        gtfs_ch_realtime_feed_url="https://opentransportdata.swiss/rt",
        gtfs_ch_auth_token="secret-token",
        gtfs_mbta_static_feed_url="https://cdn.mbta.com/MBTA_GTFS.zip",
        gtfs_mbta_realtime_feed_url="https://cdn.mbta.com/realtime/TripUpdates.pb",
    )

    configs = build_transit_feed_configs(settings)

    assert [c.domain_id for c in configs] == ["transit-ch", "transit-mbta"]
    ch, mbta = configs
    assert ch.auth_header == "Bearer secret-token"
    assert mbta.auth_header is None  # MBTA's raw GTFS-RT feed is keyless — the deliberate stress case
    assert ch.static_feed_url == "https://opentransportdata.swiss/static.zip"
    assert mbta.realtime_feed_url == "https://cdn.mbta.com/realtime/TripUpdates.pb"


def test_build_transit_feed_configs_omits_switzerland_when_unconfigured() -> None:
    # A dev machine with no Swiss token yet should still be able to run
    # against MBTA alone rather than fail Settings validation entirely.
    settings = Settings(gtfs_ch_static_feed_url="", gtfs_ch_realtime_feed_url="")

    configs = build_transit_feed_configs(settings)

    assert [c.domain_id for c in configs] == ["transit-mbta"]
