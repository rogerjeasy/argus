from app.agents.grounding import GroundingAgent
from app.models.agent_events import GroundedFact

#: Bounded per the master spec's oscillation-protection requirement —
#: exceeding this emits an EscalationEvent instead of looping further.
MAX_REPLAN_ATTEMPTS = 3


class ReplanningAgent:
    """Triggered only by a DivergenceSignal. Re-invokes the domain plugin's
    grounding for the contradicted fact — not a full task restart — and
    hands the Planner an updated fact set."""

    def __init__(self, grounding: GroundingAgent) -> None:
        self._grounding = grounding

    async def replan(self, *, key: str, attempt: int, raw_goal_text: str = "") -> GroundedFact:
        return await self._grounding.ground(key, raw_goal_text)

    def should_escalate(self, attempt: int) -> bool:
        return attempt > MAX_REPLAN_ATTEMPTS
