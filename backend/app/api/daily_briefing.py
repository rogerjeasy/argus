from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.agents.daily_briefing import DailyBriefingAgent
from app.agents.memory import MemoryAgent
from app.core.clients import get_firestore_client
from app.core.config import Settings, get_settings
from app.domains.transit.domain import TransitDomain
from app.domains.transit.registry import get_transit_domains

router = APIRouter(prefix="/internal", tags=["internal"])


def _verify_daily_briefing_secret(
    x_daily_briefing_secret: str = Header(default=""), settings: Settings = Depends(get_settings)
) -> None:
    # Fail-closed, same convention as _verify_calibration_secret
    # (app/api/calibration.py) — an empty configured secret never matches an
    # empty header.
    if (
        not settings.daily_briefing_job_shared_secret
        or x_daily_briefing_secret != settings.daily_briefing_job_shared_secret
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid daily briefing secret")


async def _get_transit_domains_dep(settings: Settings = Depends(get_settings)) -> list[TransitDomain]:
    """A thin, override-friendly wrapper — get_transit_domains() itself
    fetches real GTFS static feeds over the network on first call, so tests
    override this dependency instead of calling the real thing (mirrors
    test_ws_session.py's own reasoning for why build_orchestrator is always
    mocked in that file)."""
    return await get_transit_domains(settings)


async def _collect_uids(db) -> list[str]:
    from starlette.concurrency import run_in_threadpool

    user_snapshots = await run_in_threadpool(db.collection("argus_users").stream)
    return [s.id for s in user_snapshots]


@router.post("/run-daily-briefing")
async def run_daily_briefing(
    db=Depends(get_firestore_client),
    transit_domains: list[TransitDomain] = Depends(_get_transit_domains_dep),
    _secret_ok: None = Depends(_verify_daily_briefing_secret),
) -> dict:
    memory = MemoryAgent(db)
    agent = DailyBriefingAgent(memory, {d.domain_id: d for d in transit_domains})
    uids = await _collect_uids(db)
    created = await agent.run_for_all_uids(uids)
    return {"briefings_created": created}
