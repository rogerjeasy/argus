from app.agents.memory import DailyBriefing, MemoryAgent
from app.domains.transit.domain import TransitDomain


class DailyBriefingAgent:
    """Mirrors CalibrationAgent's shape: a read-mostly agent that turns a
    background pass with no active session and no user present into a
    queued write. For each user's stored RegularRoute, checks the matching
    TransitDomain for a real GTFS-RT alert (TransitDomain.check_disruption,
    Task 2) and, if disrupted, stores exactly one DailyBriefing — never more
    than one pending at a time per user, mirroring get_pending_daily_briefing's
    "first pending" read in MemoryAgent."""

    def __init__(self, memory: MemoryAgent, transit_domains: dict[str, TransitDomain]) -> None:
        self._memory = memory
        self._transit_domains = transit_domains

    async def run_for_all_uids(self, uids: list[str]) -> int:
        created = 0
        for uid in uids:
            existing = await self._memory.get_pending_daily_briefing(uid)
            if existing is not None:
                continue
            routes = await self._memory.get_regular_routes(uid)
            for route in routes:
                domain = self._transit_domains.get(route.domain_id)
                if domain is None:
                    continue
                summary = await domain.check_disruption(route.goal_text)
                if summary is None:
                    continue
                text = f"Heads up — {summary.header_text.lower()} on your usual route from {summary.stop_name}."
                if summary.description_text:
                    text += f" {summary.description_text}"
                briefing = DailyBriefing(summary_text=text, route_description=route.goal_text)
                await self._memory.store_daily_briefing(uid, briefing)
                created += 1
                break  # one briefing per user per run, matching "pending" being a singleton
        return created
