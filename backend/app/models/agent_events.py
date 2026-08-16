from datetime import datetime

from pydantic import BaseModel, Field


class PerceivedGoal(BaseModel):
    session_id: str
    uid: str
    raw_text: str


class SceneSignal(BaseModel):
    session_id: str
    kind: str  # e.g. "signage_text" — not yet produced in Phase 1, reserved for camera-based domains
    text: str
    confidence: float


class FramingAssessment(BaseModel):
    session_id: str
    text_detected: bool
    position: str = Field(pattern="^(left|right|center|too-close|too-far|none)$")


class GroundedFact(BaseModel):
    key: str
    value: str
    source: str  # "stub_feed" in Phase 1; "gtfs_realtime" etc. from later phases
    confidence: float
    as_of: datetime


class PlanStep(BaseModel):
    step_id: str
    domain_id: str
    description: str
    action_type: str = Field(pattern="^(guidance|execute)$")  # "execute" unused until a later phase
    requires_confirmation: bool
    payload: dict


class GuardrailDecision(BaseModel):
    step_id: str
    decision: str = Field(pattern="^(approved|requires_confirmation|requires_field_input|denied)$")
    reason: str
    #: Only set when decision == "requires_field_input" — the human-readable
    #: label of the one form field still needing a value (design doc §4a.1).
    field_label: str | None = None


class GuidanceOutput(BaseModel):
    session_id: str
    text: str
    haptic_pattern: str | None = Field(default=None, pattern="^(pattern-forward|pattern-redirect|pattern-urgent)$")
    earcon: str | None = Field(
        default=None,
        pattern="^(earcon-plan-updated|earcon-low-confidence|earcon-task-complete|earcon-escalation)$",
    )


class DivergenceSignal(BaseModel):
    session_id: str
    plan_step_id: str
    expected: str
    observed: str
    source: str


class EscalationEvent(BaseModel):
    session_id: str
    uid: str
    reason: str
    signals: list[str]
    triggered_at: datetime
