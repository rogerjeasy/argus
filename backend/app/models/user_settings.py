from pydantic import BaseModel, Field


class UserSettings(BaseModel):
    verbosity: str = Field(default="normal", pattern="^(terse|normal|verbose)$")
    pace: str = Field(default="normal", pattern="^(slow|normal|fast)$")
    #: Off by default — always-on ambient audio monitoring carries real
    #: privacy weight no other feature in this system carries (master spec
    #: §7, §15; design doc §5). No code path may flip this except an
    #: explicit user PUT.
    audio_perception_enabled: bool = False


class UserSettingsUpdate(BaseModel):
    verbosity: str | None = Field(default=None, pattern="^(terse|normal|verbose)$")
    pace: str | None = Field(default=None, pattern="^(slow|normal|fast)$")
    audio_perception_enabled: bool | None = None
