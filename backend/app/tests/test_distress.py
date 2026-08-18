from app.agents.distress import detect_distress_keywords


def test_detects_help_me() -> None:
    assert detect_distress_keywords("help me please") is True


def test_detects_ive_fallen() -> None:
    assert detect_distress_keywords("I've fallen and I can't get up") is True


def test_detects_im_hurt() -> None:
    assert detect_distress_keywords("I'm hurt, this really hurts") is True


def test_detects_call_someone() -> None:
    assert detect_distress_keywords("please call someone for me") is True


def test_ordinary_goal_is_not_flagged() -> None:
    assert detect_distress_keywords("get me to platform 4") is False


def test_word_boundaries_not_substrings() -> None:
    # "hurt" must not match inside an unrelated word like "hurtle" — same
    # word-boundary discipline as every other keyword-list domain in this
    # project (PersonalAdminDomain, IndoorWayfindingDomain).
    assert detect_distress_keywords("the train will hurtle past the station") is False
