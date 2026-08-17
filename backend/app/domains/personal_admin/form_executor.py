import io
import logging

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.domains.personal_admin.models import ExecutorOutcome, FormField, FormFillOutcome
from app.integrations.storage_client import StorageClient

logger = logging.getLogger(__name__)


def _render_receipt_pdf(fields: list[FormField]) -> bytes:
    """A generated text-based receipt/summary — field/value pairs, not an
    overlay on the photographed form's own layout (design doc revision note
    2: overlaying onto arbitrary form layouts needs per-field bounding
    boxes the extraction step doesn't produce, and risks looking worse in a
    demo than a clean, fully-controlled document)."""
    buffer = io.BytesIO()
    doc = canvas.Canvas(buffer, pagesize=letter)
    doc.setFont("Helvetica-Bold", 14)
    doc.drawString(72, 740, "Argus Form Summary")
    doc.setFont("Helvetica", 11)
    y = 700
    for field in fields:
        doc.drawString(72, y, f"{field.label}: {field.value or '(not provided)'}")
        y -= 20
    doc.showPage()
    doc.save()
    return buffer.getvalue()


class FormExecutor:
    """Satisfies Executor.execute(payload: dict) -> dict. By the time this
    runs, PersonalAdminDomain.build_executor_payload has already done
    schema extraction, autofill, and (via the orchestrator's field-request
    pause) resolved the one field that needed a user-provided value — this
    only ever receives an already-fully-resolved `fields` list, never a
    MemoryAgent reference (design rule 3, enforced by omission, same as
    CallExecutor)."""

    def __init__(self, storage: StorageClient, *, bucket_path_prefix: str = "personal_admin_forms") -> None:
        self._storage = storage
        self._prefix = bucket_path_prefix

    async def execute(self, payload: dict) -> dict:
        step_id = payload["step_id"]
        fields = [FormField(**f) for f in payload.get("fields", [])]

        pdf_bytes = _render_receipt_pdf(fields)
        blob_path = f"{self._prefix}/{step_id}.pdf"
        try:
            signed_url = await self._storage.upload_and_sign(blob_path, pdf_bytes, content_type="application/pdf")
        except Exception:
            logger.exception("form_executor_upload_failed", extra={"step_id": step_id})
            return ExecutorOutcome(
                step_id=step_id, status="failed", structured_data={}, summary_text="I couldn't generate the form's PDF."
            ).model_dump()

        outcome = FormFillOutcome(status="pdf_ready", fields=fields, missing_field=None, output_url=signed_url)
        return ExecutorOutcome(
            step_id=step_id,
            status="success",
            structured_data=outcome.model_dump(),
            summary_text=f"I've filled out the form and saved it — {len(fields)} field(s) completed.",
        ).model_dump()
