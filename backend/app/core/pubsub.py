from functools import lru_cache

from google.cloud import pubsub_v1

from app.core.config import get_settings


@lru_cache
def get_publisher_client() -> pubsub_v1.PublisherClient:
    return pubsub_v1.PublisherClient()


def events_topic_path(client: pubsub_v1.PublisherClient) -> str:
    settings = get_settings()
    return client.topic_path(settings.gcp_project_id, "argus-events")
