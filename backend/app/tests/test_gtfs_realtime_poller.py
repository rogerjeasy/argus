"""TripUpdatePoller against the real GTFS-Realtime protobuf schema. See
gtfs_builders.py for why the feed bytes are built in-process."""
import httpx
import pytest

from app.domains.transit.realtime import TripUpdatePoller
from app.tests.fixtures.gtfs_builders import build_trip_update_feed_message


class _FakeTransport(httpx.AsyncBaseTransport):
    """Records every request it receives and replies with scripted bytes —
    proves the poller sends the right URL/headers without a real network
    call."""

    def __init__(self, body: bytes, *, status_code: int = 200) -> None:
        self.body = body
        self.status_code = status_code
        self.requests: list[httpx.Request] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(self.status_code, content=self.body, request=request)


def _client(transport: httpx.AsyncBaseTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=transport)


@pytest.mark.asyncio
async def test_latest_for_decodes_the_matching_trip_and_stop() -> None:
    body = build_trip_update_feed_message([("IC1.TA.1", "8503000:4"), ("other-trip", "place-north")])
    transport = _FakeTransport(body)
    poller = TripUpdatePoller(feed_url="https://feed.example/rt", auth_header=None, client=_client(transport))

    result = await poller.latest_for("IC1.TA.1", frozenset({"8503000:4", "8503000:7"}))

    assert result is not None
    assert result.trip_id == "IC1.TA.1"
    assert result.stop_id == "8503000:4"


@pytest.mark.asyncio
async def test_latest_for_sends_the_configured_auth_header_when_present() -> None:
    body = build_trip_update_feed_message([("t1", "s1")])
    transport = _FakeTransport(body)
    poller = TripUpdatePoller(
        feed_url="https://feed.example/rt", auth_header="Bearer secret", client=_client(transport)
    )

    await poller.latest_for("t1", frozenset({"s1"}))

    assert transport.requests[0].headers["Authorization"] == "Bearer secret"


@pytest.mark.asyncio
async def test_latest_for_sends_no_auth_header_when_none_configured() -> None:
    # MBTA's real feed is keyless — this is the deliberate stress case (see
    # the design doc §3): auth must be optional config, not assumed.
    body = build_trip_update_feed_message([("t1", "s1")])
    transport = _FakeTransport(body)
    poller = TripUpdatePoller(feed_url="https://feed.example/rt", auth_header=None, client=_client(transport))

    await poller.latest_for("t1", frozenset({"s1"}))

    assert "Authorization" not in transport.requests[0].headers


@pytest.mark.asyncio
async def test_latest_for_returns_none_when_trip_not_in_feed() -> None:
    body = build_trip_update_feed_message([("some-other-trip", "s1")])
    transport = _FakeTransport(body)
    poller = TripUpdatePoller(feed_url="https://feed.example/rt", auth_header=None, client=_client(transport))

    assert await poller.latest_for("t1", frozenset({"s1"})) is None


@pytest.mark.asyncio
async def test_latest_for_returns_none_on_feed_outage() -> None:
    transport = _FakeTransport(b"", status_code=503)
    poller = TripUpdatePoller(feed_url="https://feed.example/rt", auth_header=None, client=_client(transport))

    assert await poller.latest_for("t1", frozenset({"s1"})) is None


@pytest.mark.asyncio
async def test_latest_for_caches_within_the_ttl() -> None:
    body = build_trip_update_feed_message([("t1", "s1")])
    transport = _FakeTransport(body)
    poller = TripUpdatePoller(
        feed_url="https://feed.example/rt", auth_header=None, cache_ttl_seconds=60.0, client=_client(transport)
    )

    await poller.latest_for("t1", frozenset({"s1"}))
    await poller.latest_for("t1", frozenset({"s1"}))

    assert len(transport.requests) == 1  # second call served from cache, no second fetch
