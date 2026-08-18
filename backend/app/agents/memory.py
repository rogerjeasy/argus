import base64
from datetime import datetime, timezone

from google.cloud import firestore, kms
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings


class StandingPermission(BaseModel):
    category: str
    threshold: float
    provider: str | None = None


class ConfirmationOutcome(BaseModel):
    category: str
    provider: str | None
    decision: str  # "approved" | "denied"
    decided_at: str  # ISO 8601, matches record_task_history's own convention


class ProviderContact(BaseModel):
    name: str
    phone_number: str
    category: str


class PersonalAdminProfile(BaseModel):
    known_providers: list[ProviderContact] = []
    standing_payment_threshold_cents: int | None = None
    full_name: str | None = None
    date_of_birth: str | None = None
    insurance_member_id: str | None = None


#: Medical- and financial-adjacent fields only — see design doc §10. Every
#: other PersonalAdminProfile field is stored as plaintext.
_SENSITIVE_PROFILE_FIELDS = ("insurance_member_id", "date_of_birth")


class MemoryAgent:
    """Firestore CRUD for per-user personalization: verbosity/pace (Phase
    0's `/api/settings`, unchanged here), task history, the
    standing-permissions document Guardrail reads, and (Phase 3) the
    Personal Admin profile — the user's own known providers and identity
    fields, the one thing PersonalAdminDomain grounds against instead of an
    external feed. Every category starts with no standing permission —
    confirm-first by default."""

    def __init__(self, db: firestore.Client, kms: "kms.KeyManagementServiceClient | None" = None) -> None:
        self._db = db
        self._kms = kms

    def _permissions_doc(self, uid: str):
        return self._db.collection("argus_users").document(uid).collection("permissions").document("standing")

    def _task_history_doc(self, uid: str, session_id: str):
        return self._db.collection("argus_users").document(uid).collection("task_history").document(session_id)

    def _profile_doc(self, uid: str):
        return self._db.collection("argus_users").document(uid).collection("personal_admin").document("profile")

    def _confirmation_history_collection(self, uid: str):
        return self._db.collection("argus_users").document(uid).collection("confirmation_history")

    async def record_confirmation_outcome(
        self, uid: str, *, category: str, provider: str | None, decision: str
    ) -> None:
        import uuid
        doc_id = str(uuid.uuid4())
        await run_in_threadpool(
            self._confirmation_history_collection(uid).document(doc_id).set,
            {
                "category": category, "provider": provider, "decision": decision,
                "decided_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def get_confirmation_history(
        self, uid: str, *, category: str, provider: str | None
    ) -> list[ConfirmationOutcome]:
        snapshots = await run_in_threadpool(self._confirmation_history_collection(uid).stream)
        return [
            ConfirmationOutcome(**s.to_dict())
            for s in snapshots
            if s.to_dict().get("category") == category and s.to_dict().get("provider") == provider
        ]

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

    async def get_profile(self, uid: str) -> PersonalAdminProfile:
        snapshot = await run_in_threadpool(self._profile_doc(uid).get)
        if not snapshot.exists:
            return PersonalAdminProfile()
        data = dict(snapshot.to_dict())
        for field in _SENSITIVE_PROFILE_FIELDS:
            if data.get(field):
                data[field] = await self._decrypt(data[field])
        return PersonalAdminProfile(**data)

    async def update_profile(self, uid: str, profile: PersonalAdminProfile) -> None:
        data = profile.model_dump()
        for field in _SENSITIVE_PROFILE_FIELDS:
            if data.get(field):
                data[field] = await self._encrypt(data[field])
        await run_in_threadpool(self._profile_doc(uid).set, data)

    def _kms_key_name(self) -> str:
        return get_settings().kms_key_name

    async def _encrypt(self, value: str) -> str:
        key_name = self._kms_key_name()
        if not key_name or self._kms is None:
            return value
        response = await run_in_threadpool(
            self._kms.encrypt, request={"name": key_name, "plaintext": value.encode("utf-8")}
        )
        return base64.b64encode(response.ciphertext).decode("ascii")

    async def _decrypt(self, value: str) -> str:
        key_name = self._kms_key_name()
        if not key_name or self._kms is None:
            return value
        response = await run_in_threadpool(
            self._kms.decrypt, request={"name": key_name, "ciphertext": base64.b64decode(value)}
        )
        return response.plaintext.decode("utf-8")
