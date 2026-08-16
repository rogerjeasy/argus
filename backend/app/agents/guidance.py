from app.agents.llm_runner import LlmAgentRunner
from app.models.agent_events import FramingAssessment, GuidanceOutput, PlanStep

#: Fixed, not model-generated — same latency/consistency reasoning as the
#: haptic/earcon vocabulary in shape(): a blind/low-vision user needs
#: framing feedback fast and identical every time, not phrased freshly by
#: an LLM call on every camera frame.
_POSITION_PHRASES = {
    "left": "Move slightly left.",
    "right": "Move slightly right.",
    "too-close": "Move back a little.",
    "too-far": "Move a bit closer.",
    "center": "Hold steady, almost there.",
    "none": "I can't see readable text yet. Try panning the camera slowly.",
}


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

    def shape_framing(self, session_id: str, assessment: FramingAssessment) -> GuidanceOutput:
        text = _POSITION_PHRASES.get(assessment.position, _POSITION_PHRASES["none"])
        return GuidanceOutput(
            session_id=session_id,
            text=text,
            haptic_pattern=None,
            earcon="earcon-low-confidence" if not assessment.text_detected else None,
        )
