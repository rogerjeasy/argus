import asyncio

import httpx

from app.core.config import Settings
from app.domains.indoor_wayfinding.config import build_venue_directory_config
from app.domains.indoor_wayfinding.directory_index import VenueDirectoryIndex
from app.domains.indoor_wayfinding.domain import IndoorWayfindingDomain

#: An empty directory (zero entries for any venue) — has_data_for() is
#: False for everything, so the domain runs in pure signage-only mode.
#: Constructing this needs no I/O, unlike VenueDirectoryIndex(real_bytes).
_EMPTY_DIRECTORY = VenueDirectoryIndex(b"{}")


class _LazyIndoorWayfindingRegistry:
    """Builds the domain's VenueDirectoryIndex from a real network fetch at
    most once, and only when a directory_data_url is actually configured —
    mirrors _LazyTransitDomainRegistry (app/domains/transit/registry.py),
    except the zero-config case here must skip the network entirely rather
    than fetching a default URL, since there is no default directory to
    fetch."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._domain: IndoorWayfindingDomain | None = None
        self._lock = asyncio.Lock()

    async def get(self) -> IndoorWayfindingDomain:
        if self._domain is not None:
            return self._domain
        async with self._lock:
            if self._domain is None:
                self._domain = await self._build()
        return self._domain

    async def _build(self) -> IndoorWayfindingDomain:
        config = build_venue_directory_config(self._settings)
        if config.directory_data_url is None:
            return IndoorWayfindingDomain(config, _EMPTY_DIRECTORY)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(config.directory_data_url)
            response.raise_for_status()
            index = VenueDirectoryIndex(response.content)
        return IndoorWayfindingDomain(config, index)


_registry: _LazyIndoorWayfindingRegistry | None = None


async def get_indoor_wayfinding_domain(settings: Settings) -> IndoorWayfindingDomain:
    global _registry
    if _registry is None:
        _registry = _LazyIndoorWayfindingRegistry(settings)
    return await _registry.get()


def reset_indoor_wayfinding_registry_for_tests() -> None:
    global _registry
    _registry = None
