from pydantic import BaseModel, Field


class UserSettings(BaseModel):
    verbosity: str = Field(default="normal", pattern="^(terse|normal|verbose)$")
    pace: str = Field(default="normal", pattern="^(slow|normal|fast)$")
    #: Off by default — always-on ambient audio monitoring carries real
    #: privacy weight no other feature in this system carries (master spec
    #: §7, §15; design doc §5). No code path may flip this except an
    #: explicit user PUT.
    audio_perception_enabled: bool = False
    #: BCP-47 language code spoken guidance is translated into before
    #: Gemini Live speaks it (fixes Phase 2 design doc §7's own documented
    #: gap — see Phase 5 plan Tasks 1-7). "en" is the passthrough default:
    #: _speak_and_send_guidance never calls the translation client when
    #: this is "en", the same cost-consciousness reasoning as every other
    #: optional integration in this project.
    language_preference: str = "en"


class UserSettingsUpdate(BaseModel):
    verbosity: str | None = Field(default=None, pattern="^(terse|normal|verbose)$")
    pace: str | None = Field(default=None, pattern="^(slow|normal|fast)$")
    audio_perception_enabled: bool | None = None
    language_preference: str | None = None
