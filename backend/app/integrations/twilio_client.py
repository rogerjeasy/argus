from typing import Any, Protocol

from starlette.concurrency import run_in_threadpool


class TwilioClient(Protocol):
    async def place_call(self, *, to: str, from_: str, twiml: str, status_callback_url: str | None = None) -> str: ...
    async def send_dtmf(self, *, call_sid: str, digits: str) -> None: ...
    async def hang_up(self, *, call_sid: str) -> None: ...
    async def send_sms(self, *, to: str, from_: str, body: str) -> str: ...


class RealTwilioClient:
    """The genuine `twilio` SDK behind the TwilioClient interface — not a
    mock, the real client, just swappable so tests use FakeTwilioClient
    instead (design doc §3). `sdk_client` is injectable for tests; unset in
    production, where it's built from real account credentials."""

    def __init__(self, account_sid: str, auth_token: str, *, sdk_client: Any | None = None) -> None:
        if sdk_client is not None:
            self._client = sdk_client
        else:
            from twilio.rest import Client
            self._client = Client(account_sid, auth_token)

    async def place_call(self, *, to: str, from_: str, twiml: str, status_callback_url: str | None = None) -> str:
        kwargs: dict = {"to": to, "from_": from_, "twiml": twiml}
        if status_callback_url is not None:
            kwargs["status_callback"] = status_callback_url
            kwargs["status_callback_event"] = ["initiated", "answered", "completed"]
        call = await run_in_threadpool(self._client.calls.create, **kwargs)
        return call.sid

    async def send_dtmf(self, *, call_sid: str, digits: str) -> None:
        from twilio.twiml.voice_response import VoiceResponse
        response = VoiceResponse()
        response.play(digits=digits)
        await run_in_threadpool(self._client.calls(call_sid).update, twiml=str(response))

    async def hang_up(self, *, call_sid: str) -> None:
        await run_in_threadpool(self._client.calls(call_sid).update, status="completed")

    async def send_sms(self, *, to: str, from_: str, body: str) -> str:
        message = await run_in_threadpool(self._client.messages.create, to=to, from_=from_, body=body)
        return message.sid
