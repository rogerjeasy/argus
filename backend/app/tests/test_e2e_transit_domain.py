"""Phase 2's version of test_e2e_stub_domain.py's Definition of Done
regression, with TransitDomain (real GTFS decode path) substituted for
StubDomain, parameterized over both configured feeds."""
import json

import pytest

from app.agents.escalation import EscalationAgent, LoggingNotificationSender
from app.agents.grounding import GroundingAgent
from app.agents.guardrail import GuardrailAgent
from app.agents.guidance import GuidanceAgent
from app.agents.memory import MemoryAgent
from app.agents.orchestrator import TaskOrchestrator
from app.agents.perception import PerceptionAgent
from app.agents.planner import PlannerAgent
from app.agents.replanning import MAX_REPLAN_ATTEMPTS, ReplanningAgent
from app.agents.router import DomainRouterAgent
from app.domains.transit.config import TransitFeedConfig
from app.domains.transit.domain import TransitDomain
from app.domains.transit.static_index import GtfsStaticIndex
from app.models.agent_events import PerceivedGoal
from app.tests.doubles.fake_firestore import FakeFirestoreClient
from app.tests.doubles.fake_llm_runner import FakeLlmAgentRunner
from app.tests.fixtures.gtfs_builders import build_static_feed_zip


class _FakePublisher:
    def publish(self, topic_path, data):
        class _F:
            def result(self):
                return "id"
        return _F()

    def topic_path(self, project, topic):
        return f"projects/{project}/topics/{topic}"


class _ScriptedPoller:
    """Test double standing in for TripUpdatePoller — set_stop() lets a
    test move the answer mid-run, exactly like FakeGroundingSource did for
    the stub e2e test."""

    def __init__(self, stop_id: str) -> None:
        self._stop_id = stop_id

    def set_stop(self, stop_id: str) -> None:
        self._stop_id = stop_id

    async def latest_for(self, trip_id, candidate_stop_ids):
        from datetime import datetime, timezone
        from app.domains.transit.realtime import DecodedTripUpdate
        return DecodedTripUpdate(trip_id=trip_id, stop_id=self._stop_id, fetched_at=datetime.now(timezone.utc))


_FEED_CASES = [
    TransitFeedConfig(
        domain_id="transit-ch", display_name="Switzerland", static_feed_url="", realtime_feed_url="",
        auth_header="Bearer secret", locale="de-CH",
    ),
    TransitFeedConfig(
        domain_id="transit-mbta", display_name="MBTA", static_feed_url="", realtime_feed_url="",
        auth_header=None, locale="en-US",
    ),
]
_STOPS = [
    {"stop_id": "platform-4", "stop_name": "Central Station", "platform_code": "4", "parent_station": "central"},
    {"stop_id": "platform-7", "stop_name": "Central Station", "platform_code": "7", "parent_station": "central"},
]
_STOP_TIMES = [{"trip_id": "trip-1", "stop_id": "platform-4", "arrival_time": "23:59:59", "stop_sequence": "1"}]


def _orchestrator(config: TransitFeedConfig, poller: _ScriptedPoller) -> TaskOrchestrator:
    static_index = GtfsStaticIndex(build_static_feed_zip(_STOPS, _STOP_TIMES))
    transit = TransitDomain(config, static_index, poller)
    grounding = GroundingAgent(transit)
    db = FakeFirestoreClient()
    planner_response = json.dumps({
        "description": "Head to the platform", "action_type": "guidance",
        "requires_confirmation": False, "category": "transit-guidance",
    })
    return TaskOrchestrator(
        perception=PerceptionAgent(),
        router=DomainRouterAgent(FakeLlmAgentRunner(), domains=[transit]),
        grounding_agents={config.domain_id: grounding},
        domains={config.domain_id: transit},
        planner=PlannerAgent(FakeLlmAgentRunner(next_response=planner_response)),
        guardrail=GuardrailAgent(),
        replanning=ReplanningAgent(),
        guidance=GuidanceAgent(FakeLlmAgentRunner(next_response="Head to the platform.")),
        memory=MemoryAgent(db),
        escalation=EscalationAgent(db, _FakePublisher(), LoggingNotificationSender()),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("config", _FEED_CASES, ids=lambda c: c.domain_id)
async def test_full_loop_real_feed_decode_to_divergence_to_replan(config: TransitFeedConfig) -> None:
    poller = _ScriptedPoller("platform-4")
    orchestrator = _orchestrator(config, poller)

    goal = PerceivedGoal(session_id="s1", uid="u1", raw_text="get me to the platform at Central Station")
    initial = await orchestrator.handle_goal(goal)
    assert initial.guidance.text
    assert initial.guardrail.decision == "requires_confirmation"

    poller.set_stop("platform-7")  # realtime feed reassigns the trip to a different platform
    replanned = await orchestrator.check_for_divergence(session_id="s1", uid="u1")

    assert replanned is not None
    assert replanned.guidance.haptic_pattern == "pattern-urgent"


@pytest.mark.asyncio
@pytest.mark.parametrize("config", _FEED_CASES, ids=lambda c: c.domain_id)
async def test_bounded_replan_never_loops_past_max_attempts(config: TransitFeedConfig) -> None:
    poller = _ScriptedPoller("platform-4")
    orchestrator = _orchestrator(config, poller)

    goal = PerceivedGoal(session_id="s1", uid="u1", raw_text="get me to the platform at Central Station")
    await orchestrator.handle_goal(goal)

    results = []
    for i in range(MAX_REPLAN_ATTEMPTS + 2):
        poller.set_stop("platform-4" if i % 2 == 0 else "platform-7")
        result = await orchestrator.check_for_divergence(session_id="s1", uid="u1")
        results.append(result)
        if result is not None and result.guardrail.decision == "denied":
            break

    escalated = [r for r in results if r is not None and r.guardrail.decision == "denied"]
    assert len(escalated) == 1
