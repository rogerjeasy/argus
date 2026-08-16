from dataclasses import dataclass

from app.core.config import Settings

#: Shared across every feed on purpose — matches() is a fast pre-filter, not
#: the final classifier. Two transit feeds both matching the same generic
#: goal is exactly the case DomainRouterAgent's LLM disambiguation step
#: (app/agents/router.py) exists for; see Task 6's e2e test.
_TRANSIT_KEYWORDS = ("platform", "train", "gate", "connecting", "track", "gleis", "voie")


@dataclass(frozen=True)
class TransitFeedConfig:
    """One agency's feed configuration. This is the only place an
    agency-specific value is allowed to live — GtfsStaticIndex,
    TripUpdatePoller, and TransitDomain all take one of these and branch on
    nothing agency-specific themselves."""

    domain_id: str
    display_name: str
    static_feed_url: str
    realtime_feed_url: str
    auth_header: str | None
    locale: str
    stop_name_keywords: tuple[str, ...] = _TRANSIT_KEYWORDS


def build_transit_feed_configs(settings: Settings) -> list[TransitFeedConfig]:
    """Switzerland first when configured (it's the richer, primary feed —
    see the design doc §3), MBTA always (it's keyless, so it always works
    even with zero local configuration)."""
    configs: list[TransitFeedConfig] = []

    if settings.gtfs_ch_static_feed_url and settings.gtfs_ch_realtime_feed_url:
        configs.append(
            TransitFeedConfig(
                domain_id="transit-ch",
                display_name="Switzerland (opentransportdata.swiss)",
                static_feed_url=settings.gtfs_ch_static_feed_url,
                realtime_feed_url=settings.gtfs_ch_realtime_feed_url,
                auth_header=f"Bearer {settings.gtfs_ch_auth_token}" if settings.gtfs_ch_auth_token else None,
                locale="de-CH",
            )
        )

    configs.append(
        TransitFeedConfig(
            domain_id="transit-mbta",
            display_name="MBTA (Boston, USA)",
            static_feed_url=settings.gtfs_mbta_static_feed_url,
            realtime_feed_url=settings.gtfs_mbta_realtime_feed_url,
            auth_header=None,
            locale="en-US",
        )
    )

    return configs
