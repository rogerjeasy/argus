import pytest

from app.agents.audio_perception import AudioPerceptionAgent
from app.tests.doubles.fake_audio_classifier import FakeAudioClassifier


@pytest.mark.asyncio
async def test_classify_ambient_sound_returns_the_category_when_concerning() -> None:
    classifier = FakeAudioClassifier(result="alarm")
    agent = AudioPerceptionAgent(classifier)

    result = await agent.classify_ambient_sound(b"raw-audio-bytes")

    assert result == "alarm"
    assert classifier.calls == [b"raw-audio-bytes"]


@pytest.mark.asyncio
async def test_classify_ambient_sound_returns_none_for_ordinary_ambient_noise() -> None:
    classifier = FakeAudioClassifier(result="none")
    agent = AudioPerceptionAgent(classifier)

    result = await agent.classify_ambient_sound(b"raw-audio-bytes")

    assert result is None


@pytest.mark.asyncio
async def test_classify_ambient_sound_recognizes_every_concerning_category() -> None:
    for category in ("knock", "alarm", "distress_utterance"):
        classifier = FakeAudioClassifier(result=category)
        agent = AudioPerceptionAgent(classifier)

        assert await agent.classify_ambient_sound(b"x") == category
