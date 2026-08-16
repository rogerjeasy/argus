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


class FormField(BaseModel):
    name: str
    label: str
    value: str | None
    source: str = Field(pattern="^(memory_profile|user_provided|unresolved)$")


class FormFillOutcome(BaseModel):
    status: str = Field(pattern="^(submitted|pdf_ready|needs_user_input)$")
    fields: list[FormField]
    missing_field: str | None
    output_url: str | None  # Cloud Storage signed URL
