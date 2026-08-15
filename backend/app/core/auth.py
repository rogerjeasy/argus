import firebase_admin
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials

from app.core.config import get_settings

_bearer_scheme = HTTPBearer(auto_error=False)


class InvalidTokenError(Exception):
    """Raised when a Firebase ID token fails verification."""


class AuthenticatedUser:
    def __init__(self, uid: str, email: str | None, provider: str | None = None) -> None:
        self.uid = uid
        self.email = email
        self.provider = provider


def _init_firebase_app() -> firebase_admin.App:
    try:
        return firebase_admin.get_app()
    except ValueError:
        settings = get_settings()
        cred = credentials.ApplicationDefault()
        return firebase_admin.initialize_app(cred, {"projectId": settings.firebase_project_id})


def verify_id_token_string(token: str) -> AuthenticatedUser:
    _init_firebase_app()
    try:
        decoded = firebase_auth.verify_id_token(token)
    except Exception as exc:
        raise InvalidTokenError("Invalid or expired Firebase ID token") from exc
    provider = decoded.get("firebase", {}).get("sign_in_provider")
    return AuthenticatedUser(uid=decoded["uid"], email=decoded.get("email"), provider=provider)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthenticatedUser:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    try:
        return verify_id_token_string(credentials.credentials)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
