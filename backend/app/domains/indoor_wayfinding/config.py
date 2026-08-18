from dataclasses import dataclass

from app.core.config import Settings

#: The one venue this deployment demos wayfinding for — deliberately a
#: single config, not a registry keyed by many venues, per this plan's
#: scoped-for-one-demo-venue decision. "default" lets the domain register
#: and work in pure signage-only mode with zero configuration at all,
#: matching the design doc §3 fallback-demo role.
_DEFAULT_VENUE_ID = "default"


@dataclass(frozen=True)
class VenueDirectoryConfig:
    venue_id: str
    #: None means "no directory data source configured" — the domain runs
    #: in pure signage-only mode for this venue. Not the same as an empty
    #: string; a real (misconfigured) empty-string URL should fail loudly
    #: at fetch time instead of silently downgrading to signage-only.
    directory_data_url: str | None


def build_venue_directory_config(settings: Settings) -> VenueDirectoryConfig:
    return VenueDirectoryConfig(
        venue_id=settings.indoor_wayfinding_venue_id or _DEFAULT_VENUE_ID,
        directory_data_url=settings.indoor_wayfinding_directory_url or None,
    )
