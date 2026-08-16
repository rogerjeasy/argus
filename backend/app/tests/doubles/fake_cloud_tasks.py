"""Mirrors real Cloud Tasks' own named-task uniqueness — the second
create_task() call for the same task name raises the genuine
google.api_core.exceptions.AlreadyExists, exactly like the real service
would, so enqueue_call_retry()'s `except AlreadyExists` actually proves
something against this fake."""

from google.api_core.exceptions import AlreadyExists


class FakeCloudTasksClient:
    def __init__(self) -> None:
        self.created_task_names: set[str] = set()

    def queue_path(self, project: str, location: str, queue: str) -> str:
        return f"projects/{project}/locations/{location}/queues/{queue}"

    def create_task(self, request: dict):
        name = request["task"]["name"]
        if name in self.created_task_names:
            raise AlreadyExists(name)
        self.created_task_names.add(name)
        return request["task"]
