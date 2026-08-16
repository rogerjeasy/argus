import asyncio

import httpx

from app.core.config import Settings
from app.domains.transit.config import build_transit_feed_configs
from app.domains.transit.domain import TransitDomain
from app.domains.transit.realtime import TripUpdatePoller
from app.domains.transit.static_index import GtfsStaticIndex


class _LazyTransitDomainRegistry:
    """Builds every configured TransitDomain's GtfsStaticIndex from a real
    network fetch exactly once, on first use — see this task's docstring
    for why, and app/core/pubsub.py's _LazyPublisherClient for the
    precedent this mirrors."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._domains: list[TransitDomain] | None = None
        self._lock = asyncio.Lock()

    async def get(self) -> list[TransitDomain]:
        if self._domains is not None:
            return self._domains
        async with self._lock:
            if self._domains is None:
                self._domains = await self._build()
        return self._domains

    async def _build(self) -> list[TransitDomain]:
        configs = build_transit_feed_configs(self._settings)
        domains: list[TransitDomain] = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for config in configs:
                response = await client.get(config.static_feed_url)
                response.raise_for_status()
                static_index = GtfsStaticIndex(response.content)
                poller = TripUpdatePoller(
                    feed_url=config.realtime_feed_url,
                    auth_header=config.auth_header,
                    cache_ttl_seconds=self._settings.gtfs_realtime_cache_ttl_seconds,
                )
                domains.append(TransitDomain(config, static_index, poller))
        return domains


_registry: _LazyTransitDomainRegistry | None = None


async def get_transit_domains(settings: Settings) -> list[TransitDomain]:
    global _registry
    if _registry is None:
        _registry = _LazyTransitDomainRegistry(settings)
    return await _registry.get()


def reset_transit_domain_registry_for_tests() -> None:
    global _registry
    _registry = None
