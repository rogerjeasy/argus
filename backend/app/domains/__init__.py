from datetime import time as _time
from typing import Protocol

from pydantic import BaseModel

from app.models.agent_events import GroundedFact


class GroundingRequest(BaseModel):
    key: str
    #: The user's raw spoken goal text — Phase 1's StubDomain never needed
    #: this (it had one hardcoded answer); a real domain uses it to resolve
    #: which stop/trip the user meant. Optional and defaulted so every
    #: Phase 1 call site (`GroundingRequest(key=key)`) is unaffected.
    raw_goal_text: str = ""
    #: Clock override for deterministic tests only — production code leaves
    #: this unset and GtfsStaticIndex.resolve_stop() falls back to wall time.
    now: _time | None = None

    model_config = {"arbitrary_types_allowed": True}


class Executor(Protocol):
    async def execute(self, payload: dict) -> dict: ...


class DomainPlugin(Protocol):
    domain_id: str

    def matches(self, goal_text: str) -> bool:
        """Fast pre-filter for the Domain Router's classification step —
        narrows candidates before the LLM call makes the final decision."""
        ...

    async def ground(self, request: GroundingRequest) -> GroundedFact: ...

    executors: dict[str, Executor]
