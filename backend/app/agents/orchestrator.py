from dataclasses import dataclass

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
from app.models.agent_events import (
    GroundedFact, GuardrailDecision, GuidanceOutput, PerceivedGoal, PlanStep, SceneSignal,
)

tracer = get_tracer(__name__)


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
    """

    def __init__(
        self,
        *,
        perception: PerceptionAgent,
        router: DomainRouterAgent,
        grounding_agents: dict[str, GroundingAgent],
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
        self._planner = planner
        self._guardrail = guardrail
        self._replanning = replanning
        self._guidance = guidance
        self._memory = memory
        self._escalation = escalation
        self._active: dict[str, _ActiveTask] = {}  # keyed by session_id

    async def handle_goal(self, goal: PerceivedGoal) -> OrchestrationResult:
        with tracer.start_as_current_span("agent.handle_goal") as span:
            span.set_attribute("argus.session_id", goal.session_id)
            span.set_attribute("argus.uid", goal.uid)
            domain_id = await self._router.route(goal)
            span.set_attribute("argus.domain_id", domain_id)
            grounding = self._grounding_agents[domain_id]

            # Phase 1's stub domain only ever grounds one key; a real domain
            # (later phase) would derive this from the goal text.
            grounding_key = "platform"
            fact = await grounding.ground(grounding_key, goal.raw_text)

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

    async def check_for_divergence(self, *, session_id: str, uid: str) -> OrchestrationResult | None:
        active = self._active.get(session_id)
        if active is None:
            return None

        grounding = self._grounding_agents[active.domain_id]
        new_fact = await grounding.ground(active.grounding_key, active.goal.raw_text)
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
            grounding=grounding, key=active.grounding_key, attempt=active.replan_attempts, raw_goal_text=active.goal.raw_text
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

        grounding = self._grounding_agents[active.domain_id]
        if not grounding.scene_signal_suggests_divergence(expected=active.fact, signal=signal):
            return None

        # The camera only ever earns the right to ask "please re-check" —
        # check_for_divergence re-queries the real feed and is the actual
        # tie-breaker (design doc §4), exactly as it already was for
        # Phase 2a's polling-triggered divergence.
        return await self.check_for_divergence(session_id=signal.session_id, uid=active.goal.uid)
