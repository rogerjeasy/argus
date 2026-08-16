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
from app.domains.stub import FakeGroundingSource, StubDomain
from app.models.agent_events import PerceivedGoal, SceneSignal
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


def _build_orchestrator(source: FakeGroundingSource, *, planner_response: str) -> TaskOrchestrator:
    stub = StubDomain(source)
    router_runner = FakeLlmAgentRunner()  # single candidate — never actually called
    planner_runner = FakeLlmAgentRunner(next_response=planner_response)
    guidance_runner = FakeLlmAgentRunner(next_response="Head to the platform.")

    grounding = GroundingAgent(stub)
    db = FakeFirestoreClient()
    return TaskOrchestrator(
        perception=PerceptionAgent(),
        router=DomainRouterAgent(router_runner, domains=[stub]),
        grounding_agents={"stub": grounding},
        domains={"stub": stub},
        planner=PlannerAgent(planner_runner),
        guardrail=GuardrailAgent(),
        replanning=ReplanningAgent(),
        guidance=GuidanceAgent(guidance_runner),
        memory=MemoryAgent(db),
        escalation=EscalationAgent(db, _FakePublisher(), LoggingNotificationSender()),
    )


def _planner_json(category: str = "stub-guidance") -> str:
    import json
    return json.dumps({
        "description": "Head to platform 4",
        "action_type": "guidance",
        "requires_confirmation": False,
        "category": category,
    })


@pytest.mark.asyncio
async def test_handle_goal_returns_guidance_gated_by_guardrail() -> None:
    source = FakeGroundingSource()
    source.set_answer("platform", "4")
    orchestrator = _build_orchestrator(source, planner_response=_planner_json())

    goal = PerceivedGoal(session_id="s1", uid="u1", raw_text="get me to platform 4")
    result = await orchestrator.handle_goal(goal)

    assert result.guidance.text == "Head to the platform."
    # No standing permission seeded — first-time category always requires confirmation.
    assert result.guardrail.decision == "requires_confirmation"


@pytest.mark.asyncio
async def test_divergence_triggers_autonomous_replan_with_updated_guidance() -> None:
    source = FakeGroundingSource()
    source.set_answer("platform", "4")
    orchestrator = _build_orchestrator(source, planner_response=_planner_json())

    goal = PerceivedGoal(session_id="s1", uid="u1", raw_text="get me to platform 4")
    await orchestrator.handle_goal(goal)

    # Reality changes mid-task.
    source.set_answer("platform", "7")

    result = await orchestrator.check_for_divergence(session_id="s1", uid="u1")

    assert result is not None
    assert result.guidance.text == "Head to the platform."  # re-shaped from the updated fact


@pytest.mark.asyncio
async def test_check_for_divergence_returns_none_when_nothing_changed() -> None:
    source = FakeGroundingSource()
    source.set_answer("platform", "4")
    orchestrator = _build_orchestrator(source, planner_response=_planner_json())

    goal = PerceivedGoal(session_id="s1", uid="u1", raw_text="get me to platform 4")
    await orchestrator.handle_goal(goal)

    result = await orchestrator.check_for_divergence(session_id="s1", uid="u1")

    assert result is None


@pytest.mark.asyncio
async def test_bounded_replan_escalates_instead_of_looping_forever() -> None:
    source = FakeGroundingSource()
    source.set_answer("platform", "4")
    orchestrator = _build_orchestrator(source, planner_response=_planner_json())

    goal = PerceivedGoal(session_id="s1", uid="u1", raw_text="get me to platform 4")
    await orchestrator.handle_goal(goal)

    # Every replan attempt gets contradicted again — never converges.
    for i in range(MAX_REPLAN_ATTEMPTS + 1):
        source.set_answer("platform", str(i))
        result = await orchestrator.check_for_divergence(session_id="s1", uid="u1")

    assert result is not None
    assert result.guardrail.decision == "denied"
    assert "escalat" in result.guidance.text.lower()
    assert result.guidance.earcon == "earcon-escalation"


@pytest.mark.asyncio
async def test_handle_scene_signal_triggers_replan_when_feed_confirms_the_camera() -> None:
    from app.models.agent_events import SceneSignal

    source = FakeGroundingSource()
    source.set_answer("platform", "4")
    orchestrator = _build_orchestrator(source, planner_response=_planner_json())

    goal = PerceivedGoal(session_id="s1", uid="u1", raw_text="get me to platform 4")
    await orchestrator.handle_goal(goal)

    # The camera and the feed now agree the plan is stale.
    source.set_answer("platform", "7")
    signal = SceneSignal(session_id="s1", kind="signage_text", text="Platform 7", confidence=0.9)

    result = await orchestrator.handle_scene_signal(signal)

    assert result is not None
    assert result.guidance.haptic_pattern == "pattern-urgent"


@pytest.mark.asyncio
async def test_handle_scene_signal_does_nothing_when_the_feed_disagrees_with_the_camera() -> None:
    from app.models.agent_events import SceneSignal

    source = FakeGroundingSource()
    source.set_answer("platform", "4")
    orchestrator = _build_orchestrator(source, planner_response=_planner_json())

    goal = PerceivedGoal(session_id="s1", uid="u1", raw_text="get me to platform 4")
    await orchestrator.handle_goal(goal)

    # Camera claims platform 7, but the real feed (tie-breaker) still says 4
    # — a noisy/wrong camera read must not override it.
    signal = SceneSignal(session_id="s1", kind="signage_text", text="Platform 7", confidence=0.9)

    result = await orchestrator.handle_scene_signal(signal)

    assert result is None


@pytest.mark.asyncio
async def test_handle_scene_signal_ignores_a_low_confidence_signal_without_ever_regrounding() -> None:
    from app.models.agent_events import SceneSignal

    source = FakeGroundingSource()
    source.set_answer("platform", "4")
    orchestrator = _build_orchestrator(source, planner_response=_planner_json())

    goal = PerceivedGoal(session_id="s1", uid="u1", raw_text="get me to platform 4")
    await orchestrator.handle_goal(goal)

    signal = SceneSignal(session_id="s1", kind="signage_text", text="Platform 7", confidence=0.1)

    result = await orchestrator.handle_scene_signal(signal)

    assert result is None


@pytest.mark.asyncio
async def test_handle_scene_signal_for_an_unknown_session_returns_none() -> None:
    from app.models.agent_events import SceneSignal

    orchestrator = _build_orchestrator(FakeGroundingSource(), planner_response=_planner_json())
    signal = SceneSignal(session_id="never-started", kind="signage_text", text="Platform 7", confidence=0.9)

    assert await orchestrator.handle_scene_signal(signal) is None


class _FakeExecutor:
    def __init__(self, outcome: dict) -> None:
        self.outcome = outcome
        self.received_payloads: list[dict] = []

    async def execute(self, payload: dict) -> dict:
        self.received_payloads.append(payload)
        return self.outcome


class _FakePersonalAdminDomain:
    domain_id = "personal_admin"

    def __init__(self, *, triage_result, fact, executors: dict) -> None:
        self._triage_result = triage_result
        self._fact = fact
        self.executors = executors

    def matches(self, goal_text: str) -> bool:
        return "mail" in goal_text or "deal with" in goal_text

    async def triage(self, signal):
        return self._triage_result

    async def ground(self, request):
        return self._fact


def _personal_admin_orchestrator(*, executor_outcome: dict, requires_confirmation: bool):
    from app.domains.personal_admin.models import TriageResult
    from app.models.agent_events import GroundedFact
    from datetime import datetime, timezone

    triage_result = TriageResult(category="pharmacy_refill_under_20", urgency="normal", subflow="call", confidence=0.9)
    fact = GroundedFact(
        key="pharmacy_refill_under_20", value="+15551234567", source="user_profile",
        confidence=1.0 if not requires_confirmation else 0.9, as_of=datetime.now(timezone.utc),
    )
    executor = _FakeExecutor(executor_outcome)
    domain = _FakePersonalAdminDomain(triage_result=triage_result, fact=fact, executors={"call": executor})

    router_runner = FakeLlmAgentRunner()  # single candidate — never actually called
    planner_runner = FakeLlmAgentRunner(next_response=_planner_json_for("personal_admin"))
    guidance_runner = FakeLlmAgentRunner(next_response="__ECHO_STEP_DESCRIPTION__")
    grounding = GroundingAgent(domain)
    db = FakeFirestoreClient()
    orch = TaskOrchestrator(
        perception=PerceptionAgent(),
        router=DomainRouterAgent(router_runner, domains=[domain]),
        grounding_agents={"personal_admin": grounding},
        domains={"personal_admin": domain},
        planner=PlannerAgent(planner_runner),
        guardrail=GuardrailAgent(),
        replanning=ReplanningAgent(),
        guidance=_EchoingGuidanceAgent(guidance_runner),
        memory=MemoryAgent(db),
        escalation=EscalationAgent(db, _FakePublisher(), LoggingNotificationSender()),
    )
    return orch, executor


def _planner_json_for(category: str) -> str:
    import json
    return json.dumps({
        "description": "call the pharmacy to confirm refill status",
        "action_type": "execute",
        "requires_confirmation": False,
        "category": category,
    })


class _EchoingGuidanceAgent(GuidanceAgent):
    """shape() normally phrases a PlanStep's description via the LLM
    runner — these tests care about the *executor outcome's* summary_text
    reaching Guidance verbatim (design doc §4a's report-back path), so this
    subclass echoes step.description unchanged instead of going through a
    FakeLlmAgentRunner's scripted response, which would otherwise return
    the same fixed string for every call regardless of which step it was
    asked to shape."""

    async def shape(self, session_id, uid, step, *, urgent: bool = False):
        from app.models.agent_events import GuidanceOutput
        return GuidanceOutput(
            session_id=session_id, text=step.description,
            haptic_pattern="pattern-urgent" if urgent else "pattern-forward", earcon="earcon-plan-updated",
        )


@pytest.mark.asyncio
async def test_handle_document_signal_pauses_on_requires_confirmation() -> None:
    orch, executor = _personal_admin_orchestrator(
        executor_outcome={"step_id": "s1", "status": "success", "structured_data": {}, "summary_text": "done"},
        requires_confirmation=True,
    )
    goal = PerceivedGoal(session_id="sess-1", uid="user-1", raw_text="deal with this piece of mail")
    await orch.handle_goal(goal)
    signal = SceneSignal(session_id="sess-1", kind="signage_text", text="Example Pharmacy refill notice", confidence=0.9)

    result = await orch.handle_document_signal(signal)

    assert result is not None
    assert result.guardrail.decision == "requires_confirmation"
    assert executor.received_payloads == []  # never executed before confirmation


@pytest.mark.asyncio
async def test_resolve_confirmation_accepted_executes_and_reports_success() -> None:
    orch, executor = _personal_admin_orchestrator(
        executor_outcome={"step_id": "s1", "status": "success", "structured_data": {"copay_cents": 1200}, "summary_text": "Refill confirmed, ready tomorrow."},
        requires_confirmation=True,
    )
    goal = PerceivedGoal(session_id="sess-1", uid="user-1", raw_text="deal with this piece of mail")
    await orch.handle_goal(goal)
    signal = SceneSignal(session_id="sess-1", kind="signage_text", text="Example Pharmacy refill notice", confidence=0.9)
    await orch.handle_document_signal(signal)

    result = await orch.resolve_confirmation("sess-1", "user-1", accepted=True)

    assert result is not None
    assert executor.received_payloads != []
    assert result.guardrail.decision == "approved"
    assert "Refill confirmed" in result.guidance.text


@pytest.mark.asyncio
async def test_resolve_confirmation_declined_never_executes() -> None:
    orch, executor = _personal_admin_orchestrator(
        executor_outcome={"step_id": "s1", "status": "success", "structured_data": {}, "summary_text": "done"},
        requires_confirmation=True,
    )
    goal = PerceivedGoal(session_id="sess-1", uid="user-1", raw_text="deal with this piece of mail")
    await orch.handle_goal(goal)
    signal = SceneSignal(session_id="sess-1", kind="signage_text", text="Example Pharmacy refill notice", confidence=0.9)
    await orch.handle_document_signal(signal)

    result = await orch.resolve_confirmation("sess-1", "user-1", accepted=False)

    assert result is not None
    assert executor.received_payloads == []
    assert result.guardrail.decision == "denied"


@pytest.mark.asyncio
async def test_resolve_confirmation_with_no_pending_step_returns_none() -> None:
    orch, _ = _personal_admin_orchestrator(
        executor_outcome={"step_id": "s1", "status": "success", "structured_data": {}, "summary_text": "done"},
        requires_confirmation=True,
    )

    assert await orch.resolve_confirmation("no-such-session", "user-1", accepted=True) is None


@pytest.mark.asyncio
async def test_handle_goal_treats_a_spoken_yes_as_confirmation_not_a_new_goal() -> None:
    orch, executor = _personal_admin_orchestrator(
        executor_outcome={"step_id": "s1", "status": "success", "structured_data": {}, "summary_text": "done"},
        requires_confirmation=True,
    )
    goal = PerceivedGoal(session_id="sess-1", uid="user-1", raw_text="deal with this piece of mail")
    await orch.handle_goal(goal)
    signal = SceneSignal(session_id="sess-1", kind="signage_text", text="Example Pharmacy refill notice", confidence=0.9)
    await orch.handle_document_signal(signal)

    result = await orch.handle_goal(PerceivedGoal(session_id="sess-1", uid="user-1", raw_text="yes"))

    assert executor.received_payloads != []
    assert result.guardrail.decision == "approved"


@pytest.mark.asyncio
async def test_failed_executor_outcome_is_reported_as_denied_not_silently_coerced() -> None:
    orch, executor = _personal_admin_orchestrator(
        executor_outcome={"step_id": "s1", "status": "failed", "structured_data": {}, "summary_text": "Could not place the call."},
        requires_confirmation=True,
    )
    goal = PerceivedGoal(session_id="sess-1", uid="user-1", raw_text="deal with this piece of mail")
    await orch.handle_goal(goal)
    signal = SceneSignal(session_id="sess-1", kind="signage_text", text="Example Pharmacy refill notice", confidence=0.9)
    await orch.handle_document_signal(signal)

    result = await orch.resolve_confirmation("sess-1", "user-1", accepted=True)

    assert result.guardrail.decision == "denied"


@pytest.mark.asyncio
async def test_malformed_executor_outcome_is_treated_as_failed() -> None:
    orch, executor = _personal_admin_orchestrator(
        executor_outcome={"status": "not-a-real-status"},  # missing required fields, invalid status
        requires_confirmation=True,
    )
    goal = PerceivedGoal(session_id="sess-1", uid="user-1", raw_text="deal with this piece of mail")
    await orch.handle_goal(goal)
    signal = SceneSignal(session_id="sess-1", kind="signage_text", text="Example Pharmacy refill notice", confidence=0.9)
    await orch.handle_document_signal(signal)

    result = await orch.resolve_confirmation("sess-1", "user-1", accepted=True)

    assert result.guardrail.decision == "denied"
