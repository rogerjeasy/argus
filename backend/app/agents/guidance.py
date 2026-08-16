from app.agents.llm_runner import LlmAgentRunner
from app.models.agent_events import GuidanceOutput, PlanStep


class GuidanceAgent:
    """Shapes a PlanStep into spoken text plus a haptic pattern and earcon
    chosen from a small fixed vocabulary — not invented per-call, matching
    the master spec's "modality-to-signal mapping is deliberate, not
    decorative." """

    def __init__(self, runner: LlmAgentRunner) -> None:
        self._runner = runner

    async def shape(self, session_id: str, uid: str, step: PlanStep, *, urgent: bool = False) -> GuidanceOutput:
        prompt = (
            f"Turn this plan step into one short, concrete spoken instruction "
            f"for a blind or low-vision user: {step.description}"
        )
        text = await self._runner.invoke(user_id=uid, session_id=session_id, prompt=prompt)
        return GuidanceOutput(
            session_id=session_id,
            text=text,
            haptic_pattern="pattern-urgent" if urgent else "pattern-forward",
            earcon="earcon-plan-updated",
        )
