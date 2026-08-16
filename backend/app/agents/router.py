from app.agents.llm_runner import LlmAgentRunner
from app.domains import DomainPlugin
from app.models.agent_events import PerceivedGoal


class DomainRouterAgent:
    """`matches()` narrows the registry as a fast pre-filter; an ADK
    `LlmAgent` (via `LlmAgentRunner`) makes the final call only when more
    than one candidate remains. With Phase 1's single-entry registry
    (`StubDomain`), the fast path always wins — genuine multi-domain
    classification gets its first real exercise once a second plugin
    exists."""

    def __init__(self, runner: LlmAgentRunner, domains: list[DomainPlugin]) -> None:
        self._runner = runner
        self._domains = domains

    async def route(self, goal: PerceivedGoal) -> str:
        candidates = [d for d in self._domains if d.matches(goal.raw_text)]
        if not candidates:
            raise ValueError("no domain plugin matches this goal")
        if len(candidates) == 1:
            return candidates[0].domain_id

        options = ", ".join(d.domain_id for d in candidates)
        prompt = (
            f"Goal: {goal.raw_text}\nCandidate domains: {options}\n"
            "Reply with exactly one domain id from the candidates, nothing else."
        )
        response = await self._runner.invoke(user_id=goal.uid, session_id=goal.session_id, prompt=prompt)
        chosen = response.strip()
        if chosen not in {d.domain_id for d in candidates}:
            raise ValueError(f"router returned an unrecognized domain id: {chosen!r}")
        return chosen
