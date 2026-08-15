from fastapi import APIRouter, Depends
from google.cloud import firestore

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.clients import get_firestore_client
from app.models.user_settings import UserSettings, UserSettingsUpdate

router = APIRouter(prefix="/api", tags=["settings"])


def _settings_doc(db: firestore.Client, uid: str):
    return db.collection("argus_users").document(uid).collection("settings").document("preferences")


@router.get("/settings", response_model=UserSettings)
def get_user_settings(
    user: AuthenticatedUser = Depends(get_current_user),
    db: firestore.Client = Depends(get_firestore_client),
) -> UserSettings:
    snapshot = _settings_doc(db, user.uid).get()
    if not snapshot.exists:
        return UserSettings()
    return UserSettings(**snapshot.to_dict())


@router.put("/settings", response_model=UserSettings)
def update_user_settings(
    payload: UserSettingsUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: firestore.Client = Depends(get_firestore_client),
) -> UserSettings:
    doc_ref = _settings_doc(db, user.uid)
    snapshot = doc_ref.get()
    current = UserSettings(**snapshot.to_dict()) if snapshot.exists else UserSettings()
    updated = current.model_copy(update=payload.model_dump(exclude_none=True))
    doc_ref.set(updated.model_dump())
    return updated
