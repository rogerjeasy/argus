import pytest

from app.agents.audio_perception import AudioPerceptionAgent
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
from app.domains.stub import FakeGroundingSource, StubDomain
from app.models.agent_events import PerceivedGoal
from app.tests.doubles.fake_audio_classifier import FakeAudioClassifier
from app.tests.doubles.fake_firestore import FakeFirestoreClient
from app.tests.doubles.fake_llm_runner import FakeLlmAgentRunner


class _FakePublisher:
    def publish(self, topic_path, data):
        class _F:
            def result(self):
                return "id"
        return _F()

    def topic_path(self, project, topic):
        return f"projects/{project}/topics/{topic}"


def _orchestrator() -> TaskOrchestrator:
    source = FakeGroundingSource()
    source.set_answer("platform", "4")
    stub = StubDomain(source)
    db = FakeFirestoreClient()
    return TaskOrchestrator(
        perception=PerceptionAgent(),
        router=DomainRouterAgent(FakeLlmAgentRunner(), domains=[stub]),
        grounding_agents={"stub": GroundingAgent(stub)},
        domains={"stub": stub},
        planner=PlannerAgent(FakeLlmAgentRunner(next_response='{"description":"x","action_type":"guidance","requires_confirmation":false,"category":"stub-guidance"}')),
        guardrail=GuardrailAgent(),
        replanning=ReplanningAgent(),
        guidance=GuidanceAgent(FakeLlmAgentRunner(next_response="ok")),
        memory=MemoryAgent(db),
        escalation=EscalationAgent(db, _FakePublisher(), LoggingNotificationSender()),
    )


@pytest.mark.asyncio
async def test_spoken_distress_alone_never_escalates() -> None:
    """Red-team case (design doc §9): the keyword signal alone must not
    trigger — the real goal must still be routed normally."""
    orch = _orchestrator()

    result = await orch.handle_goal(PerceivedGoal(session_id="s1", uid="u1", raw_text="help me, I fell"))

    assert result.guardrail.step_id != "distress-escalation"


@pytest.mark.asyncio
async def test_ambient_sound_alone_never_escalates() -> None:
    """Red-team case (design doc §9 / DoD #3): the ambient classification
    alone — with no corroborating spoken signal — must not trigger."""
    orch = _orchestrator()
    classifier = FakeAudioClassifier(result="distress_utterance")
    agent = AudioPerceptionAgent(classifier)

    category = await agent.classify_ambient_sound(b"audio")
    result = await orch.handle_ambient_sound_signal("s1", "u1", category)

    assert result is None


@pytest.mark.asyncio
async def test_spoken_distress_then_ambient_sound_within_the_window_escalates() -> None:
    orch = _orchestrator()
    classifier = FakeAudioClassifier(result="alarm")
    agent = AudioPerceptionAgent(classifier)

    keyword_result = await orch.handle_goal(PerceivedGoal(session_id="s1", uid="u1", raw_text="help me please"))
    assert keyword_result.guardrail.step_id != "distress-escalation"  # only one signal so far

    category = await agent.classify_ambient_sound(b"audio")
    ambient_result = await orch.handle_ambient_sound_signal("s1", "u1", category)

    assert ambient_result is not None
    assert ambient_result.guardrail.step_id == "distress-escalation"
    assert ambient_result.guidance.text  # non-empty spoken response
