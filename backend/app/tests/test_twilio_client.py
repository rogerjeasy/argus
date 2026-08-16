from unittest.mock import MagicMock

import pytest

from app.integrations.twilio_client import RealTwilioClient


@pytest.mark.asyncio
async def test_place_call_creates_a_call_with_the_given_twiml_and_status_callback() -> None:
    fake_sdk_client = MagicMock()
    fake_sdk_client.calls.create.return_value = MagicMock(sid="CA123")

    client = RealTwilioClient("sid", "token", sdk_client=fake_sdk_client)
    sid = await client.place_call(
        to="+15559990000", from_="+15551234567", twiml="<Response></Response>",
        status_callback_url="https://example.com/webhooks/twilio/call-status",
    )

    assert sid == "CA123"
    _, kwargs = fake_sdk_client.calls.create.call_args
    assert kwargs["to"] == "+15559990000"
    assert kwargs["from_"] == "+15551234567"
    assert kwargs["twiml"] == "<Response></Response>"
    assert kwargs["status_callback"] == "https://example.com/webhooks/twilio/call-status"


@pytest.mark.asyncio
async def test_send_dtmf_updates_the_call_with_a_play_digits_twiml() -> None:
    fake_sdk_client = MagicMock()
    calls_resource = MagicMock()
    fake_sdk_client.calls.return_value = calls_resource

    client = RealTwilioClient("sid", "token", sdk_client=fake_sdk_client)
    await client.send_dtmf(call_sid="CA123", digits="1")

    fake_sdk_client.calls.assert_called_with("CA123")
    _, kwargs = calls_resource.update.call_args
    assert "Play digits=\"1\"" in kwargs["twiml"]


@pytest.mark.asyncio
async def test_hang_up_updates_the_call_status_to_completed() -> None:
    fake_sdk_client = MagicMock()
    calls_resource = MagicMock()
    fake_sdk_client.calls.return_value = calls_resource

    client = RealTwilioClient("sid", "token", sdk_client=fake_sdk_client)
    await client.hang_up(call_sid="CA123")

    fake_sdk_client.calls.assert_called_with("CA123")
    calls_resource.update.assert_called_with(status="completed")
