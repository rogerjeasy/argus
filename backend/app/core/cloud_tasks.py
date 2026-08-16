import json
from functools import lru_cache
from typing import Any

from google.cloud import tasks_v2


class _LazyCloudTasksClient:
    """Same deferred-construction precedent as _LazyPublisherClient
    (app/core/pubsub.py) — most sessions never enqueue a retry, so paying
    GCP credential-resolution cost at import time would be wasted work."""

    def __init__(self) -> None:
        self._client: tasks_v2.CloudTasksClient | None = None

    def _real_client(self) -> tasks_v2.CloudTasksClient:
        if self._client is None:
            self._client = tasks_v2.CloudTasksClient()
        return self._client

    def queue_path(self, project: str, location: str, queue: str) -> str:
        return self._real_client().queue_path(project, location, queue)

    def create_task(self, request: dict):
        return self._real_client().create_task(request=request)


@lru_cache
def get_cloud_tasks_client() -> _LazyCloudTasksClient:
    return _LazyCloudTasksClient()


def enqueue_call_retry(
    client: Any, *, project: str, location: str, queue: str, step_id: str, payload: dict, retry_endpoint_url: str,
) -> bool:
    """Returns True if a new retry was enqueued, False if one for this
    step_id already existed. Idempotency is Cloud Tasks' own named-task
    uniqueness, not custom bookkeeping — see this task's Interfaces note."""
    from google.api_core.exceptions import AlreadyExists

    queue_path = client.queue_path(project, location, queue)
    task_name = f"{queue_path}/tasks/call-retry-{step_id}"
    task = {
        "name": task_name,
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": retry_endpoint_url,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(payload).encode("utf-8"),
        },
    }
    try:
        client.create_task(request={"parent": queue_path, "task": task})
        return True
    except AlreadyExists:
        return False
