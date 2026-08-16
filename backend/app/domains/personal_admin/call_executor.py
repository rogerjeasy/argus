import logging

from app.domains.personal_admin.call_session_registry import CallSessionRegistry
from app.domains.personal_admin.models import CallGoal, ExecutorOutcome
from app.integrations.twilio_client import TwilioClient

logger = logging.getLogger(__name__)

_STATUS_TO_EXECUTOR_STATUS = {
    "connected_resolved": "success",
    "connected_unresolved": "needs_retry",
    "busy": "needs_retry",
    "no_answer": "needs_retry",
    "failed": "failed",
}


class CallExecutor:
    """Satisfies Executor.execute(payload: dict) -> dict. Places a real call
    through TwilioClient, then awaits its outcome via CallSessionRegistry —
    resolved either by the Media Stream WS handler (Task 12, a call that
    connected) or the Twilio status-callback webhook (Task 13, a call that
    never connected: busy/no-answer/failed)."""

    def __init__(
        self, twilio: TwilioClient, registry: CallSessionRegistry, *,
        from_number: str, public_base_url: str, call_timeout_seconds: float = 90.0,
    ) -> None:
        self._twilio = twilio
        self._registry = registry
        self._from_number = from_number
        self._public_base_url = public_base_url.rstrip("/")
        self._call_timeout_seconds = call_timeout_seconds

    async def execute(self, payload: dict) -> dict:
        step_id = payload["step_id"]
        call_goal = CallGoal(**payload["call_goal"])
        self._registry.register(step_id, call_goal, self._twilio)

        stream_url = f"{self._public_base_url.replace('https://', 'wss://').replace('http://', 'ws://')}/ws/twilio-media/{step_id}"
        twiml = f'<Response><Connect><Stream url="{stream_url}" /></Connect></Response>'
        status_callback_url = f"{self._public_base_url}/webhooks/twilio/call-status?step_id={step_id}"

        try:
            call_sid = await self._twilio.place_call(
                to=call_goal.target_phone_number, from_=self._from_number, twiml=twiml, status_callback_url=status_callback_url
            )
            self._registry.set_call_sid(step_id, call_sid)
        except Exception:
            logger.exception("call_executor_place_call_failed", extra={"step_id": step_id})
            self._registry.discard(step_id)
            return ExecutorOutcome(
                step_id=step_id, status="failed", structured_data={}, summary_text="I couldn't place the call."
            ).model_dump()

        try:
            outcome = await self._registry.wait_for_outcome(step_id, timeout=self._call_timeout_seconds)
        except TimeoutError:
            return ExecutorOutcome(
                step_id=step_id, status="failed", structured_data={}, summary_text="The call timed out before resolving."
            ).model_dump()
        finally:
            self._registry.discard(step_id)

        return ExecutorOutcome(
            step_id=step_id,
            status=_STATUS_TO_EXECUTOR_STATUS.get(outcome.status, "failed"),
            structured_data=outcome.structured_data,
            summary_text=outcome.transcript_summary,
        ).model_dump()
