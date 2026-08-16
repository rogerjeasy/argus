from app.models.agent_events import FramingAssessment, PerceivedGoal, SceneSignal


class PerceptionAgent:
    """Structures Gemini Live's transcribed output into typed models. Not a
    second model call — Gemini Live already did the multimodal reasoning;
    this only parses its output. The only agent that ever sees raw
    transcript text or raw function-call args; everything downstream sees
    only typed models."""

    def handle_transcript(self, *, session_id: str, uid: str, text: str) -> PerceivedGoal:
        return PerceivedGoal(session_id=session_id, uid=uid, raw_text=text.strip())

    def handle_scene_observation(
        self, *, session_id: str, text_detected: bool, position: str, signage_text: str, confidence: float
    ) -> tuple[FramingAssessment, SceneSignal | None]:
        framing = FramingAssessment(session_id=session_id, text_detected=text_detected, position=position)
        signal = (
            SceneSignal(session_id=session_id, kind="signage_text", text=signage_text, confidence=confidence)
            if signage_text
            else None
        )
        return framing, signal
