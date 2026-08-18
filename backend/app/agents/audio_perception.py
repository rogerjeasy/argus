from typing import Protocol

#: "none" is the classifier's own explicit "nothing concerning heard"
#: answer — collapsed to None here so every caller checks one thing
#: (`is not None`) rather than also excluding a magic string itself.
_CONCERNING_CATEGORIES = frozenset({"knock", "alarm", "distress_utterance"})


class AudioClassifier(Protocol):
    async def classify(self, audio_chunk: bytes) -> str: ...


class AudioPerceptionAgent:
    """Wraps a swappable AudioClassifier (real implementation: a low-
    frequency Gemini call, deferred to the pre-demo checklist — same
    pattern as every other real-external-service integration in this
    project). Runs continuously and independent of whether a task is
    active — the opt-in gate and the low-frequency throttling both live
    at the WS-session call site, not here, so this class stays a pure
    classify-one-chunk wrapper."""

    def __init__(self, classifier: AudioClassifier) -> None:
        self._classifier = classifier

    async def classify_ambient_sound(self, audio_chunk: bytes) -> str | None:
        category = await self._classifier.classify(audio_chunk)
        return category if category in _CONCERNING_CATEGORIES else None
