"""End-to-end regression for Phase 4a's Definition of Done: Indoor
Wayfinding demoable in both grounding modes (directory-backed, pure
signage-only), plus proof that its deliberate keyword collision with
TransitDomain (both match "gate") resolves correctly via the Domain
Router's LLM disambiguation step rather than silently breaking."""
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
from app.agents.replanning import ReplanningAgent
from app.agents.router import DomainRouterAgent
from app.domains.indoor_wayfinding.config import VenueDirectoryConfig
from app.domains.indoor_wayfinding.directory_index import VenueDirectoryIndex
from app.domains.indoor_wayfinding.domain import IndoorWayfindingDomain
from app.domains.transit.config import TransitFeedConfig
from app.domains.transit.domain import TransitDomain
from app.domains.transit.static_index import GtfsStaticIndex
from app.models.agent_events import PerceivedGoal, SceneSignal
from app.tests.doubles.fake_firestore import FakeFirestoreClient
from app.tests.doubles.fake_llm_runner import FakeLlmAgentRunner
from app.tests.fixtures.gtfs_builders import build_static_feed_zip
from app.tests.fixtures.venue_directory_builders import build_directory_json


class _FakePublisher:
    def publish(self, topic_path, data):
        class _F:
            def result(self):
                return "id"
        return _F()

    def topic_path(self, project, topic):
        return f"projects/{project}/topics/{topic}"


def _wayfinding_domain(entries_by_venue: dict[str, list[dict]] | None = None) -> IndoorWayfindingDomain:
    index = VenueDirectoryIndex(build_directory_json(entries_by_venue or {}))
    return IndoorWayfindingDomain(VenueDirectoryConfig(venue_id="venue-a", directory_data_url=None), index)


def _orchestrator(domain: IndoorWayfindingDomain) -> TaskOrchestrator:
    grounding = GroundingAgent(domain)
    db = FakeFirestoreClient()
    planner_response = json.dumps({
        "description": "Head that way", "action_type": "guidance",
        "requires_confirmation": False, "category": "wayfinding-guidance",
    })
    return TaskOrchestrator(
        perception=PerceptionAgent(),
        router=DomainRouterAgent(FakeLlmAgentRunner(), domains=[domain]),
        grounding_agents={domain.domain_id: grounding},
        domains={domain.domain_id: domain},
        planner=PlannerAgent(FakeLlmAgentRunner(next_response=planner_response)),
        guardrail=GuardrailAgent(),
        replanning=ReplanningAgent(),
        guidance=GuidanceAgent(FakeLlmAgentRunner(next_response="Head that way.")),
        memory=MemoryAgent(db),
        escalation=EscalationAgent(db, _FakePublisher(), LoggingNotificationSender()),
    )


@pytest.mark.asyncio
async def test_e2e_directory_backed_grounding_mode() -> None:
    """DoD #1, directory-backed path: a venue with published directory data
    resolves a goal to the correct location on the first ground() call, no
    scene signal needed."""
    entries = {"venue-a": [{"target": "breakfast room", "value": "Level 2, East Wing"}]}
    domain = _wayfinding_domain(entries)
    orchestrator = _orchestrator(domain)

    goal = PerceivedGoal(session_id="s1", uid="u1", raw_text="where's the breakfast room")
    result = await orchestrator.handle_goal(goal)

    assert result.guidance.text
    active = orchestrator._active["s1"]
    assert active.fact.value == "Level 2, East Wing"
    assert active.fact.source == "venue_directory"
    assert active.fact.confidence == 1.0


@pytest.mark.asyncio
async def test_e2e_signage_only_grounding_mode_via_scene_signal() -> None:
    """DoD #1, signage-only path: no directory data at all; the fact only
    becomes correct after a scene signal triggers the divergence/replan
    path (Task 7's round trip), now exercised through the full agent
    stack rather than a hand-built orchestrator."""
    domain = _wayfinding_domain()  # no directory data anywhere
    orchestrator = _orchestrator(domain)

    goal = PerceivedGoal(session_id="s1", uid="u1", raw_text="where's the breakfast room")
    initial = await orchestrator.handle_goal(goal)
    assert initial.guidance.text
    assert orchestrator._active["s1"].fact.value == "unknown"

    signal = SceneSignal(session_id="s1", kind="signage_text", text="Room 204", confidence=0.9)
    replanned = await orchestrator.handle_scene_signal(signal)

    assert replanned is not None
    assert replanned.guidance.haptic_pattern == "pattern-urgent"
    active = orchestrator._active["s1"]
    assert active.fact.value == "Room 204"
    assert active.fact.source == "signage_only"


@pytest.mark.asyncio
async def test_e2e_router_disambiguates_gate_between_transit_and_wayfinding() -> None:
    """"Gate" is a keyword in both TransitDomain's stop_name_keywords and
    IndoorWayfindingDomain's own keyword list — deliberately, per the same
    precedent as two transit feeds both matching a generic goal (see
    app/domains/transit/config.py's own comment). Both domains' matches()
    return True; DomainRouterAgent's LLM disambiguation step is the actual
    classifier, proving the collision is handled, not silently broken."""
    static_index = GtfsStaticIndex(build_static_feed_zip(
        [{"stop_id": "s1", "stop_name": "Central Station", "platform_code": "3", "parent_station": ""}],
        [{"trip_id": "t1", "stop_id": "s1", "arrival_time": "09:00:00", "stop_sequence": "1"}],
    ))
    transit = TransitDomain(
        TransitFeedConfig(
            domain_id="transit-ch", display_name="x", static_feed_url="", realtime_feed_url="",
            auth_header=None, locale="en-US",
        ),
        static_index, poller=None,  # matches()-only test, ground() never called
    )
    wayfinding = _wayfinding_domain()

    runner = FakeLlmAgentRunner(next_response="indoor_wayfinding")
    router = DomainRouterAgent(runner, domains=[transit, wayfinding])

    domain_id = await router.route(PerceivedGoal(session_id="s1", uid="u1", raw_text="take me to the gate"))

    assert domain_id == "indoor_wayfinding"
    assert len(runner.calls) == 1  # both matched — the LLM step was actually needed, not skipped
