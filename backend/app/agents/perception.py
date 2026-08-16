from app.models.agent_events import PerceivedGoal


class PerceptionAgent:
    """Structures Gemini Live's transcribed output into typed models. Not a
    second model call — Gemini Live already did the multimodal reasoning;
    this only parses its output. The only agent that ever sees raw
    transcript text; everything downstream sees only `PerceivedGoal`."""

    def handle_transcript(self, *, session_id: str, uid: str, text: str) -> PerceivedGoal:
        return PerceivedGoal(session_id=session_id, uid=uid, raw_text=text.strip())
