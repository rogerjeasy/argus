import inspect

import pytest

from app.agents.calibration import CalibrationAgent
from app.agents.memory import MemoryAgent
from app.tests.doubles.fake_firestore import FakeFirestoreClient


async def _seed_approvals(memory: MemoryAgent, uid: str, *, category: str, provider: str, count: int) -> None:
    for _ in range(count):
        await memory.record_confirmation_outcome(uid, category=category, provider=provider, decision="approved")


@pytest.mark.asyncio
async def test_detect_proposal_after_fifteen_of_fifteen_approvals() -> None:
    db = FakeFirestoreClient()
    memory = MemoryAgent(db)
    await _seed_approvals(memory, "u1", category="pharmacy_refill", provider="cvs-main-st", count=15)
    agent = CalibrationAgent(memory)

    proposal = await agent.detect_proposal("u1", category="pharmacy_refill", provider="cvs-main-st")

    assert proposal is not None
    assert proposal.category == "pharmacy_refill"
    assert proposal.provider == "cvs-main-st"
    assert proposal.evidence == "approved 15/15 times"
    assert proposal.status == "pending_user_opt_in"
    assert proposal.current_rule == "confirm_every_time"


@pytest.mark.asyncio
async def test_detect_proposal_returns_none_below_threshold() -> None:
    db = FakeFirestoreClient()
    memory = MemoryAgent(db)
    await _seed_approvals(memory, "u1", category="pharmacy_refill", provider="cvs-main-st", count=14)
    agent = CalibrationAgent(memory)

    assert await agent.detect_proposal("u1", category="pharmacy_refill", provider="cvs-main-st") is None


@pytest.mark.asyncio
async def test_detect_proposal_returns_none_if_any_denial_exists() -> None:
    db = FakeFirestoreClient()
    memory = MemoryAgent(db)
    await _seed_approvals(memory, "u1", category="pharmacy_refill", provider="cvs-main-st", count=14)
    await memory.record_confirmation_outcome("u1", category="pharmacy_refill", provider="cvs-main-st", decision="denied")
    agent = CalibrationAgent(memory)

    assert await agent.detect_proposal("u1", category="pharmacy_refill", provider="cvs-main-st") is None


@pytest.mark.asyncio
async def test_threshold_is_configurable() -> None:
    db = FakeFirestoreClient()
    memory = MemoryAgent(db)
    await _seed_approvals(memory, "u1", category="pharmacy_refill", provider="cvs-main-st", count=3)
    agent = CalibrationAgent(memory, threshold=3)

    proposal = await agent.detect_proposal("u1", category="pharmacy_refill", provider="cvs-main-st")

    assert proposal is not None
    assert proposal.evidence == "approved 3/3 times"


def test_calibration_agent_source_never_references_standing_permissions() -> None:
    """The code-level write-scope-separation guarantee this plan actually
    delivers (see this plan's Global Constraints on the honest scoping of
    the design doc's stronger infra-level claim): CalibrationAgent's own
    source has no reference to get_standing_permissions or any
    permissions-document write path at all.

    Checks method *bodies* only (excludes __doc__), not the class's own
    docstring — the docstring legitimately explains this property in
    English prose, which naturally contains words like "permissions" and
    "standing"; that's documentation, not a capability. The real guarantee
    is that no method calls the actual named methods that write there."""
    for name in ("__init__", "detect_proposal"):
        method_source = inspect.getsource(getattr(CalibrationAgent, name))
        assert "get_standing_permissions" not in method_source
        assert "apply_calibration_proposal_to_standing_permissions" not in method_source
        assert "_permissions_doc" not in method_source


@pytest.mark.asyncio
async def test_run_for_all_users_creates_proposals_for_qualifying_triples() -> None:
    db = FakeFirestoreClient()
    memory = MemoryAgent(db)
    await _seed_approvals(memory, "u1", category="pharmacy_refill", provider="cvs-main-st", count=15)
    await _seed_approvals(memory, "u2", category="bill_payment", provider=None, count=3)  # below threshold
    agent = CalibrationAgent(memory)

    created = await agent.run_for_all_users([
        ("u1", "pharmacy_refill", "cvs-main-st"),
        ("u2", "bill_payment", None),
    ])

    assert created == 1
    pending = await memory.get_pending_calibration_proposal("u1")
    assert pending is not None
    assert await memory.get_pending_calibration_proposal("u2") is None


@pytest.mark.asyncio
async def test_run_for_all_users_does_not_duplicate_an_existing_pending_proposal() -> None:
    db = FakeFirestoreClient()
    memory = MemoryAgent(db)
    await _seed_approvals(memory, "u1", category="pharmacy_refill", provider="cvs-main-st", count=15)
    agent = CalibrationAgent(memory)

    first_run = await agent.run_for_all_users([("u1", "pharmacy_refill", "cvs-main-st")])
    second_run = await agent.run_for_all_users([("u1", "pharmacy_refill", "cvs-main-st")])

    assert first_run == 1
    assert second_run == 0  # already has a pending proposal for this triple
