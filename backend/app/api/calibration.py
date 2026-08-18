from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.agents.calibration import CalibrationAgent
from app.agents.memory import MemoryAgent
from app.core.clients import get_firestore_client
from app.core.config import Settings, get_settings

router = APIRouter(prefix="/internal", tags=["internal"])


def _verify_calibration_secret(
    x_calibration_secret: str = Header(default=""), settings: Settings = Depends(get_settings)
) -> None:
    # Fail-closed: an empty configured secret never matches an empty header,
    # so a deployment that forgot to set the secret rejects every call
    # rather than accepting every call.
    if not settings.calibration_job_shared_secret or x_calibration_secret != settings.calibration_job_shared_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid calibration secret")


async def _collect_triples(db) -> "list[tuple[str, str, str | None]]":
    """Scans every user's confirmation history for distinct (category,
    provider) pairs — a real, explicitly-not-scaled O(all history) pass,
    not a Firestore query (this project's real Firestore usage doesn't
    use collection-group queries anywhere yet, and the fake test double
    deliberately doesn't add query filtering either — see this task's
    plan note and the pre-demo checklist)."""
    from starlette.concurrency import run_in_threadpool

    user_snapshots = await run_in_threadpool(db.collection("argus_users").stream)
    triples: set[tuple[str, str, str | None]] = set()
    for user_snapshot in user_snapshots:
        uid = user_snapshot.id
        history_snapshots = await run_in_threadpool(
            db.collection("argus_users").document(uid).collection("confirmation_history").stream
        )
        for snapshot in history_snapshots:
            data = snapshot.to_dict()
            triples.add((uid, data["category"], data.get("provider")))
    return list(triples)


@router.post("/run-calibration")
async def run_calibration(
    db=Depends(get_firestore_client), _secret_ok: None = Depends(_verify_calibration_secret)
) -> dict:
    memory = MemoryAgent(db)
    agent = CalibrationAgent(memory)
    triples = await _collect_triples(db)
    created = await agent.run_for_all_users(triples)
    return {"proposals_created": created}
