import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Protocol

from google.cloud import firestore
from starlette.concurrency import run_in_threadpool

from app.core.pubsub import events_topic_path
from app.models.agent_events import EscalationEvent

logger = logging.getLogger(__name__)

#: How long two independent distress signals stay "concurrent enough" to
#: corroborate each other — chosen as a reasonable bound for genuinely
#: related signals (someone says something concerning, then a fall/alarm
#: sound follows within the same couple of minutes), not derived from any
#: real usage data. Tune once real usage exists (see pre-demo checklist).
_DISTRESS_SIGNAL_WINDOW = timedelta(seconds=120)


class NotificationSender(Protocol):
    async def send(self, event: EscalationEvent) -> None: ...


class LoggingNotificationSender:
    """Phase 1's NotificationSender: writes to Cloud Logging. A later phase
    swaps in a Twilio-backed sender once real credentials exist — this
    interface boundary means that swap touches one dependency wire-up, not
    Escalation Agent's logic."""

    async def send(self, event: EscalationEvent) -> None:
        logger.warning(
            "escalation_triggered",
            extra={"session_id": event.session_id, "uid": event.uid, "reason": event.reason, "signals": event.signals},
        )


class EscalationAgent:
    """A multi-signal rule check — never a single low-confidence signal
    alone — builds an EscalationEvent, persists it, publishes it, and
    notifies via the injected sender."""

    def __init__(self, db: firestore.Client, publisher, sender: NotificationSender) -> None:
        self._db = db
        self._publisher = publisher
        self._sender = sender
        self._pending_distress_signals: dict[str, dict[str, datetime]] = {}

    async def consider_distress_signal(
        self, *, session_id: str, uid: str, signal_type: str, reason: str
    ) -> EscalationEvent | None:
        """Never escalates on one signal type alone — a separate mechanism
        from escalate() itself, which stays the unconditional "fire it
        now" primitive check_for_divergence already uses for a completely
        different failure category (a stuck task, not physical distress)."""
        now = datetime.now(timezone.utc)
        session_signals = {
            t: ts for t, ts in self._pending_distress_signals.get(session_id, {}).items()
            if (now - ts) <= _DISTRESS_SIGNAL_WINDOW
        }
        session_signals[signal_type] = now

        if len(session_signals) < 2:
            self._pending_distress_signals[session_id] = session_signals
            return None

        del self._pending_distress_signals[session_id]
        return await self.escalate(session_id=session_id, uid=uid, reason=reason, signals=list(session_signals.keys()))

    async def escalate(self, *, session_id: str, uid: str, reason: str, signals: list[str]) -> EscalationEvent:
        event = EscalationEvent(
            session_id=session_id, uid=uid, reason=reason, signals=signals, triggered_at=datetime.now(timezone.utc)
        )
        doc_id = f"{session_id}-{int(event.triggered_at.timestamp())}"
        await run_in_threadpool(
            self._db.collection("argus_users").document(uid).collection("escalations").document(doc_id).set,
            event.model_dump(mode="json"),
        )
        topic_path = events_topic_path(self._publisher)
        await run_in_threadpool(self._publisher.publish(topic_path, json.dumps(event.model_dump(mode="json")).encode("utf-8")).result)
        await self._sender.send(event)
        return event
