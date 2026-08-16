import asyncio

from app.domains.personal_admin.models import CallGoal, CallOutcome
from app.integrations.twilio_client import TwilioClient


class CallSessionRegistry:
    """In-process rendezvous between CallExecutor.execute() (which places a
    call and needs to await its eventual outcome) and the two independent
    inbound connections that can report that outcome — the Twilio
    status-callback webhook (Task 13) and the Media Stream WS handler
    (Task 12). Keyed by step_id, generated before the call is placed, not
    by Twilio's own call_sid (unknown until place_call() returns)."""

    def __init__(self) -> None:
        self._call_goals: dict[str, CallGoal] = {}
        self._twilio_clients: dict[str, TwilioClient] = {}
        self._call_sids: dict[str, str] = {}
        self._outcome_futures: dict[str, asyncio.Future] = {}

    def register(self, step_id: str, call_goal: CallGoal, twilio: TwilioClient) -> None:
        # Deliberately no asyncio.Future created here — register() is a
        # plain synchronous call (CallExecutor.execute() calls it before
        # its own first await), and asyncio.get_event_loop() raises when
        # there is no running loop yet. The future is created lazily, on
        # first access from wait_for_outcome()/resolve_outcome(), both of
        # which only ever run inside a running loop.
        self._call_goals[step_id] = call_goal
        self._twilio_clients[step_id] = twilio

    def get_call_goal(self, step_id: str) -> CallGoal | None:
        return self._call_goals.get(step_id)

    def get_twilio_client(self, step_id: str) -> TwilioClient | None:
        return self._twilio_clients.get(step_id)

    def set_call_sid(self, step_id: str, call_sid: str) -> None:
        self._call_sids[step_id] = call_sid

    def get_call_sid(self, step_id: str) -> str | None:
        return self._call_sids.get(step_id)

    def _get_or_create_future(self, step_id: str) -> asyncio.Future:
        future = self._outcome_futures.get(step_id)
        if future is None:
            future = asyncio.get_event_loop().create_future()
            self._outcome_futures[step_id] = future
        return future

    async def wait_for_outcome(self, step_id: str, timeout: float) -> CallOutcome:
        if step_id not in self._call_goals:
            raise TimeoutError(f"no registered call session for step_id={step_id!r}")
        future = self._get_or_create_future(step_id)
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError as exc:
            raise TimeoutError(f"call for step_id={step_id!r} did not resolve within {timeout}s") from exc

    def resolve_outcome(self, step_id: str, outcome: CallOutcome) -> None:
        future = self._get_or_create_future(step_id)
        if not future.done():
            future.set_result(outcome)

    def discard(self, step_id: str) -> None:
        self._call_goals.pop(step_id, None)
        self._twilio_clients.pop(step_id, None)
        self._call_sids.pop(step_id, None)
        self._outcome_futures.pop(step_id, None)
