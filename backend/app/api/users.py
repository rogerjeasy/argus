from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from google.cloud import firestore

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.clients import get_firestore_client
from app.models.user_profile import UserProfile, UserProfileUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


def _profile_doc(db: firestore.Client, uid: str):
    return db.collection("argus_users").document(uid)


@router.put("/me", response_model=UserProfile)
def sync_current_user_profile(
    payload: UserProfileUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: firestore.Client = Depends(get_firestore_client),
) -> UserProfile:
    doc_ref = _profile_doc(db, user.uid)
    snapshot = doc_ref.get()
    existing = snapshot.to_dict() if snapshot.exists else {}
    now = datetime.now(timezone.utc).isoformat()

    profile = UserProfile(
        uid=user.uid,
        email=user.email,
        display_name=payload.display_name if payload.display_name is not None else existing.get("display_name"),
        photo_url=payload.photo_url if payload.photo_url is not None else existing.get("photo_url"),
        provider=user.provider,
        created_at=existing.get("created_at", now),
        last_login_at=now,
    )
    doc_ref.set(profile.model_dump(mode="json"))
    return profile
