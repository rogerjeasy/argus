import base64
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from google.cloud import firestore, kms
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.models.trusted_contact import TrustedContact
from app.models.user_settings import UserSettings

if TYPE_CHECKING:
    # Real import only for type checkers — a top-level runtime import here
    # would be circular (app.agents.calibration imports MemoryAgent from
    # this module). Every actual runtime use is a local import instead.
    from app.agents.calibration import CalibrationProposal


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


class RegularRoute(BaseModel):
    domain_id: str
    goal_text: str


class DailyBriefing(BaseModel):
    summary_text: str
    route_description: str
    status: str = "pending_delivery"


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

    def _settings_doc(self, uid: str):
        return self._db.collection("argus_users").document(uid).collection("settings").document("preferences")

    def _regular_routes_doc(self, uid: str):
        return self._db.collection("argus_users").document(uid).collection("transit").document("regular_routes")

    def _trusted_contact_doc(self, uid: str):
        return self._db.collection("argus_users").document(uid).collection("escalation").document("trusted_contact")

    def _notes_doc(self, uid: str):
        return self._db.collection("argus_users").document(uid).collection("memory").document("notes")

    async def remember(self, uid: str, key: str, value: str) -> None:
        """A free-form per-user key/value store the live agent writes to
        when the user says "remember ..." — kept apart from the typed
        profile/routes/permissions stores so an arbitrary key can't collide
        with a schema'd field."""
        snapshot = await run_in_threadpool(self._notes_doc(uid).get)
        notes = snapshot.to_dict() if snapshot.exists else {}
        notes[key] = value
        await run_in_threadpool(self._notes_doc(uid).set, notes)

    async def recall(self, uid: str, key: str) -> str | None:
        snapshot = await run_in_threadpool(self._notes_doc(uid).get)
        if not snapshot.exists:
            return None
        return snapshot.to_dict().get(key)

    async def get_user_settings(self, uid: str) -> UserSettings:
        snapshot = await run_in_threadpool(self._settings_doc(uid).get)
        if not snapshot.exists:
            return UserSettings()
        return UserSettings(**snapshot.to_dict())

    async def get_regular_routes(self, uid: str) -> list[RegularRoute]:
        snapshot = await run_in_threadpool(self._regular_routes_doc(uid).get)
        if not snapshot.exists:
            return []
        return [RegularRoute(**r) for r in snapshot.to_dict().get("routes", [])]

    async def add_regular_route(self, uid: str, route: RegularRoute) -> None:
        existing = await self.get_regular_routes(uid)
        updated = [*existing, route]
        await run_in_threadpool(
            self._regular_routes_doc(uid).set, {"routes": [r.model_dump() for r in updated]}
        )

    async def get_trusted_contact(self, uid: str) -> TrustedContact | None:
        snapshot = await run_in_threadpool(self._trusted_contact_doc(uid).get)
        if not snapshot.exists:
            return None
        return TrustedContact(**snapshot.to_dict())

    async def set_trusted_contact(self, uid: str, contact: TrustedContact) -> None:
        await run_in_threadpool(self._trusted_contact_doc(uid).set, contact.model_dump())

    async def store_daily_briefing(self, uid: str, briefing: "DailyBriefing") -> str:
        import uuid
        briefing_id = str(uuid.uuid4())
        await run_in_threadpool(
            self._daily_briefings_collection(uid).document(briefing_id).set, briefing.model_dump()
        )
        return briefing_id

    async def get_pending_daily_briefing(self, uid: str) -> "tuple[str, DailyBriefing] | None":
        snapshots = await run_in_threadpool(self._daily_briefings_collection(uid).stream)
        for snapshot in snapshots:
            data = snapshot.to_dict()
            if data.get("status") == "pending_delivery":
                return snapshot.id, DailyBriefing(**data)
        return None

    async def mark_daily_briefing_delivered(self, uid: str, briefing_id: str) -> None:
        await run_in_threadpool(
            self._daily_briefings_collection(uid).document(briefing_id).update, {"status": "delivered"}
        )

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

    def _calibration_proposals_collection(self, uid: str):
        return self._db.collection("argus_users").document(uid).collection("calibration_proposals")

    def _daily_briefings_collection(self, uid: str):
        return self._db.collection("argus_users").document(uid).collection("daily_briefings")

    async def store_calibration_proposal(self, uid: str, proposal: "CalibrationProposal") -> str:
        import uuid
        proposal_id = str(uuid.uuid4())
        await run_in_threadpool(
            self._calibration_proposals_collection(uid).document(proposal_id).set, proposal.model_dump()
        )
        return proposal_id

    async def get_pending_calibration_proposal(self, uid: str) -> "tuple[str, CalibrationProposal] | None":
        from app.agents.calibration import CalibrationProposal
        snapshots = await run_in_threadpool(self._calibration_proposals_collection(uid).stream)
        for snapshot in snapshots:
            data = snapshot.to_dict()
            if data.get("status") == "pending_user_opt_in":
                return snapshot.id, CalibrationProposal(**data)
        return None

    async def mark_calibration_proposal_dismissed(self, uid: str, proposal_id: str) -> None:
        await run_in_threadpool(
            self._calibration_proposals_collection(uid).document(proposal_id).update, {"status": "dismissed"}
        )

    async def apply_calibration_proposal_to_standing_permissions(self, uid: str, proposal_id: str) -> None:
        """The only method in this codebase Self-Calibration's proposal
        flow can reach that writes to _permissions_doc — reached only from
        TaskOrchestrator.resolve_confirmation's "calibration" branch, itself
        reachable only after an explicit accepted=True from the user.
        CalibrationAgent has no reference to this method (see
        test_calibration_agent.py's write-scope-separation test)."""
        from app.agents.guardrail import MIN_CONFIDENCE_FLOOR  # local: guardrail.py imports StandingPermission
        # from this module, so a top-level import here would be circular.
        snapshot = await run_in_threadpool(self._calibration_proposals_collection(uid).document(proposal_id).get)
        proposal = snapshot.to_dict()
        permissions = await self.get_standing_permissions(uid)
        permissions.append(StandingPermission(
            category=proposal["category"], provider=proposal.get("provider"), threshold=MIN_CONFIDENCE_FLOOR
        ))
        await run_in_threadpool(
            self._permissions_doc(uid).set, {"rules": [p.model_dump() for p in permissions]}
        )
        await self.mark_calibration_proposal_dismissed(uid, proposal_id)

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
