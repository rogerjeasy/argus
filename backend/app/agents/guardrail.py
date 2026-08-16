import re

from app.agents.memory import StandingPermission
from app.models.agent_events import GuardrailDecision, PlanStep

#: Below this, a fact is too uncertain to act on regardless of any standing
#: permission — a rule in source control, not a prompt, per the master
#: spec's "how does the system recover if a worker agent hallucinates."
MIN_CONFIDENCE_FLOOR = 0.5

#: A deterministic screen, not the authority boundary — standing permissions
#: are read from MemoryAgent's Firestore document only, never inferred from
#: perceived text. Matches imperative phrases a scam letter or a malicious
#: IVR prompt would use to try to grant itself authority it was never given.
_UNTRUSTED_CONTENT_PATTERN = re.compile(
    r"approve (this|automatically)|ignore (previous|prior) instructions|"
    r"send payment now|auto-approve|do not (ask|confirm)",
    re.IGNORECASE,
)


class GuardrailAgent:
    """A rule evaluator, not a model call. Reads the plan step, the user's
    standing-permissions document, and a fixed confidence floor, and returns
    a decision. Deliberately deterministic and auditable."""

    def evaluate(
        self, step: PlanStep, confidence: float, standing_permissions: list[StandingPermission]
    ) -> GuardrailDecision:
        if confidence < MIN_CONFIDENCE_FLOOR:
            return GuardrailDecision(step_id=step.step_id, decision="denied", reason="grounding confidence below floor")

        if step.requires_confirmation:
            return GuardrailDecision(
                step_id=step.step_id, decision="requires_confirmation", reason="domain plugin requires confirmation"
            )

        category = step.payload.get("category", "uncategorized")
        provider = step.payload.get("provider")
        matching = next(
            (
                p for p in standing_permissions
                if p.category == category and (p.provider is None or p.provider == provider)
            ),
            None,
        )
        if matching is not None and confidence >= matching.threshold:
            return GuardrailDecision(step_id=step.step_id, decision="approved", reason="standing permission covers this category")

        return GuardrailDecision(
            step_id=step.step_id, decision="requires_confirmation", reason="no standing permission for this category"
        )

    def screen_untrusted_content(self, text: str) -> bool:
        """True if perceived text (a scanned document, an IVR transcript)
        contains an embedded instruction attempting to grant itself
        authority. A miss here cannot grant anything by itself — standing
        permissions are still read only from MemoryAgent's Firestore
        document, never from this screen."""
        return bool(_UNTRUSTED_CONTENT_PATTERN.search(text))
