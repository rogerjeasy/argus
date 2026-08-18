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
from app.domains import DomainPlugin
from app.domains.indoor_wayfinding.config import VenueDirectoryConfig
from app.domains.indoor_wayfinding.directory_index import VenueDirectoryIndex
from app.domains.indoor_wayfinding.domain import IndoorWayfindingDomain
from app.domains.stub import FakeGroundingSource, StubDomain
from app.models.agent_events import PerceivedGoal, SceneSignal
from app.tests.doubles.fake_firestore import FakeFirestoreClient
from app.tests.doubles.fake_llm_runner import FakeLlmAgentRunner
from app.tests.fixtures.venue_directory_builders import build_directory_json


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


def _build_orchestrator_for_domain(domain: DomainPlugin, *, planner_response: str) -> TaskOrchestrator:
    """Sibling to _build_orchestrator above — that one is hardcoded to
    StubDomain; this one takes any already-constructed domain plugin, for
    tests that need a specific real domain's own ground()/matches()
    behavior (e.g. IndoorWayfindingDomain's signage-only mode) rather than
    FakeGroundingSource's settable-per-test answers."""
    router_runner = FakeLlmAgentRunner()  # single candidate — never actually called
    planner_runner = FakeLlmAgentRunner(next_response=planner_response)
    guidance_runner = FakeLlmAgentRunner(next_response="Head that way.")

    grounding = GroundingAgent(domain)
    db = FakeFirestoreClient()
    return TaskOrchestrator(
        perception=PerceptionAgent(),
        router=DomainRouterAgent(router_runner, domains=[domain]),
        grounding_agents={domain.domain_id: grounding},
        domains={domain.domain_id: domain},
        planner=PlannerAgent(planner_runner),
        guardrail=GuardrailAgent(),
        replanning=ReplanningAgent(),
        guidance=GuidanceAgent(guidance_runner),
        memory=MemoryAgent(db),
        escalation=EscalationAgent(db, _FakePublisher(), LoggingNotificationSender()),
    )


def _planner_json(category: str = "stub-guidance", provider: str | None = None) -> str:
    import json
    payload = {
        "description": "Head to platform 4",
        "action_type": "guidance",
        "requires_confirmation": False,
        "category": category,
    }
    if provider is not None:
        payload["provider"] = provider
    return json.dumps(payload)


class _RecordingExecutor:
    def __init__(self) -> None:
        self.received_payloads: list[dict] = []

    async def execute(self, payload: dict) -> dict:
        self.received_payloads.append(payload)
        return {"step_id": "x", "status": "success", "structured_data": {}, "summary_text": "done"}


async def _confirm_orchestrator(*, category: str, provider: str) -> tuple[TaskOrchestrator, str]:
    """Real gap this plan's own research found while executing Task 2:
    resolve_confirmation is only ever reachable via handle_document_signal's
    _gate_and_respond tail — handle_goal alone never populates
    _pending_input, since StubDomain/TransitDomain have no executors and
    their own requires_confirmation decision is purely informational (see
    handle_goal's body: it records _active and returns, it never checks
    decision.decision at all). A StubDomain + handle_goal-only test (this
    helper's first draft) can therefore never reach resolve_confirmation's
    populated-pending state — this rebuilds the real PersonalAdminDomain +
    handle_document_signal pattern test_e2e_personal_admin.py already
    establishes, the only path that actually reaches it, adapted to a
    parametrized category/provider. Returns (orchestrator, step_id)."""
    import json

    from app.agents.memory import PersonalAdminProfile, ProviderContact
    from app.domains.personal_admin.domain import PersonalAdminDomain
    from app.models.agent_events import SceneSignal

    triage_response = json.dumps({"category": category, "urgency": "normal", "subflow": "call", "confidence": 0.9})
    triage_runner = FakeLlmAgentRunner(next_response=triage_response)
    guardrail = GuardrailAgent()
    db = FakeFirestoreClient()
    memory = MemoryAgent(db, kms=None)
    await memory.update_profile("u1", PersonalAdminProfile(
        known_providers=[ProviderContact(name=provider, phone_number="+15559990000", category=category)]
    ))

    domain = PersonalAdminDomain(triage_runner, memory, guardrail)
    domain.executors["call"] = _RecordingExecutor()

    planner_response = json.dumps({
        "description": f"call {provider}", "action_type": "execute",
        "requires_confirmation": False, "category": category,
    })
    orchestrator = TaskOrchestrator(
        perception=PerceptionAgent(),
        router=DomainRouterAgent(FakeLlmAgentRunner(), domains=[domain]),
        grounding_agents={"personal_admin": GroundingAgent(domain)},
        domains={"personal_admin": domain},
        planner=PlannerAgent(FakeLlmAgentRunner(next_response=planner_response)),
        guardrail=guardrail,
        replanning=ReplanningAgent(),
        guidance=GuidanceAgent(FakeLlmAgentRunner(next_response="unused")),
        memory=memory,
        escalation=EscalationAgent(db, _FakePublisher(), LoggingNotificationSender()),
    )

    await orchestrator.handle_goal(PerceivedGoal(session_id="s1", uid="u1", raw_text="deal with this"))
    signal = SceneSignal(session_id="s1", kind="signage_text", text=f"{provider} notice", confidence=0.9)
    triage_result = await orchestrator.handle_document_signal(signal)
    assert triage_result is not None
    assert triage_result.guardrail.decision == "requires_confirmation"

    return orchestrator, triage_result.guardrail.step_id


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


@pytest.mark.asyncio
async def test_handle_document_signal_with_inform_only_subflow_never_grounds_or_executes() -> None:
    from app.domains.personal_admin.models import TriageResult

    class _InformOnlyDomain(_FakePersonalAdminDomain):
        async def ground(self, request):
            # handle_goal() itself grounds once first (Phase 1's hardcoded
            # "platform" key, unrelated to document triage) before
            # handle_document_signal ever runs — only a grounding call keyed
            # on the triage category (what the inform-only branch must never
            # make) is the thing under test here.
            if request.key == "platform":
                from datetime import datetime, timezone
                from app.models.agent_events import GroundedFact
                return GroundedFact(key="platform", value="4", source="test", confidence=1.0, as_of=datetime.now(timezone.utc))
            raise AssertionError("ground() must never be called for an inform-only subflow")

    executor = _FakeExecutor({"step_id": "s1", "status": "success", "structured_data": {}, "summary_text": "unused"})
    domain = _InformOnlyDomain(
        triage_result=TriageResult(category="junk", urgency="low", subflow="inform-only", confidence=0.9),
        fact=None, executors={"call": executor},
    )
    router_runner = FakeLlmAgentRunner()
    db = FakeFirestoreClient()
    orch = TaskOrchestrator(
        perception=PerceptionAgent(), router=DomainRouterAgent(router_runner, domains=[domain]),
        grounding_agents={"personal_admin": GroundingAgent(domain)}, domains={"personal_admin": domain},
        # handle_goal() itself calls plan() once (its own initial-plan step,
        # unrelated to document triage) before handle_document_signal ever
        # runs, so this needs a real scripted JSON response too.
        planner=PlannerAgent(FakeLlmAgentRunner(next_response=_planner_json_for("personal_admin"))),
        guardrail=GuardrailAgent(), replanning=ReplanningAgent(),
        guidance=GuidanceAgent(FakeLlmAgentRunner(next_response="unused")),
        memory=MemoryAgent(db), escalation=EscalationAgent(db, _FakePublisher(), LoggingNotificationSender()),
    )
    goal = PerceivedGoal(session_id="sess-1", uid="user-1", raw_text="deal with this piece of mail")
    await orch.handle_goal(goal)
    signal = SceneSignal(session_id="sess-1", kind="signage_text", text="You may already be a winner!", confidence=0.9)

    result = await orch.handle_document_signal(signal)

    assert result is not None
    assert result.guardrail.decision == "approved"
    assert executor.received_payloads == []


class _FakePersonalAdminDomainWithPayload(_FakePersonalAdminDomain):
    def __init__(self, *, triage_result, fact, executors: dict, payload_extra: dict) -> None:
        super().__init__(triage_result=triage_result, fact=fact, executors=executors)
        self._payload_extra = payload_extra

    async def build_executor_payload(self, step, fact, triage_result, uid, signal=None):
        payload = dict(step.payload)
        payload["step_id"] = step.step_id
        payload["executor"] = "form"
        payload.update(self._payload_extra)
        return payload


def _form_orchestrator(*, payload_extra: dict, executor_outcome: dict | None = None):
    from datetime import datetime, timezone

    from app.domains.personal_admin.models import TriageResult
    from app.models.agent_events import GroundedFact

    triage_result = TriageResult(category="medical", urgency="normal", subflow="form", confidence=0.9)
    fact = GroundedFact(key="medical", value="form", source="user_profile", confidence=1.0, as_of=datetime.now(timezone.utc))
    executor = _FakeExecutor(executor_outcome or {"step_id": "s1", "status": "success", "structured_data": {}, "summary_text": "Form submitted."})
    domain = _FakePersonalAdminDomainWithPayload(
        triage_result=triage_result, fact=fact, executors={"form": executor}, payload_extra=payload_extra
    )

    router_runner = FakeLlmAgentRunner()
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


@pytest.mark.asyncio
async def test_handle_document_signal_pauses_for_one_missing_form_field() -> None:
    orch, executor = _form_orchestrator(payload_extra={
        "fields": [
            {"name": "full_name", "label": "Full name", "value": "Jordan Rivera", "source": "memory_profile"},
            {"name": "policy_number", "label": "Policy number", "value": None, "source": "unresolved"},
        ],
        "missing_field": "policy_number", "unresolved_field_count": 1,
    })
    goal = PerceivedGoal(session_id="sess-1", uid="user-1", raw_text="deal with this form")
    await orch.handle_goal(goal)
    signal = SceneSignal(session_id="sess-1", kind="form_schema", text="Insurance Claim Form", confidence=0.9)

    result = await orch.handle_document_signal(signal)

    assert result is not None
    assert result.guardrail.decision == "requires_field_input"
    assert result.guardrail.field_label == "Policy number"
    assert executor.received_payloads == []  # never executed before the field is resolved


@pytest.mark.asyncio
async def test_resolve_field_input_injects_value_and_proceeds_to_confirmation_gate() -> None:
    orch, executor = _form_orchestrator(payload_extra={
        "fields": [{"name": "policy_number", "label": "Policy number", "value": None, "source": "unresolved"}],
        "missing_field": "policy_number", "unresolved_field_count": 1,
    })
    goal = PerceivedGoal(session_id="sess-1", uid="user-1", raw_text="deal with this form")
    await orch.handle_goal(goal)
    signal = SceneSignal(session_id="sess-1", kind="form_schema", text="Insurance Claim Form", confidence=0.9)
    await orch.handle_document_signal(signal)

    result = await orch.resolve_field_input("sess-1", "user-1", "POL-12345")

    assert result is not None
    # No standing permission seeded — resolving the field re-enters at
    # Guardrail, which still requires the normal confirm-before-submit gate.
    assert result.guardrail.decision == "requires_confirmation"
    assert executor.received_payloads == []


@pytest.mark.asyncio
async def test_resolve_field_input_then_confirmation_executes_with_the_resolved_value() -> None:
    orch, executor = _form_orchestrator(payload_extra={
        "fields": [{"name": "policy_number", "label": "Policy number", "value": None, "source": "unresolved"}],
        "missing_field": "policy_number", "unresolved_field_count": 1,
    })
    goal = PerceivedGoal(session_id="sess-1", uid="user-1", raw_text="deal with this form")
    await orch.handle_goal(goal)
    signal = SceneSignal(session_id="sess-1", kind="form_schema", text="Insurance Claim Form", confidence=0.9)
    await orch.handle_document_signal(signal)
    await orch.resolve_field_input("sess-1", "user-1", "POL-12345")

    result = await orch.resolve_confirmation("sess-1", "user-1", accepted=True)

    assert result is not None
    assert result.guardrail.decision == "approved"
    assert executor.received_payloads[0]["fields"][0]["value"] == "POL-12345"
    assert executor.received_payloads[0]["fields"][0]["source"] == "user_provided"


@pytest.mark.asyncio
async def test_a_spoken_answer_resolves_a_pending_field_request_not_a_new_goal() -> None:
    orch, executor = _form_orchestrator(payload_extra={
        "fields": [{"name": "policy_number", "label": "Policy number", "value": None, "source": "unresolved"}],
        "missing_field": "policy_number", "unresolved_field_count": 1,
    })
    goal = PerceivedGoal(session_id="sess-1", uid="user-1", raw_text="deal with this form")
    await orch.handle_goal(goal)
    signal = SceneSignal(session_id="sess-1", kind="form_schema", text="Insurance Claim Form", confidence=0.9)
    await orch.handle_document_signal(signal)

    result = await orch.handle_goal(PerceivedGoal(session_id="sess-1", uid="user-1", raw_text="POL-12345"))

    assert result.guardrail.decision == "requires_confirmation"
    assert executor.received_payloads == []


@pytest.mark.asyncio
async def test_more_than_one_missing_field_is_denied_not_paused() -> None:
    orch, executor = _form_orchestrator(payload_extra={
        "fields": [
            {"name": "policy_number", "label": "Policy number", "value": None, "source": "unresolved"},
            {"name": "employer_name", "label": "Employer name", "value": None, "source": "unresolved"},
        ],
        "missing_field": None, "unresolved_field_count": 2,
    })
    goal = PerceivedGoal(session_id="sess-1", uid="user-1", raw_text="deal with this form")
    await orch.handle_goal(goal)
    signal = SceneSignal(session_id="sess-1", kind="form_schema", text="Insurance Claim Form", confidence=0.9)

    result = await orch.handle_document_signal(signal)

    assert result is not None
    assert result.guardrail.decision == "denied"
    assert executor.received_payloads == []
    # Nothing was left pending — a subsequent resolve call (of either kind)
    # has nothing to resolve, proving this path pauses neither mode.
    assert await orch.resolve_confirmation("sess-1", "user-1", accepted=True) is None
    assert await orch.resolve_field_input("sess-1", "user-1", "anything") is None


@pytest.mark.asyncio
async def test_resolve_field_input_with_no_pending_field_request_returns_none() -> None:
    orch, _ = _form_orchestrator(payload_extra={"fields": [], "missing_field": None, "unresolved_field_count": 0})

    assert await orch.resolve_field_input("no-such-session", "user-1", "anything") is None


@pytest.mark.asyncio
async def test_resolve_confirmation_ignores_a_pending_field_request() -> None:
    """A pending field_request is not a pending confirmation — the wrong
    resolver must not clear or answer it."""
    orch, executor = _form_orchestrator(payload_extra={
        "fields": [{"name": "policy_number", "label": "Policy number", "value": None, "source": "unresolved"}],
        "missing_field": "policy_number", "unresolved_field_count": 1,
    })
    goal = PerceivedGoal(session_id="sess-1", uid="user-1", raw_text="deal with this form")
    await orch.handle_goal(goal)
    signal = SceneSignal(session_id="sess-1", kind="form_schema", text="Insurance Claim Form", confidence=0.9)
    await orch.handle_document_signal(signal)

    result = await orch.resolve_confirmation("sess-1", "user-1", accepted=True)

    assert result is None
    assert executor.received_payloads == []


@pytest.mark.asyncio
async def test_handle_scene_signal_resolves_a_signage_only_fact_via_replan() -> None:
    # A full round trip proving BOTH grounding.ground() calls inside
    # check_for_divergence receive scene_signal_text — see Task 7's plan
    # notes on why threading only the replan() call is insufficient.
    domain = IndoorWayfindingDomain(
        VenueDirectoryConfig(venue_id="venue-a", directory_data_url=None),
        VenueDirectoryIndex(build_directory_json({})),  # signage-only mode
    )
    orchestrator = _build_orchestrator_for_domain(domain, planner_response=_planner_json(category="wayfinding"))
    goal = PerceivedGoal(session_id="s1", uid="u1", raw_text="where's the breakfast room")
    await orchestrator.handle_goal(goal)

    signal = SceneSignal(session_id="s1", kind="signage_text", text="Breakfast Room this way", confidence=0.9)
    result = await orchestrator.handle_scene_signal(signal)

    assert result is not None
    active = orchestrator._active["s1"]
    assert active.fact.value == "Breakfast Room this way"
    assert active.fact.source == "signage_only"


@pytest.mark.asyncio
async def test_resolve_confirmation_declined_records_a_denied_outcome() -> None:
    orch, step_id = await _confirm_orchestrator(category="pharmacy_refill", provider="cvs-main-st")

    await orch.resolve_confirmation("s1", "u1", accepted=False)

    history = await orch._memory.get_confirmation_history("u1", category="pharmacy_refill", provider="cvs-main-st")
    assert len(history) == 1
    assert history[0].decision == "denied"


@pytest.mark.asyncio
async def test_resolve_confirmation_accepted_records_an_approved_outcome() -> None:
    orch, step_id = await _confirm_orchestrator(category="pharmacy_refill", provider="cvs-main-st")

    await orch.resolve_confirmation("s1", "u1", accepted=True)

    history = await orch._memory.get_confirmation_history("u1", category="pharmacy_refill", provider="cvs-main-st")
    assert len(history) == 1
    assert history[0].decision == "approved"


@pytest.mark.asyncio
async def test_check_for_pending_calibration_proposal_offers_it_as_a_confirmation() -> None:
    """Uses the file's plain _build_orchestrator (StubDomain-based), not
    _confirm_orchestrator — the "calibration" pending mode is set directly
    by check_for_pending_calibration_proposal itself, independent of any
    domain's own confirm flow, so the lightweight existing helper is both
    sufficient and the correct-weight tool here (see the note on
    _confirm_orchestrator's own real-PersonalAdminDomain requirement)."""
    from app.agents.calibration import CalibrationProposal

    source = FakeGroundingSource()
    source.set_answer("platform", "4")
    orch = _build_orchestrator(source, planner_response=_planner_json())
    proposal = CalibrationProposal(category="pharmacy_refill", provider="cvs-main-st", evidence="approved 15/15 times")
    proposal_id = await orch._memory.store_calibration_proposal("u1", proposal)

    result = await orch.check_for_pending_calibration_proposal("s1", "u1")

    assert result is not None
    assert result.guardrail.decision == "requires_confirmation"
    assert result.guardrail.step_id == proposal_id
    assert "pharmacy_refill" in result.guidance.text or "15/15" in result.guidance.text


@pytest.mark.asyncio
async def test_check_for_pending_calibration_proposal_returns_none_when_nothing_pending() -> None:
    source = FakeGroundingSource()
    source.set_answer("platform", "4")
    orch = _build_orchestrator(source, planner_response=_planner_json())

    assert await orch.check_for_pending_calibration_proposal("s1", "u1") is None
