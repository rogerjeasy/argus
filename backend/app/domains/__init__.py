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
    #: Which user is asking — Phase 1's TransitDomain/StubDomain answer the
    #: same for everyone, so they ignore this. PersonalAdminDomain.ground()
    #: reads that specific user's own stored profile, so it needs uid.
    #: Optional and defaulted so every Phase 1 call site is unaffected.
    uid: str = ""
    #: Clock override for deterministic tests only — production code leaves
    #: this unset and GtfsStaticIndex.resolve_stop() falls back to wall time.
    now: _time | None = None
    #: Which triage subflow this grounding call is for ("call"|"form"|
    #: "inform-only") — optional and defaulted so every non-PersonalAdmin
    #: call site (StubDomain, TransitDomain) is unaffected. PersonalAdminDomain
    #: needs it: a "form" subflow's grounded fact isn't "do we know this
    #: provider's phone number" the way "call" is — forms autofill from the
    #: profile directly in build_executor_payload, so ground() must not deny
    #: on that irrelevant question.
    subflow: str = ""
    #: The live camera-read signage text, when this grounding call was
    #: triggered by a scene signal rather than a polling recheck or the
    #: initial goal. Optional and defaulted so every existing call site
    #: (TransitDomain's polling-triggered re-ground, PersonalAdminDomain,
    #: StubDomain) is unaffected. IndoorWayfindingDomain's signage-only mode
    #: is the first domain that reads this — see app/domains/indoor_wayfinding/domain.py.
    scene_signal_text: str = ""

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
