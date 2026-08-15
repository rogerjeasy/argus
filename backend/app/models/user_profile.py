from datetime import datetime

from pydantic import BaseModel


class UserProfile(BaseModel):
    uid: str
    email: str | None = None
    display_name: str | None = None
    photo_url: str | None = None
    provider: str | None = None
    created_at: datetime
    last_login_at: datetime


class UserProfileUpdate(BaseModel):
    display_name: str | None = None
    photo_url: str | None = None
