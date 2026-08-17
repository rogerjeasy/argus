import pytest

from app.domains.personal_admin.form_executor import FormExecutor
from app.tests.doubles.fake_storage_client import FakeStorageClient


@pytest.mark.asyncio
async def test_execute_renders_a_pdf_uploads_it_and_returns_a_success_outcome() -> None:
    storage = FakeStorageClient()
    executor = FormExecutor(storage)
    payload = {
        "step_id": "step-1",
        "fields": [
            {"name": "full_name", "label": "Full name", "value": "Jordan Rivera", "source": "memory_profile"},
            {"name": "policy_number", "label": "Policy number", "value": "POL-12345", "source": "user_provided"},
        ],
    }

    outcome = await executor.execute(payload)

    assert outcome["step_id"] == "step-1"
    assert outcome["status"] == "success"
    assert outcome["structured_data"]["output_url"] == "https://fake-storage.example.com/personal_admin_forms/step-1.pdf?signed=true"
    assert outcome["structured_data"]["status"] == "pdf_ready"
    assert len(storage.uploads) == 1
    assert storage.uploads[0]["content_type"] == "application/pdf"
    assert storage.uploads[0]["data"].startswith(b"%PDF")


@pytest.mark.asyncio
async def test_execute_reports_failed_status_when_upload_raises() -> None:
    class _FailingStorage:
        async def upload_and_sign(self, path, data, *, content_type):
            raise RuntimeError("bucket unreachable")

    executor = FormExecutor(_FailingStorage())
    payload = {"step_id": "step-1", "fields": [{"name": "full_name", "label": "Full name", "value": "Jordan Rivera", "source": "memory_profile"}]}

    outcome = await executor.execute(payload)

    assert outcome["status"] == "failed"
    assert outcome["structured_data"] == {}
