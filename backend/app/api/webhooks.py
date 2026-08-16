import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from twilio.request_validator import RequestValidator

from app.core.cloud_tasks import enqueue_call_retry, get_cloud_tasks_client
from app.core.config import get_settings
from app.domains.personal_admin.call_session_registry import CallSessionRegistry
from app.domains.personal_admin.models import CallOutcome
from app.ws.twilio_media import get_call_session_registry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks/twilio", tags=["webhooks"])

#: Twilio call statuses that mean the call never connected — resolved
#: directly here, never by the Media Stream handler (which only ever opens
#: once a call is answered). Anything else (answered, completed) is left to
#: that handler, which is the one that actually knows the real outcome.
_NEVER_CONNECTED_STATUSES = {"busy", "no-answer", "failed"}


def _validate_twilio_signature(request: Request, form: dict) -> bool:
    settings = get_settings()
    validator = RequestValidator(settings.twilio_auth_token)
    signature = request.headers.get("X-Twilio-Signature", "")
    return validator.validate(str(request.url), form, signature)


@router.post("/call-status")
async def call_status_webhook(
    request: Request, step_id: str, registry: CallSessionRegistry = Depends(get_call_session_registry),
) -> dict:
    form = dict(await request.form())
    if not _validate_twilio_signature(request, form):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid Twilio signature")

    call_status = str(form.get("CallStatus", ""))
    normalized = call_status.replace("-", "_")  # Twilio sends "no-answer"; CallOutcome uses "no_answer"
    if normalized not in {"busy", "no_answer", "failed"}:
        return {"status": "ignored", "call_status": call_status}

    registry.resolve_outcome(
        step_id,
        CallOutcome(status=normalized, structured_data={}, transcript_summary=f"Call status: {call_status}.", confidence=1.0),
    )

    settings = get_settings()
    call_goal = registry.get_call_goal(step_id)
    payload = {"step_id": step_id, "call_goal": call_goal.model_dump() if call_goal else {}}
    enqueue_call_retry(
        get_cloud_tasks_client(),
        project=settings.gcp_project_id, location=settings.cloud_tasks_location, queue=settings.cloud_tasks_queue,
        step_id=step_id, payload=payload,
        retry_endpoint_url=f"{settings.public_base_url}/internal/retry-call/{step_id}",
    )
    return {"status": "resolved", "call_status": call_status}


#: A separate router (own prefix, own tag) in the same file: colocated with
#: the webhook that enqueues its target URL, but semantically an internal
#: Cloud Tasks target, not a Twilio-facing webhook.
internal_router = APIRouter(prefix="/internal", tags=["internal"])


def get_call_executor(
    settings=Depends(get_settings), registry: CallSessionRegistry = Depends(get_call_session_registry),
):
    from app.domains.personal_admin.call_executor import CallExecutor
    from app.integrations.twilio_client import RealTwilioClient

    twilio = RealTwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
    return CallExecutor(twilio, registry, from_number=settings.twilio_from_number, public_base_url=settings.public_base_url)


@internal_router.post("/retry-call/{step_id}")
async def retry_call(step_id: str, request: Request, executor=Depends(get_call_executor)) -> dict:
    """Cloud Tasks' own HTTP target for a retried call. The request body is
    exactly what enqueue_call_retry() serialized (core/cloud_tasks.py) — the
    original call_goal — so this replays CallExecutor.execute() rather than
    needing to reconstruct anything from Firestore."""
    payload = await request.json()
    return await executor.execute(payload)
