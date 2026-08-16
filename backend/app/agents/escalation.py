import json
import logging
from datetime import datetime, timezone
from typing import Protocol

from google.cloud import firestore
from starlette.concurrency import run_in_threadpool

from app.core.pubsub import events_topic_path
from app.models.agent_events import EscalationEvent

logger = logging.getLogger(__name__)


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
