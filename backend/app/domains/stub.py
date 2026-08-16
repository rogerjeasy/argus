from datetime import datetime, timezone

from app.domains import DomainPlugin, GroundingRequest  # noqa: F401 — DomainPlugin documents the Protocol StubDomain implements
from app.models.agent_events import GroundedFact


class FakeGroundingSource:
    """A synthetic grounding source whose answers are settable per-test,
    including mid-test — this is what makes a divergence-and-replan sequence
    provable without any real external feed."""

    def __init__(self) -> None:
        self._answers: dict[str, str] = {}

    def set_answer(self, key: str, value: str) -> None:
        self._answers[key] = value

    def get_answer(self, key: str) -> str | None:
        return self._answers.get(key)


class StubDomain:
    domain_id = "stub"
    executors: dict = {}

    def __init__(self, source: FakeGroundingSource) -> None:
        self._source = source

    def matches(self, goal_text: str) -> bool:
        # The only domain plugin in Phase 1's registry — genuine multi-domain
        # classification isn't exercised until a second plugin exists.
        return True

    async def ground(self, request: GroundingRequest) -> GroundedFact:
        value = self._source.get_answer(request.key)
        return GroundedFact(
            key=request.key,
            value=value or "",
            source="stub_feed",
            confidence=1.0 if value is not None else 0.0,
            as_of=datetime.now(timezone.utc),
        )
