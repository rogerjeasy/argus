from datetime import datetime, timezone

from google.cloud import firestore
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool


class StandingPermission(BaseModel):
    category: str
    threshold: float
    provider: str | None = None


class MemoryAgent:
    """Firestore CRUD for per-user personalization: verbosity/pace (Phase
    0's `/api/settings`, unchanged here), task history, and the
    standing-permissions document Guardrail reads. Every category starts
    with no standing permission — confirm-first by default."""

    def __init__(self, db: firestore.Client) -> None:
        self._db = db

    def _permissions_doc(self, uid: str):
        return self._db.collection("argus_users").document(uid).collection("permissions").document("standing")

    def _task_history_doc(self, uid: str, session_id: str):
        return self._db.collection("argus_users").document(uid).collection("task_history").document(session_id)

    async def get_standing_permissions(self, uid: str) -> list[StandingPermission]:
        snapshot = await run_in_threadpool(self._permissions_doc(uid).get)
        if not snapshot.exists:
            return []
        rules = snapshot.to_dict().get("rules", [])
        return [StandingPermission(**rule) for rule in rules]

    async def record_task_history(self, *, uid: str, session_id: str, summary: str) -> None:
        await run_in_threadpool(
            self._task_history_doc(uid, session_id).set,
            {"summary": summary, "recorded_at": datetime.now(timezone.utc).isoformat()},
        )
