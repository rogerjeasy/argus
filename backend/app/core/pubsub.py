from functools import lru_cache

from google.cloud import pubsub_v1

from app.core.config import get_settings


class _LazyPublisherClient:
    """`pubsub_v1.PublisherClient()` resolves GCP credentials synchronously
    at construction time. `build_orchestrator()` wires this client into
    every WS session's `EscalationAgent`, regardless of whether that
    session ever actually escalates — constructing the real client eagerly
    would mean every session pays credential-resolution cost (and, in an
    environment with no ambient GCP credentials at all, fails outright)
    just to be ready for the rare escalation path. Defer construction to
    the first real publish."""

    def __init__(self) -> None:
        self._client: pubsub_v1.PublisherClient | None = None

    def _real_client(self) -> pubsub_v1.PublisherClient:
        if self._client is None:
            self._client = pubsub_v1.PublisherClient()
        return self._client

    def publish(self, topic_path: str, data: bytes):
        return self._real_client().publish(topic_path, data)

    def topic_path(self, project: str, topic: str) -> str:
        return self._real_client().topic_path(project, topic)


@lru_cache
def get_publisher_client() -> _LazyPublisherClient:
    return _LazyPublisherClient()


def events_topic_path(client: _LazyPublisherClient) -> str:
    settings = get_settings()
    return client.topic_path(settings.gcp_project_id, "argus-events")
