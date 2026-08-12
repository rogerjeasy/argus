from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.auth import InvalidTokenError, get_current_user, verify_id_token_string


def test_verify_id_token_string_returns_authenticated_user() -> None:
    with patch("app.core.auth.firebase_auth.verify_id_token", return_value={"uid": "user-1", "email": "a@example.com"}):
        with patch("app.core.auth._init_firebase_app"):
            user = verify_id_token_string("valid-token")
    assert user.uid == "user-1"
    assert user.email == "a@example.com"


def test_verify_id_token_string_raises_on_invalid_token() -> None:
    with patch("app.core.auth.firebase_auth.verify_id_token", side_effect=ValueError("bad token")):
        with patch("app.core.auth._init_firebase_app"):
            with pytest.raises(InvalidTokenError):
                verify_id_token_string("bad-token")


@pytest.mark.asyncio
async def test_get_current_user_raises_401_when_no_credentials() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=None)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_raises_401_on_invalid_token() -> None:
    """Test that get_current_user catches InvalidTokenError and re-raises as 401."""
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid-token")
    with patch("app.core.auth.verify_id_token_string", side_effect=InvalidTokenError("Token expired")):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=creds)
    assert exc_info.value.status_code == 401
