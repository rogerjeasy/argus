import json
import re
from datetime import datetime, timezone

from app.agents.guardrail import GuardrailAgent
from app.agents.llm_runner import LlmAgentRunner
from app.agents.memory import MemoryAgent
from app.domains import GroundingRequest
from app.domains.personal_admin.models import TriageResult
from app.models.agent_events import GroundedFact, PlanStep, SceneSignal

#: A fast pre-filter, same role as TransitDomain's keyword list
#: (app/domains/transit/config.py) — DomainRouterAgent's LLM disambiguation
#: is the real classifier when more than one domain's matches() returns True.
_PERSONAL_ADMIN_KEYWORDS = ("mail", "letter", "bill", "form", "call the", "deal with this", "pharmacy", "refill")

#: Word-boundary matching, not raw substring containment — TransitDomain's
#: own "platform" keyword contains "form" as a substring, and a plain
#: `keyword in text` check would misroute every transit goal mentioning a
#: platform into this domain.
_KEYWORD_PATTERN = re.compile("|".join(rf"\b{re.escape(keyword)}\b" for keyword in _PERSONAL_ADMIN_KEYWORDS))

_UNRESOLVED_CONFIDENCE = 0.0


class PersonalAdminDomain:
    """Grounds against the user's own stored profile (MemoryAgent), not an
    external feed — the one domain where ground()'s source is Memory
    itself. triage() is a plugin-provided reasoning step the orchestrator
    calls once routed (design doc §4a) — not a new specialist agent, per
    master spec §7's explicit design choice."""

    domain_id = "personal_admin"

    def __init__(self, triage_runner: LlmAgentRunner, memory: MemoryAgent, guardrail: GuardrailAgent) -> None:
        self._triage_runner = triage_runner
        self._memory = memory
        self._guardrail = guardrail
        self.executors: dict = {}

    def matches(self, goal_text: str) -> bool:
        return bool(_KEYWORD_PATTERN.search(goal_text.lower()))

    async def triage(self, document_signal: SceneSignal) -> TriageResult:
        prompt = (
            "A blind or low-vision user photographed a piece of mail or a document. "
            f"Its detected text: {document_signal.text!r}\n\n"
            'Reply with JSON only: {"category": "bill"|"medical"|"legal"|"junk"|"scam-suspect", '
            '"urgency": "low"|"normal"|"high", "subflow": "call"|"form"|"inform-only", "confidence": float}'
        )
        response = await self._triage_runner.invoke(
            user_id="triage", session_id=document_signal.session_id, prompt=prompt
        )
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError as exc:
            raise ValueError(f"could not parse triage response: {response!r}") from exc
        result = TriageResult(**parsed)

        if self._guardrail.screen_untrusted_content(document_signal.text):
            # An embedded instruction overrides the LLM's own classification
            # — a scam letter's text is never trusted to route itself to an
            # executable subflow, regardless of what triage concluded from
            # it. See this task's design note.
            return TriageResult(category="scam-suspect", urgency=result.urgency, subflow="inform-only", confidence=result.confidence)
        return result

    async def ground(self, request: GroundingRequest) -> GroundedFact:
        profile = await self._memory.get_profile(request.uid)
        provider = next((p for p in profile.known_providers if p.category == request.key), None)
        if provider is None:
            return GroundedFact(
                key=request.key, value="", source="user_profile", confidence=_UNRESOLVED_CONFIDENCE,
                as_of=datetime.now(timezone.utc),
            )
        return GroundedFact(
            key=request.key, value=provider.phone_number, source="user_profile", confidence=1.0,
            as_of=datetime.now(timezone.utc),
        )

    async def build_executor_payload(
        self, step: PlanStep, fact: GroundedFact, triage_result: TriageResult, uid: str
    ) -> dict:
        """PlannerAgent.plan()'s real prompt only ever produces {description,
        action_type, requires_confirmation, category} — it has no reason to
        know CallGoal's shape (master spec §7.1: only the domain plugin
        changes). This derives everything an executor payload needs from
        data the domain already has, called by the orchestrator right
        before Guardrail evaluates the step (see this task's third gap)."""
        payload = dict(step.payload)
        payload["step_id"] = step.step_id
        payload["executor"] = "call" if triage_result.subflow == "call" else triage_result.subflow

        profile = await self._memory.get_profile(uid)
        provider = next((p for p in profile.known_providers if p.category == triage_result.category), None)
        payload["provider"] = provider.name if provider is not None else None

        if triage_result.subflow == "call" and provider is not None:
            payload["call_goal"] = {
                "target_phone_number": fact.value,
                "purpose": step.description,
                "structured_question": step.description,
            }
        return payload
