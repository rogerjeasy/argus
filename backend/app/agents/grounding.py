from app.domains import DomainPlugin, GroundingRequest
from app.models.agent_events import DivergenceSignal, GroundedFact


class GroundingAgent:
    """Calls the active domain plugin's grounding source, and compares each
    new fact against the currently active plan's assumptions. Deliberately
    deterministic, not an LLM call — this is a trust boundary, and a trust
    boundary implemented as a model call is one a malformed or adversarial
    input can talk its way through."""

    def __init__(self, domain: DomainPlugin) -> None:
        self._domain = domain

    async def ground(self, key: str, raw_goal_text: str = "") -> GroundedFact:
        return await self._domain.ground(GroundingRequest(key=key, raw_goal_text=raw_goal_text))

    def check_divergence(
        self, *, plan_step_id: str, expected: GroundedFact, new_fact: GroundedFact
    ) -> DivergenceSignal | None:
        if expected.value == new_fact.value:
            return None
        return DivergenceSignal(
            session_id="",  # filled in by the orchestrator, which owns session context
            plan_step_id=plan_step_id,
            expected=expected.value,
            observed=new_fact.value,
            source=new_fact.source,
        )
