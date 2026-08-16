from app.agents.perception import PerceptionAgent


def test_handle_transcript_produces_a_perceived_goal() -> None:
    agent = PerceptionAgent()
    goal = agent.handle_transcript(session_id="s1", uid="u1", text="  get me to platform 4  ")
    assert goal.session_id == "s1"
    assert goal.uid == "u1"
    assert goal.raw_text == "get me to platform 4"


def test_handle_scene_observation_always_returns_a_framing_assessment() -> None:
    framing, signal = PerceptionAgent().handle_scene_observation(
        session_id="s1", text_detected=False, position="none", signage_text="", confidence=0.0
    )

    assert framing.session_id == "s1"
    assert framing.text_detected is False
    assert framing.position == "none"
    assert signal is None  # no signage text read — nothing to compare against the plan


def test_handle_scene_observation_produces_a_scene_signal_when_text_is_read() -> None:
    framing, signal = PerceptionAgent().handle_scene_observation(
        session_id="s1", text_detected=True, position="center", signage_text="Platform 7", confidence=0.9
    )

    assert framing.text_detected is True
    assert signal is not None
    assert signal.session_id == "s1"
    assert signal.kind == "signage_text"
    assert signal.text == "Platform 7"
    assert signal.confidence == 0.9
