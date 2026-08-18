from pydantic import BaseModel

from app.agents.memory import MemoryAgent

#: Matches the design doc §4's own example ("approved 15/15 times over 3
#: weeks") exactly — a strict all-approved bar over this many total
#: confirmation responses, not a percentage or a rolling window (both would
#: need a time-decay policy the design doc never specifies; this is the
#: simplest rule that matches the doc's own worked example precisely).
_DEFAULT_THRESHOLD = 15


class CalibrationProposal(BaseModel):
    category: str
    provider: str | None
    current_rule: str = "confirm_every_time"
    proposed_rule: str = "auto_approve"
    evidence: str
    status: str = "pending_user_opt_in"


class CalibrationAgent:
    """Read-only over confirmation-outcome history. Deliberately has no
    reference anywhere in this class to the standing-permissions document
    or MemoryAgent.get_standing_permissions — see this plan's Global
    Constraints on why this is a code-level guarantee, not (as the design
    doc's prose alone might suggest) an infrastructure-level one. Only
    MemoryAgent.apply_calibration_proposal_to_standing_permissions,
    triggered exclusively by an explicit user "yes", ever writes there."""

    def __init__(self, memory: MemoryAgent, threshold: int = _DEFAULT_THRESHOLD) -> None:
        self._memory = memory
        self._threshold = threshold

    async def detect_proposal(self, uid: str, *, category: str, provider: str | None) -> CalibrationProposal | None:
        history = await self._memory.get_confirmation_history(uid, category=category, provider=provider)
        if len(history) < self._threshold:
            return None
        if any(h.decision == "denied" for h in history):
            return None

        return CalibrationProposal(
            category=category, provider=provider,
            evidence=f"approved {len(history)}/{len(history)} times",
        )

    async def run_for_all_users(self, uids_and_categories: "list[tuple[str, str, str | None]]") -> int:
        created = 0
        for uid, category, provider in uids_and_categories:
            existing = await self._memory.get_pending_calibration_proposal(uid)
            if existing is not None and existing[1].category == category and existing[1].provider == provider:
                continue
            proposal = await self.detect_proposal(uid, category=category, provider=provider)
            if proposal is not None:
                await self._memory.store_calibration_proposal(uid, proposal)
                created += 1
        return created
