from app.agents.grounding import GroundingAgent
from app.models.agent_events import GroundedFact

#: Bounded per the master spec's oscillation-protection requirement —
#: exceeding this emits an EscalationEvent instead of looping further.
MAX_REPLAN_ATTEMPTS = 3


class ReplanningAgent:
    """Triggered only by a DivergenceSignal. Re-invokes the domain plugin's
    grounding for the contradicted fact — not a full task restart — and
    hands the Planner an updated fact set.

    Takes its GroundingAgent per call, not at construction: Phase 1 had
    exactly one domain, so a `GroundingAgent` fixed at construction was
    never wrong — but the orchestrator's `check_for_divergence` already
    looks up the *active task's own* domain's GroundingAgent from
    `self._grounding_agents[active.domain_id]` and never actually passed it
    through to `replan()`. With a single domain this bug was invisible; with
    two feeds it would silently replan against the wrong domain's grounding
    source whenever the active task wasn't the one the agent happened to be
    constructed with."""

    def __init__(self) -> None:
        pass

    async def replan(self, *, grounding: GroundingAgent, key: str, attempt: int, raw_goal_text: str = "") -> GroundedFact:
        return await grounding.ground(key, raw_goal_text)

    def should_escalate(self, attempt: int) -> bool:
        return attempt > MAX_REPLAN_ATTEMPTS
