from app.core.cloud_tasks import enqueue_call_retry
from app.tests.doubles.fake_cloud_tasks import FakeCloudTasksClient


def test_enqueue_call_retry_returns_true_on_first_enqueue() -> None:
    client = FakeCloudTasksClient()

    enqueued = enqueue_call_retry(
        client, project="p", location="us-central1", queue="q", step_id="step-1",
        payload={"call_goal": {}}, retry_endpoint_url="https://argus.example/internal/retry-call/step-1",
    )

    assert enqueued is True


def test_enqueue_call_retry_returns_false_for_a_duplicate_step_id() -> None:
    client = FakeCloudTasksClient()
    kwargs = dict(
        client=client, project="p", location="us-central1", queue="q", step_id="step-1",
        payload={"call_goal": {}}, retry_endpoint_url="https://argus.example/internal/retry-call/step-1",
    )

    first = enqueue_call_retry(**kwargs)
    second = enqueue_call_retry(**kwargs)

    assert first is True
    assert second is False
