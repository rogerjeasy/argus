from fastapi import APIRouter, Depends
from google.cloud import firestore
from pydantic import BaseModel

from app.agents.memory import MemoryAgent
from app.core.auth import AuthenticatedUser, get_current_user
from app.core.clients import get_firestore_client

router = APIRouter(prefix="/api", tags=["history"])


class SessionHistoryEntry(BaseModel):
    session_id: str
    summary: str
    started_at: str | None = None
    ended_at: str | None = None
    recorded_at: str | None = None


@router.get("/history", response_model=list[SessionHistoryEntry])
async def get_history(
    limit: int = 20,
    user: AuthenticatedUser = Depends(get_current_user),
    db: firestore.Client = Depends(get_firestore_client),
) -> list[SessionHistoryEntry]:
    rows = await MemoryAgent(db).get_session_history(user.uid, limit=min(limit, 100))
    return [SessionHistoryEntry(**{k: row.get(k) for k in SessionHistoryEntry.model_fields}) for row in rows]
