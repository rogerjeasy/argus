from fastapi import APIRouter, Depends
from google.cloud import firestore

from app.agents.memory import MemoryAgent
from app.core.auth import AuthenticatedUser, get_current_user
from app.core.clients import get_firestore_client
from app.models.trusted_contact import TrustedContact

router = APIRouter(prefix="/api", tags=["trusted-contact"])


@router.get("/trusted-contact", response_model=TrustedContact | None)
async def get_trusted_contact(
    user: AuthenticatedUser = Depends(get_current_user),
    db: firestore.Client = Depends(get_firestore_client),
) -> TrustedContact | None:
    return await MemoryAgent(db).get_trusted_contact(user.uid)


@router.put("/trusted-contact", response_model=TrustedContact)
async def put_trusted_contact(
    payload: TrustedContact,
    user: AuthenticatedUser = Depends(get_current_user),
    db: firestore.Client = Depends(get_firestore_client),
) -> TrustedContact:
    memory = MemoryAgent(db)
    await memory.set_trusted_contact(user.uid, payload)
    return payload
