from dataclasses import dataclass
from datetime import datetime, timezone

from app.domains import GroundingRequest
from app.domains.transit.config import TransitFeedConfig
from app.domains.transit.realtime import TripUpdatePoller
from app.domains.transit.static_index import GtfsStaticIndex
from app.models.agent_events import GroundedFact

#: Guardrail's own floor is 0.5 (app/agents/guardrail.py); this domain
#: reports comfortably below it on any unresolved-stop or feed-outage case
#: so Guardrail's existing rule — not a new one — handles it.
_UNRESOLVED_CONFIDENCE = 0.0


@dataclass(frozen=True)
class DisruptionSummary:
    stop_name: str
    header_text: str
    description_text: str | None


class TransitDomain:
    """Config-driven GTFS-Realtime domain plugin — one instance per
    configured feed. No agency-specific branch exists anywhere in this
    class; everything that differs between Switzerland and MBTA lives in
    the TransitFeedConfig it was constructed with."""

    def __init__(self, config: TransitFeedConfig, static_index: GtfsStaticIndex, poller: TripUpdatePoller) -> None:
        self.domain_id = config.domain_id
        self._config = config
        self._static_index = static_index
        self._poller = poller
        self.executors: dict = {}  # informational domain only — no executors, matches the design doc §5

    def matches(self, goal_text: str) -> bool:
        lowered = goal_text.lower()
        return any(keyword in lowered for keyword in self._config.stop_name_keywords)

    async def ground(self, request: GroundingRequest) -> GroundedFact:
        static_stop = self._static_index.resolve_stop(request.raw_goal_text, now=request.now)
        if static_stop is None:
            return self._unresolved(request.key)

        siblings = self._static_index.sibling_stop_ids(static_stop.stop_id)
        trip_update = await self._poller.latest_for(static_stop.trip_id, siblings)
        if trip_update is None:
            # Covers both "feed outage/unreachable" and "feed reachable but
            # this trip has dropped off it" — the design doc §5 treats both
            # as the same case: report low confidence, never guess.
            return self._unresolved(request.key)

        platform = self._static_index.platform_code_for(trip_update.stop_id)
        return GroundedFact(
            key=request.key, value=platform, source="gtfs_realtime", confidence=1.0, as_of=trip_update.fetched_at
        )

    def _unresolved(self, key: str) -> GroundedFact:
        return GroundedFact(
            key=key, value="", source="gtfs_realtime", confidence=_UNRESOLVED_CONFIDENCE, as_of=datetime.now(timezone.utc)
        )

    async def check_disruption(self, goal_text: str) -> DisruptionSummary | None:
        """Same resolve_stop() lookup ground() uses, but checks the
        realtime feed's Alert entities instead of TripUpdate — used only by
        DailyBriefingAgent's no-session background pass, never by the live
        goal-handling path. goal_text is the same kind of spoken phrase a
        user's regular route is stored as (see MemoryAgent.RegularRoute)."""
        static_stop = self._static_index.resolve_stop(goal_text)
        if static_stop is None:
            return None
        siblings = self._static_index.sibling_stop_ids(static_stop.stop_id)
        alert = await self._poller.latest_alert_for(static_stop.trip_id, siblings)
        if alert is None:
            return None
        return DisruptionSummary(
            stop_name=static_stop.stop_name, header_text=alert.header_text, description_text=alert.description_text,
        )
