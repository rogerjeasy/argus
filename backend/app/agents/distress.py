import re

#: Deliberately narrow and literal — false negatives (missing a real
#: distress utterance) are safer to correct later than false positives
#: (an accidental escalation call is itself disruptive for a blind/
#: low-vision user, per this system's whole accessibility-first mission).
#: Word-boundary matching, not substring containment — see every other
#: keyword-list domain in this project for the established reason.
_DISTRESS_KEYWORDS = (
    "help me", "i've fallen", "i fell", "i'm hurt", "this hurts",
    "call someone", "call for help", "emergency", "i need help",
)
_KEYWORD_PATTERN = re.compile("|".join(rf"\b{re.escape(k)}\b" for k in _DISTRESS_KEYWORDS))


def detect_distress_keywords(text: str) -> bool:
    return bool(_KEYWORD_PATTERN.search(text.lower()))
