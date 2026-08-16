from app.agents.memory import StandingPermission
from app.models.agent_events import GuardrailDecision, PlanStep

#: Below this, a fact is too uncertain to act on regardless of any standing
#: permission — a rule in source control, not a prompt, per the master
#: spec's "how does the system recover if a worker agent hallucinates."
MIN_CONFIDENCE_FLOOR = 0.5


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
        matching = next((p for p in standing_permissions if p.category == category), None)
        if matching is not None and confidence >= matching.threshold:
            return GuardrailDecision(step_id=step.step_id, decision="approved", reason="standing permission covers this category")

        return GuardrailDecision(
            step_id=step.step_id, decision="requires_confirmation", reason="no standing permission for this category"
        )
