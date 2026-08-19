"""Design doc §9's own required Daily Briefing test: stage a route
disruption fixture overnight, assert the next session's opening turn
includes the correct, unprompted summary — DoD #5."""
import json

import pytest

from app.agents.calibration import CalibrationAgent
from app.agents.daily_briefing import DailyBriefingAgent
from app.agents.escalation import EscalationAgent, LoggingNotificationSender
from app.agents.grounding import GroundingAgent
from app.agents.guardrail import GuardrailAgent
from app.agents.guidance import GuidanceAgent
from app.agents.memory import MemoryAgent, RegularRoute
from app.agents.orchestrator import TaskOrchestrator
from app.agents.perception import PerceptionAgent
from app.agents.planner import PlannerAgent
from app.agents.replanning import ReplanningAgent
from app.agents.router import DomainRouterAgent
from app.domains.transit.config import TransitFeedConfig
from app.domains.transit.domain import TransitDomain
from app.domains.transit.realtime import DecodedAlert
from app.domains.transit.static_index import GtfsStaticIndex
from app.tests.doubles.fake_firestore import FakeFirestoreClient
from app.tests.doubles.fake_llm_runner import FakeLlmAgentRunner
from app.tests.fixtures.gtfs_builders import build_static_feed_zip

_CONFIG = TransitFeedConfig(
    domain_id="transit-ch", display_name="Switzerland", static_feed_url="", realtime_feed_url="",
    auth_header=None, locale="de-CH",
)
_STOPS = [{"stop_id": "8503000:4", "stop_name": "Zürich HB", "platform_code": "4", "parent_station": "8503000"}]
_STOP_TIMES = [{"trip_id": "IC1.TA.1", "stop_id": "8503000:4", "arrival_time": "23:59:59", "stop_sequence": "1"}]


class _FakePublisher:
    def publish(self, topic_path, data):
        class _F:
            def result(self):
                return "id"
        return _F()

    def topic_path(self, project, topic):
        return f"projects/{project}/topics/{topic}"


class _OvernightAlertPoller:
    """Standing in for TripUpdatePoller — the "overnight" staging is that
    this alert exists before the morning session ever starts, exactly as
    the design doc's demo script describes."""

    async def latest_for(self, trip_id, candidate_stop_ids):
        return None

    async def latest_alert_for(self, trip_id, candidate_stop_ids):
        from datetime import datetime, timezone
        return DecodedAlert(
            header_text="Delays", description_text="Signal fault near Zürich HB",
            fetched_at=datetime.now(timezone.utc),
        )


def _orchestrator(db, transit: TransitDomain) -> TaskOrchestrator:
    grounding = GroundingAgent(transit)
    planner_response = json.dumps({
        "description": "Head to the platform", "action_type": "guidance",
        "requires_confirmation": False, "category": "transit-guidance",
    })
    return TaskOrchestrator(
        perception=PerceptionAgent(),
        router=DomainRouterAgent(FakeLlmAgentRunner(), domains=[transit]),
        grounding_agents={transit.domain_id: grounding},
        domains={transit.domain_id: transit},
        planner=PlannerAgent(FakeLlmAgentRunner(next_response=planner_response)),
        guardrail=GuardrailAgent(),
        replanning=ReplanningAgent(),
        guidance=GuidanceAgent(FakeLlmAgentRunner(next_response="Head to the platform.")),
        memory=MemoryAgent(db),
        escalation=EscalationAgent(db, _FakePublisher(), LoggingNotificationSender()),
    )


@pytest.mark.asyncio
async def test_staged_overnight_disruption_produces_an_unprompted_briefing_at_next_session() -> None:
    db = FakeFirestoreClient()
    memory = MemoryAgent(db)
    static_index = GtfsStaticIndex(build_static_feed_zip(_STOPS, _STOP_TIMES))
    transit = TransitDomain(_CONFIG, static_index, _OvernightAlertPoller())

    # Overnight: the user has a stored regular route, and the background
    # job runs with no session and no user present.
    await memory.add_regular_route("u1", RegularRoute(domain_id="transit-ch", goal_text="get me to Zürich HB"))
    briefing_agent = DailyBriefingAgent(memory, {"transit-ch": transit})
    created = await briefing_agent.run_for_all_uids(["u1"])
    assert created == 1

    # Next morning: the user opens a session — nobody asked anything yet.
    orchestrator = _orchestrator(db, transit)
    result = await orchestrator.check_for_pending_daily_briefing("s1", "u1")

    assert result is not None
    assert "delays" in result.guidance.text.lower()
    assert "zürich hb" in result.guidance.text.lower()
    assert result.guardrail.decision == "approved"

    # And it's a one-shot delivery — a second session doesn't repeat it.
    assert await orchestrator.check_for_pending_daily_briefing("s2", "u1") is None


@pytest.mark.asyncio
async def test_daily_briefing_and_calibration_proposals_coexist_independently() -> None:
    """Regression for the ordering decision in Task 8 — a pending
    CalibrationProposal must still surface correctly even when a
    DailyBriefing was already delivered in the same session-connect flow;
    the two mechanisms share no state."""
    db = FakeFirestoreClient()
    memory = MemoryAgent(db)
    static_index = GtfsStaticIndex(build_static_feed_zip(_STOPS, _STOP_TIMES))
    transit = TransitDomain(_CONFIG, static_index, _OvernightAlertPoller())

    await memory.add_regular_route("u1", RegularRoute(domain_id="transit-ch", goal_text="get me to Zürich HB"))
    await DailyBriefingAgent(memory, {"transit-ch": transit}).run_for_all_uids(["u1"])

    for _ in range(15):
        await memory.record_confirmation_outcome(
            "u1", category="pharmacy_refill", provider="cvs-main-st", decision="approved"
        )
    await CalibrationAgent(memory).run_for_all_users([("u1", "pharmacy_refill", "cvs-main-st")])

    orchestrator = _orchestrator(db, transit)
    briefing = await orchestrator.check_for_pending_daily_briefing("s1", "u1")
    calibration_offer = await orchestrator.check_for_pending_calibration_proposal("s1", "u1")

    assert briefing is not None
    assert calibration_offer is not None
    assert "delays" in briefing.guidance.text.lower()
    assert "pattern" in calibration_offer.guidance.text.lower()
