import httpx
import pytest

from app.core.config import Settings
from app.domains.indoor_wayfinding.registry import get_indoor_wayfinding_domain, reset_indoor_wayfinding_registry_for_tests
from app.tests.fixtures.venue_directory_builders import build_directory_json

_RealAsyncClient = httpx.AsyncClient  # see test_transit_domain_registry.py for why this capture matters


class _FakeTransport(httpx.AsyncBaseTransport):
    def __init__(self, body: bytes) -> None:
        self._body = body
        self.request_count = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.request_count += 1
        return httpx.Response(200, content=self._body, request=request)


@pytest.fixture(autouse=True)
def _reset_registry():
    reset_indoor_wayfinding_registry_for_tests()
    yield
    reset_indoor_wayfinding_registry_for_tests()


@pytest.mark.asyncio
async def test_no_directory_url_configured_never_makes_a_network_call(monkeypatch) -> None:
    called = False

    def _fail_if_called(**kw):
        nonlocal called
        called = True
        raise AssertionError("must not construct an httpx client when no directory_url is configured")

    monkeypatch.setattr("app.domains.indoor_wayfinding.registry.httpx.AsyncClient", _fail_if_called)
    settings = Settings(indoor_wayfinding_venue_id="", indoor_wayfinding_directory_url="")

    domain = await get_indoor_wayfinding_domain(settings)

    assert called is False
    assert domain.domain_id == "indoor_wayfinding"


@pytest.mark.asyncio
async def test_configured_directory_url_is_fetched_and_cached(monkeypatch) -> None:
    body = build_directory_json({"venue-a": [{"target": "breakfast room", "value": "Level 2"}]})
    transport = _FakeTransport(body)
    monkeypatch.setattr(
        "app.domains.indoor_wayfinding.registry.httpx.AsyncClient", lambda **kw: _RealAsyncClient(transport=transport)
    )
    settings = Settings(indoor_wayfinding_venue_id="venue-a", indoor_wayfinding_directory_url="https://example.org/d.json")

    domain1 = await get_indoor_wayfinding_domain(settings)
    domain2 = await get_indoor_wayfinding_domain(settings)

    assert transport.request_count == 1  # cached after first build, same as _LazyTransitDomainRegistry
    assert domain1 is domain2

    from app.domains import GroundingRequest  # sanity: directory data actually loaded, not just fetched
    fact = await domain1.ground(GroundingRequest(key="k", raw_goal_text="breakfast room"))
    assert fact.value == "Level 2"
