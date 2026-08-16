from app.agents.perception import PerceptionAgent


def test_handle_transcript_produces_a_perceived_goal() -> None:
    agent = PerceptionAgent()
    goal = agent.handle_transcript(session_id="s1", uid="u1", text="  get me to platform 4  ")
    assert goal.session_id == "s1"
    assert goal.uid == "u1"
    assert goal.raw_text == "get me to platform 4"
