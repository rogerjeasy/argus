import httpx
import pytest

from app.core.config import Settings
from app.domains.transit.registry import get_transit_domains, reset_transit_domain_registry_for_tests
from app.tests.fixtures.gtfs_builders import build_static_feed_zip

_STOPS = [{"stop_id": "s1", "stop_name": "North Station", "platform_code": "", "parent_station": ""}]
_STOP_TIMES = [{"trip_id": "t1", "stop_id": "s1", "arrival_time": "09:00:00", "stop_sequence": "1"}]
_STATIC_ZIP = build_static_feed_zip(_STOPS, _STOP_TIMES)

# Captured before any monkeypatch runs: `app.domains.transit.registry.httpx`
# is the exact same module object as this file's own `import httpx` (Python
# modules are singletons), so patching `...registry.httpx.AsyncClient` also
# changes what the name `httpx.AsyncClient` resolves to right here. A lambda
# that called `httpx.AsyncClient(...)` directly would therefore call itself
# — this captured reference is what breaks that recursion.
_RealAsyncClient = httpx.AsyncClient


class _FakeTransport(httpx.AsyncBaseTransport):
    def __init__(self) -> None:
        self.request_count = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.request_count += 1
        return httpx.Response(200, content=_STATIC_ZIP, request=request)


@pytest.fixture(autouse=True)
def _reset_registry():
    reset_transit_domain_registry_for_tests()
    yield
    reset_transit_domain_registry_for_tests()


@pytest.mark.asyncio
async def test_get_transit_domains_builds_mbta_only_when_ch_unconfigured(monkeypatch) -> None:
    transport = _FakeTransport()
    monkeypatch.setattr("app.domains.transit.registry.httpx.AsyncClient", lambda **kw: _RealAsyncClient(transport=transport))
    settings = Settings(gtfs_ch_static_feed_url="", gtfs_ch_realtime_feed_url="")

    domains = await get_transit_domains(settings)

    assert [d.domain_id for d in domains] == ["transit-mbta"]


@pytest.mark.asyncio
async def test_get_transit_domains_fetches_the_static_feed_exactly_once(monkeypatch) -> None:
    transport = _FakeTransport()
    monkeypatch.setattr("app.domains.transit.registry.httpx.AsyncClient", lambda **kw: _RealAsyncClient(transport=transport))
    settings = Settings(gtfs_ch_static_feed_url="", gtfs_ch_realtime_feed_url="")

    await get_transit_domains(settings)
    await get_transit_domains(settings)

    assert transport.request_count == 1  # second call served from the lazy cache
