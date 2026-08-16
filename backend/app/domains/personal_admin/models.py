from pydantic import BaseModel, Field


class TriageResult(BaseModel):
    category: str      # "bill" | "medical" | "legal" | "junk" | "scam-suspect"
    urgency: str = Field(pattern="^(low|normal|high)$")
    subflow: str = Field(pattern="^(call|form|inform-only)$")
    confidence: float


class ExecutorOutcome(BaseModel):
    """What every Executor.execute() call's returned dict is validated into
    before the orchestrator trusts it — master spec §14's mitigation for a
    hallucinated or malformed executor outcome."""

    step_id: str
    status: str = Field(pattern="^(success|failed|needs_retry)$")
    structured_data: dict
    summary_text: str


class CallGoal(BaseModel):
    target_phone_number: str
    purpose: str
    structured_question: str


class CallOutcome(BaseModel):
    status: str = Field(pattern="^(connected_resolved|connected_unresolved|busy|no_answer|failed)$")
    structured_data: dict
    transcript_summary: str
    confidence: float
