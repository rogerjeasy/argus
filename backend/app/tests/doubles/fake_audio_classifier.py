class FakeAudioClassifier:
    """Scriptable AudioClassifier double — set_result() controls what the
    next classify() call returns, mirroring FakeGroundingSource's
    settable-per-test shape."""

    def __init__(self, result: str = "none") -> None:
        self._result = result
        self.calls: list[bytes] = []

    def set_result(self, result: str) -> None:
        self._result = result

    async def classify(self, audio_chunk: bytes) -> str:
        self.calls.append(audio_chunk)
        return self._result
