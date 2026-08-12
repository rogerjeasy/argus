from pydantic import BaseModel, Field


class UserSettings(BaseModel):
    verbosity: str = Field(default="normal", pattern="^(terse|normal|verbose)$")
    pace: str = Field(default="normal", pattern="^(slow|normal|fast)$")


class UserSettingsUpdate(BaseModel):
    verbosity: str | None = Field(default=None, pattern="^(terse|normal|verbose)$")
    pace: str | None = Field(default=None, pattern="^(slow|normal|fast)$")
