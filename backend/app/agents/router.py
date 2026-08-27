from app.agents.llm_runner import LlmAgentRunner
from app.domains import DomainPlugin
from app.models.agent_events import PerceivedGoal

#: The router asks the LLM to reply with this exact token when the request
#: fits none of the available task domains.
_NO_DOMAIN_TOKEN = "NONE"


class DomainRouterAgent:
    """`matches()` is a fast keyword pre-filter. When exactly one plugin
    matches, that is the answer with no LLM call. Otherwise — zero matches,
    or an ambiguous multi-match — an ADK `LlmAgent` (via `LlmAgentRunner`)
    classifies the request against the candidate set (all domains when the
    pre-filter found nothing), or says NONE so the caller can ask the user
    to rephrase. Keyword lists are narrow by design; real spoken phrasing
    rarely contains them, so the LLM is the normal path, not the exception."""

    def __init__(self, runner: LlmAgentRunner, domains: list[DomainPlugin]) -> None:
        self._runner = runner
        self._domains = domains

    async def route(self, goal: PerceivedGoal) -> str:
        candidates = [d for d in self._domains if d.matches(goal.raw_text)]
        if len(candidates) == 1:
            return candidates[0].domain_id

        pool = candidates or list(self._domains)
        options = ", ".join(d.domain_id for d in pool)
        prompt = (
            f"User request: {goal.raw_text}\n"
            f"Available task domains: {options}\n"
            f"Reply with exactly the one domain id that best fits this request, "
            f"or {_NO_DOMAIN_TOKEN} if it fits none of them. Reply with that token only, nothing else."
        )
        response = await self._runner.invoke(user_id=goal.uid, session_id=goal.session_id, prompt=prompt)
        chosen = response.strip()
        if chosen in {d.domain_id for d in pool}:
            return chosen
        raise ValueError(f"no domain plugin matches this goal (router said {chosen!r})")
