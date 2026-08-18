from dataclasses import dataclass

from pydantic import ValidationError

from app.agents.escalation import EscalationAgent
from app.agents.grounding import GroundingAgent
from app.agents.guardrail import GuardrailAgent
from app.agents.guidance import GuidanceAgent
from app.agents.memory import MemoryAgent
from app.agents.perception import PerceptionAgent
from app.agents.planner import PlannerAgent
from app.agents.replanning import ReplanningAgent
from app.agents.router import DomainRouterAgent
from app.core.telemetry import get_tracer
from app.domains import DomainPlugin
from app.domains.personal_admin.models import ExecutorOutcome
from app.models.agent_events import (
    GroundedFact, GuardrailDecision, GuidanceOutput, PerceivedGoal, PlanStep, SceneSignal,
)

tracer = get_tracer(__name__)

#: A conservative allowlist, not a full NLU intent classifier — anything not
#: a clear "yes" is treated as a decline, never a silent guess. Matches the
#: same "never guess on anything safety-adjacent" discipline the confidence
#: floor already enforces elsewhere.
_ACCEPT_PHRASES = {"yes", "yeah", "yep", "confirm", "confirmed", "go ahead", "do it", "sure", "okay", "ok"}


def _looks_like_acceptance(text: str) -> bool:
    normalized = text.strip().lower().rstrip(".!")
    return normalized in _ACCEPT_PHRASES or any(normalized.startswith(f"{w} ") for w in _ACCEPT_PHRASES)


@dataclass
class OrchestrationResult:
    guidance: GuidanceOutput
    guardrail: GuardrailDecision


@dataclass
class _ActiveTask:
    goal: PerceivedGoal
    domain_id: str
    grounding_key: str
    fact: GroundedFact
    step: PlanStep
    replan_attempts: int = 0


@dataclass
class _PendingInput:
    step: PlanStep
    uid: str
    domain_id: str
    mode: str  # "confirm" | "field_request"
    confidence: float
    field_name: str | None = None  # only set when mode == "field_request"


class TaskOrchestrator:
    """Drives the fixed sequence Perception → Router → Grounding → Planner →
    Guardrail → Guidance, with Grounding's divergence output short-circuiting
    into Replanning → Planner instead of proceeding. Sequencing lives here,
    in deterministic Python, specifically so Perception never talks directly
    to Guidance — every fact reaches the user through Grounding and Guardrail
    first, by construction, not by every LLM call being separately trusted
    to respect that rule.

    Note on scope: Phase 1 built `check_for_divergence` with no real trigger
    wired to it yet — a stub domain has no continuous scene signal to react
    to. `handle_scene_signal` (Phase 2b) is that trigger: the camera never
    talks to Guidance directly, it only ever earns the right to ask
    `check_for_divergence` to re-check the real feed, which remains the
    actual tie-breaker.

    Phase 3a adds a second kind of scene signal: a photographed document
    (`handle_document_signal`), dispatched via `hasattr(domain, "triage")`
    so Transit's own divergence flow is completely untouched. A step that
    requires confirmation now pauses in `_pending_input` instead of
    executing — `resolve_confirmation` (a spoken "yes"/"no" or a tapped
    button) is the only thing that can release it, and `handle_goal` checks
    for a pending confirmation before ever routing a new goal, so a spoken
    "yes" is never misrouted as a fresh, unrelated request.

    Phase 3b generalizes `_pending_input` to a second mode, "field_request":
    Form-Filling's one-missing-field ask needs a free-text answer, not a
    yes/no. Still exactly one pending thing per session — a form that needs
    both a field value and a confirmation pauses twice in sequence, sharing
    the same slot, never both modes at once. `resolve_field_input` mirrors
    `resolve_confirmation`'s shape; `_gate_and_respond` is the tail both the
    initial flow and a just-resolved field converge on.
    """

    def __init__(
        self,
        *,
        perception: PerceptionAgent,
        router: DomainRouterAgent,
        grounding_agents: dict[str, GroundingAgent],
        domains: dict[str, DomainPlugin],
        planner: PlannerAgent,
        guardrail: GuardrailAgent,
        replanning: ReplanningAgent,
        guidance: GuidanceAgent,
        memory: MemoryAgent,
        escalation: EscalationAgent,
    ) -> None:
        self._perception = perception
        self._router = router
        self._grounding_agents = grounding_agents
        self._domains = domains
        self._planner = planner
        self._guardrail = guardrail
        self._replanning = replanning
        self._guidance = guidance
        self._memory = memory
        self._escalation = escalation
        self._active: dict[str, _ActiveTask] = {}  # keyed by session_id
        self._pending_input: dict[str, _PendingInput] = {}  # keyed by session_id

    async def handle_goal(self, goal: PerceivedGoal) -> OrchestrationResult:
        pending = self._pending_input.get(goal.session_id)
        if pending is not None:
            if pending.mode == "confirm":
                resolved = await self.resolve_confirmation(
                    goal.session_id, goal.uid, _looks_like_acceptance(goal.raw_text)
                )
            else:
                # Any spoken utterance while a field_request is pending is
                # treated as the field's value, not a new goal (design doc
                # §4a.1's last bullet) — never run through
                # _looks_like_acceptance, which is confirm-mode-specific.
                resolved = await self.resolve_field_input(goal.session_id, goal.uid, goal.raw_text)
            if resolved is not None:
                return resolved

        with tracer.start_as_current_span("agent.handle_goal") as span:
            span.set_attribute("argus.session_id", goal.session_id)
            span.set_attribute("argus.uid", goal.uid)
            domain_id = await self._router.route(goal)
            span.set_attribute("argus.domain_id", domain_id)
            grounding = self._grounding_agents[domain_id]

            # Phase 1's stub domain only ever grounds one key; a real domain
            # (later phase) would derive this from the goal text.
            grounding_key = "platform"
            fact = await grounding.ground(grounding_key, goal.raw_text, goal.uid)

            step = await self._planner.plan(goal, [fact], domain_id=domain_id)
            permissions = await self._memory.get_standing_permissions(goal.uid)
            decision = self._guardrail.evaluate(step, fact.confidence, permissions)
            span.set_attribute("argus.guardrail_decision", decision.decision)
            guidance_output = await self._guidance.shape(goal.session_id, goal.uid, step)

            self._active[goal.session_id] = _ActiveTask(
                goal=goal, domain_id=domain_id, grounding_key=grounding_key, fact=fact, step=step
            )
            await self._memory.record_task_history(uid=goal.uid, session_id=goal.session_id, summary=step.description)

            return OrchestrationResult(guidance=guidance_output, guardrail=decision)

    async def check_for_divergence(
        self, *, session_id: str, uid: str, scene_signal_text: str = ""
    ) -> OrchestrationResult | None:
        active = self._active.get(session_id)
        if active is None:
            return None

        grounding = self._grounding_agents[active.domain_id]
        new_fact = await grounding.ground(
            active.grounding_key, active.goal.raw_text, active.goal.uid, scene_signal_text=scene_signal_text
        )
        divergence = grounding.check_divergence(plan_step_id=active.step.step_id, expected=active.fact, new_fact=new_fact)
        if divergence is None:
            return None

        active.replan_attempts += 1
        if self._replanning.should_escalate(active.replan_attempts):
            await self._escalation.escalate(
                session_id=session_id, uid=uid, reason="bounded replan exhausted", signals=["replan_exhausted"]
            )
            escalation_output = GuidanceOutput(
                session_id=session_id,
                text="I couldn't confirm a stable plan and I'm escalating to a human for help.",
                haptic_pattern="pattern-urgent",
                earcon="earcon-escalation",
            )
            denied = GuardrailDecision(step_id=active.step.step_id, decision="denied", reason="bounded replan exhausted")
            del self._active[session_id]
            return OrchestrationResult(guidance=escalation_output, guardrail=denied)

        replanned_fact = await self._replanning.replan(
            grounding=grounding, key=active.grounding_key, attempt=active.replan_attempts,
            raw_goal_text=active.goal.raw_text, scene_signal_text=scene_signal_text,
        )
        new_step = await self._planner.plan(active.goal, [replanned_fact], domain_id=active.domain_id)
        permissions = await self._memory.get_standing_permissions(uid)
        decision = self._guardrail.evaluate(new_step, replanned_fact.confidence, permissions)
        guidance_output = await self._guidance.shape(session_id, uid, new_step, urgent=True)

        active.fact = replanned_fact
        active.step = new_step

        return OrchestrationResult(guidance=guidance_output, guardrail=decision)

    async def handle_scene_signal(self, signal: SceneSignal) -> OrchestrationResult | None:
        active = self._active.get(signal.session_id)
        if active is None:
            return None

        domain = self._domains[active.domain_id]
        if hasattr(domain, "triage"):
            return await self.handle_document_signal(signal)

        grounding = self._grounding_agents[active.domain_id]
        if not grounding.scene_signal_suggests_divergence(expected=active.fact, signal=signal):
            return None

        # The camera only ever earns the right to ask "please re-check" —
        # check_for_divergence re-queries the real feed and is the actual
        # tie-breaker (design doc §4), exactly as it already was for
        # Phase 2a's polling-triggered divergence. scene_signal_text is
        # threaded through so a signage-only domain (Phase 4a) can use the
        # camera's own read as the re-grounded value — a real feed/
        # directory-backed domain ignores it entirely (GroundingRequest
        # defaults it to "" and TransitDomain/PersonalAdminDomain never
        # read it).
        return await self.check_for_divergence(
            session_id=signal.session_id, uid=active.goal.uid, scene_signal_text=signal.text
        )

    async def handle_document_signal(self, signal: SceneSignal) -> OrchestrationResult | None:
        active = self._active.get(signal.session_id)
        if active is None:
            return None
        domain = self._domains[active.domain_id]
        triage = getattr(domain, "triage", None)
        if triage is None:
            return None

        triage_result = await triage(signal)

        if triage_result.subflow == "inform-only":
            # Nothing to ground, plan, or confirm — a junk/inform-only
            # document (including one screen_untrusted_content() force-routed
            # here) never reaches an executable subflow at all. See this
            # task's design note.
            guidance_output = GuidanceOutput(
                session_id=signal.session_id,
                text=f"This looks like a {triage_result.category} item — I don't think it needs action from me.",
                haptic_pattern=None, earcon=None,
            )
            decision = GuardrailDecision(step_id="inform-only", decision="approved", reason="inform-only subflow, nothing to execute")
            return OrchestrationResult(guidance=guidance_output, guardrail=decision)

        fact = await self._grounding_agents[active.domain_id].ground(
            triage_result.category, active.goal.raw_text, active.goal.uid, subflow=triage_result.subflow
        )
        step = await self._planner.plan(active.goal, [fact], domain_id=active.domain_id)

        build_payload = getattr(domain, "build_executor_payload", None)
        if build_payload is not None:
            step = step.model_copy(update={
                "payload": await build_payload(step, fact, triage_result, active.goal.uid, signal=signal)
            })

        active.fact = fact

        # Form-filling's build_executor_payload (Task 2) may report field
        # resolution status in the payload — Call Agent's payload never has
        # these keys, so this whole block is a no-op for "call".
        unresolved_count = step.payload.get("unresolved_field_count", 0)
        if unresolved_count > 1:
            # More than one missing field is out of scope for the
            # field-request pause (design doc §8's "exactly one") — denied
            # with a spoken explanation, never a crash or a silent pause.
            guidance_output = GuidanceOutput(
                session_id=signal.session_id,
                text="This form has more than one field I can't fill in on my own — I'll need you to fill it in by hand.",
                haptic_pattern=None, earcon=None,
            )
            decision = GuardrailDecision(step_id=step.step_id, decision="denied", reason="more than one unresolved form field")
            return OrchestrationResult(guidance=guidance_output, guardrail=decision)

        missing_field = step.payload.get("missing_field")
        if missing_field:
            field_label = next(
                (f["label"] for f in step.payload.get("fields", []) if f["name"] == missing_field), missing_field,
            )
            self._pending_input[signal.session_id] = _PendingInput(
                step=step, uid=active.goal.uid, domain_id=active.domain_id,
                mode="field_request", confidence=fact.confidence, field_name=missing_field,
            )
            guidance_output = GuidanceOutput(
                session_id=signal.session_id,
                text=f"I've filled in what I can, but I need one more thing — what's your {field_label.lower()}?",
                haptic_pattern=None, earcon=None,
            )
            decision = GuardrailDecision(
                step_id=step.step_id, decision="requires_field_input",
                reason="form has one unresolved field", field_label=field_label,
            )
            return OrchestrationResult(guidance=guidance_output, guardrail=decision)

        return await self._gate_and_respond(signal.session_id, active.goal.uid, active.domain_id, step, fact.confidence)

    async def resolve_confirmation(self, session_id: str, uid: str, accepted: bool) -> OrchestrationResult | None:
        pending = self._pending_input.get(session_id)
        if pending is None or pending.mode != "confirm":
            return None
        del self._pending_input[session_id]

        category = pending.step.payload.get("category", "uncategorized")
        provider = pending.step.payload.get("provider")
        await self._memory.record_confirmation_outcome(
            uid, category=category, provider=provider, decision="approved" if accepted else "denied"
        )

        if not accepted:
            guidance_output = GuidanceOutput(
                session_id=session_id, text="Okay, I won't do that.", haptic_pattern=None, earcon=None
            )
            decision = GuardrailDecision(step_id=pending.step.step_id, decision="denied", reason="user declined")
            return OrchestrationResult(guidance=guidance_output, guardrail=decision)

        return await self._execute_step(session_id, uid, pending.domain_id, pending.step)

    async def resolve_field_input(self, session_id: str, uid: str, value: str) -> OrchestrationResult | None:
        pending = self._pending_input.get(session_id)
        if pending is None or pending.mode != "field_request":
            return None
        del self._pending_input[session_id]

        fields = list(pending.step.payload.get("fields", []))
        updated_fields = [
            {**f, "value": value, "source": "user_provided"} if f["name"] == pending.field_name else f
            for f in fields
        ]
        updated_payload = {**pending.step.payload, "fields": updated_fields, "missing_field": None}
        step = pending.step.model_copy(update={"payload": updated_payload})

        return await self._gate_and_respond(session_id, uid, pending.domain_id, step, pending.confidence)

    async def _gate_and_respond(
        self, session_id: str, uid: str, domain_id: str, step: PlanStep, confidence: float
    ) -> OrchestrationResult:
        """The shared tail of both handle_document_signal (once a step has
        no missing field left to ask about) and resolve_field_input (once
        the last missing field has just been filled in) — a form and a call
        both go through the identical confirm-before-execute gate from here,
        proving the two pause modes converge on one path, not two."""
        permissions = await self._memory.get_standing_permissions(uid)
        decision = self._guardrail.evaluate(step, confidence, permissions)

        active = self._active.get(session_id)
        if active is not None:
            active.step = step

        if decision.decision == "approved":
            return await self._execute_step(session_id, uid, domain_id, step)

        if decision.decision == "requires_confirmation":
            self._pending_input[session_id] = _PendingInput(
                step=step, uid=uid, domain_id=domain_id, mode="confirm", confidence=confidence
            )

        guidance_output = await self._guidance.shape(session_id, uid, step)
        return OrchestrationResult(guidance=guidance_output, guardrail=decision)

    async def _execute_step(self, session_id: str, uid: str, domain_id: str, step: PlanStep) -> OrchestrationResult:
        domain = self._domains[domain_id]
        executor = domain.executors.get(step.payload.get("executor", "call"))
        if executor is None:
            guidance_output = await self._guidance.shape(session_id, uid, step)
            decision = GuardrailDecision(step_id=step.step_id, decision="denied", reason="no executor registered")
            return OrchestrationResult(guidance=guidance_output, guardrail=decision)

        raw_outcome = await executor.execute(step.payload)
        try:
            outcome = ExecutorOutcome(**raw_outcome)
        except ValidationError:
            outcome = ExecutorOutcome(step_id=step.step_id, status="failed", structured_data={}, summary_text="")

        # See this task's design note: a status-derived decision, never
        # GuardrailAgent.evaluate() — that method's semantics are for gating
        # a *proposed* action, not re-confirming an already-executed one.
        report_decision = GuardrailDecision(
            step_id=step.step_id,
            decision="approved" if outcome.status == "success" else "denied",
            reason=f"executor outcome status={outcome.status}",
        )
        report_step = PlanStep(
            step_id=step.step_id, domain_id=domain_id,
            description=outcome.summary_text or "The action could not be completed.",
            action_type="guidance", requires_confirmation=False,
            payload={"category": step.payload.get("category", "uncategorized")},
        )
        guidance_output = await self._guidance.shape(session_id, uid, report_step)
        await self._memory.record_task_history(uid=uid, session_id=session_id, summary=outcome.summary_text)
        return OrchestrationResult(guidance=guidance_output, guardrail=report_decision)
