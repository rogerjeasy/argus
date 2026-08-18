import re

from app.agents.guardrail import MIN_CONFIDENCE_FLOOR
from app.domains import DomainPlugin, GroundingRequest
from app.models.agent_events import DivergenceSignal, GroundedFact, SceneSignal

_DIGIT_PATTERN = re.compile(r"\d+")


class GroundingAgent:
    """Calls the active domain plugin's grounding source, and compares each
    new fact against the currently active plan's assumptions. Deliberately
    deterministic, not an LLM call — this is a trust boundary, and a trust
    boundary implemented as a model call is one a malformed or adversarial
    input can talk its way through."""

    def __init__(self, domain: DomainPlugin) -> None:
        self._domain = domain

    async def ground(
        self, key: str, raw_goal_text: str = "", uid: str = "", subflow: str = "", scene_signal_text: str = ""
    ) -> GroundedFact:
        return await self._domain.ground(
            GroundingRequest(
                key=key, raw_goal_text=raw_goal_text, uid=uid, subflow=subflow, scene_signal_text=scene_signal_text
            )
        )

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

    def scene_signal_suggests_divergence(self, *, expected: GroundedFact, signal: SceneSignal) -> bool:
        """Gates whether a camera signal is worth a re-ground — never the
        divergence decision itself (that's still the real feed/directory via
        check_for_divergence). Both red-team cases from the design doc are
        enforced here regardless of domain: a low-confidence read and a
        signal with no plausible candidate content each return False before
        any grounding call happens.

        A domain may define extract_signage_candidate(text) -> str | None
        to say what "plausible content for this domain" means (e.g.
        IndoorWayfindingDomain matches against directory entries or, in
        signage-only mode, accepts any non-blank read). Domains that don't
        define it (TransitDomain, StubDomain, PersonalAdminDomain) fall back
        to the original digit-pattern check, unmodified — see the design
        doc §3's explicit instruction not to change this shape for domains
        that don't need to."""
        if signal.kind != "signage_text":
            return False
        if signal.confidence < MIN_CONFIDENCE_FLOOR:
            return False

        extractor = getattr(self._domain, "extract_signage_candidate", None)
        if extractor is not None:
            candidate = extractor(signal.text)
            return candidate is not None and candidate != expected.value

        match = _DIGIT_PATTERN.search(signal.text)
        if match is None:
            return False
        return match.group() != expected.value
