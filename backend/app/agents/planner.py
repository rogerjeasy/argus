import json
import uuid

from app.agents.llm_runner import LlmAgentRunner
from app.models.agent_events import GroundedFact, PerceivedGoal, PlanStep


class PlannerAgent:
    """Takes a goal plus the current grounded facts, returns a single next
    `PlanStep`. Domain-general logic; domain-specific knowledge arrives only
    through the `GroundedFact`s the plugin produced, never hardcoded here."""

    def __init__(self, runner: LlmAgentRunner) -> None:
        self._runner = runner

    async def plan(self, goal: PerceivedGoal, facts: list[GroundedFact], *, domain_id: str) -> PlanStep:
        facts_text = "\n".join(f"- {f.key}: {f.value} (confidence {f.confidence})" for f in facts) or "(none yet)"
        prompt = (
            f"Goal: {goal.raw_text}\nGrounded facts:\n{facts_text}\n\n"
            'Reply with JSON only: {"description": str, "action_type": "guidance"|"execute", '
            '"requires_confirmation": bool, "category": str}'
        )
        response = await self._runner.invoke(user_id=goal.uid, session_id=goal.session_id, prompt=prompt)
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError as exc:
            raise ValueError(f"could not parse planner response: {response!r}") from exc

        return PlanStep(
            step_id=str(uuid.uuid4()),
            domain_id=domain_id,
            description=parsed["description"],
            action_type=parsed["action_type"],
            requires_confirmation=parsed["requires_confirmation"],
            payload={"category": parsed["category"]},
        )
