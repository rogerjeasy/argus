import time as time_module
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from google.transit import gtfs_realtime_pb2


@dataclass(frozen=True)
class DecodedTripUpdate:
    trip_id: str
    stop_id: str
    fetched_at: datetime


@dataclass(frozen=True)
class DecodedAlert:
    header_text: str
    description_text: str | None
    fetched_at: datetime


class TripUpdatePoller:
    """Fetches and decodes a GTFS-Realtime TripUpdate feed, caching the
    latest decode for `cache_ttl_seconds` so a burst of grounding requests
    during one active session doesn't hammer the upstream feed. `stop_id`
    resolution (which platform) is left to the caller — see TransitDomain
    (Task 4) — this class only ever answers "what does the feed say about
    this trip, at one of these candidate stops, right now."
    """

    def __init__(
        self,
        *,
        feed_url: str,
        auth_header: str | None,
        cache_ttl_seconds: float = 5.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._feed_url = feed_url
        self._auth_header = auth_header
        self._cache_ttl_seconds = cache_ttl_seconds
        self._client = client or httpx.AsyncClient(timeout=10.0)
        self._cached_message: gtfs_realtime_pb2.FeedMessage | None = None
        self._cached_at: float = 0.0

    async def _fetch(self) -> gtfs_realtime_pb2.FeedMessage:
        now = time_module.monotonic()
        if self._cached_message is not None and (now - self._cached_at) < self._cache_ttl_seconds:
            return self._cached_message

        headers = {"Authorization": self._auth_header} if self._auth_header else {}
        response = await self._client.get(self._feed_url, headers=headers)
        response.raise_for_status()

        message = gtfs_realtime_pb2.FeedMessage()
        message.ParseFromString(response.content)
        self._cached_message = message
        self._cached_at = now
        return message

    async def latest_for(self, trip_id: str, candidate_stop_ids: frozenset[str]) -> DecodedTripUpdate | None:
        try:
            message = await self._fetch()
        except httpx.HTTPError:
            return None

        for entity in message.entity:
            if not entity.HasField("trip_update"):
                continue
            trip_update = entity.trip_update
            if trip_update.trip.trip_id != trip_id:
                continue
            for stu in trip_update.stop_time_update:
                if stu.stop_id in candidate_stop_ids:
                    return DecodedTripUpdate(
                        trip_id=trip_id, stop_id=stu.stop_id, fetched_at=datetime.now(timezone.utc)
                    )
            return None  # trip is in this feed snapshot but not calling at any candidate stop
        return None  # trip not present in this feed snapshot at all

    async def latest_alert_for(self, trip_id: str, candidate_stop_ids: frozenset[str]) -> DecodedAlert | None:
        """Same cached FeedMessage latest_for() reads — GTFS-RT commonly
        serves TripUpdate and Alert entities on one combined feed URL (see
        the pre-demo checklist for the real-feed verification this still
        needs). Matches an alert whose informed_entity references this
        trip_id directly, or one of the candidate platform-level stop_ids —
        the same two-key match latest_for() already uses for TripUpdate."""
        try:
            message = await self._fetch()
        except httpx.HTTPError:
            return None

        for entity in message.entity:
            if not entity.HasField("alert"):
                continue
            alert = entity.alert
            matched = any(
                informed.trip.trip_id == trip_id or informed.stop_id in candidate_stop_ids
                for informed in alert.informed_entity
            )
            if not matched:
                continue
            header = alert.header_text.translation[0].text if alert.header_text.translation else ""
            description = alert.description_text.translation[0].text if alert.description_text.translation else None
            return DecodedAlert(header_text=header, description_text=description, fetched_at=datetime.now(timezone.utc))
        return None
