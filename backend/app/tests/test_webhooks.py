from fastapi.testclient import TestClient

from app.domains.personal_admin.call_session_registry import CallSessionRegistry
from app.domains.personal_admin.models import CallGoal
from app.main import app
from app.tests.doubles.fake_cloud_tasks import FakeCloudTasksClient
from app.ws.twilio_media import get_call_session_registry


def _registry_with_pending_call() -> CallSessionRegistry:
    registry = CallSessionRegistry()
    from app.tests.doubles.fake_twilio_client import FakeTwilioClient
    goal = CallGoal(target_phone_number="+15559990000", purpose="confirm refill status", structured_question="Is it ready?")
    registry.register("step-1", goal, FakeTwilioClient())
    return registry


def test_busy_status_resolves_the_registry_and_enqueues_one_retry(monkeypatch) -> None:
    registry = _registry_with_pending_call()
    fake_tasks_client = FakeCloudTasksClient()

    app.dependency_overrides[get_call_session_registry] = lambda: registry
    monkeypatch.setattr("app.api.webhooks._validate_twilio_signature", lambda request, form: True)
    monkeypatch.setattr("app.api.webhooks.get_cloud_tasks_client", lambda: fake_tasks_client)

    client = TestClient(app)
    response = client.post(
        "/webhooks/twilio/call-status", params={"step_id": "step-1"},
        data={"CallSid": "CA123", "CallStatus": "busy"},
    )

    assert response.status_code == 200
    assert len(fake_tasks_client.created_task_names) == 1


def test_completed_status_is_a_no_op_left_to_the_media_stream_handler(monkeypatch) -> None:
    registry = _registry_with_pending_call()
    fake_tasks_client = FakeCloudTasksClient()

    app.dependency_overrides[get_call_session_registry] = lambda: registry
    monkeypatch.setattr("app.api.webhooks._validate_twilio_signature", lambda request, form: True)
    monkeypatch.setattr("app.api.webhooks.get_cloud_tasks_client", lambda: fake_tasks_client)

    client = TestClient(app)
    response = client.post(
        "/webhooks/twilio/call-status", params={"step_id": "step-1"},
        data={"CallSid": "CA123", "CallStatus": "completed"},
    )

    assert response.status_code == 200
    assert fake_tasks_client.created_task_names == set()


def test_invalid_signature_is_rejected(monkeypatch) -> None:
    registry = _registry_with_pending_call()
    app.dependency_overrides[get_call_session_registry] = lambda: registry
    monkeypatch.setattr("app.api.webhooks._validate_twilio_signature", lambda request, form: False)

    client = TestClient(app)
    response = client.post(
        "/webhooks/twilio/call-status", params={"step_id": "step-1"},
        data={"CallSid": "CA123", "CallStatus": "busy"},
    )

    assert response.status_code == 403


def test_retry_call_endpoint_replays_execute_with_the_original_payload() -> None:
    from app.api.webhooks import get_call_executor

    class _FakeExecutor:
        def __init__(self) -> None:
            self.received: dict | None = None

        async def execute(self, payload: dict) -> dict:
            self.received = payload
            return {"step_id": payload["step_id"], "status": "success", "structured_data": {}, "summary_text": "ok"}

    fake_executor = _FakeExecutor()
    app.dependency_overrides[get_call_executor] = lambda: fake_executor

    client = TestClient(app)
    response = client.post(
        "/internal/retry-call/step-1",
        json={"step_id": "step-1", "call_goal": {"target_phone_number": "+1", "purpose": "p", "structured_question": "q"}},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert fake_executor.received["step_id"] == "step-1"
