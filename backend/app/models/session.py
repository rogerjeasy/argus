from datetime import datetime

from pydantic import BaseModel, Field


class SessionRecord(BaseModel):
    session_id: str
    uid: str
    started_at: datetime
    ended_at: datetime | None = None
    status: str = Field(default="active", pattern="^(active|closed|error)$")
