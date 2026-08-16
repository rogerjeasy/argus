class FakeTwilioClient:
    """Test double for TwilioClient — records every call so a test can
    assert on it, never touches real Twilio infrastructure."""

    def __init__(self, *, next_call_sid: str = "CA_fake") -> None:
        self.next_call_sid = next_call_sid
        self.placed_calls: list[dict] = []
        self.dtmf_sent: list[dict] = []
        self.hangups: list[str] = []

    async def place_call(self, *, to: str, from_: str, twiml: str, status_callback_url: str) -> str:
        self.placed_calls.append({"to": to, "from_": from_, "twiml": twiml, "status_callback_url": status_callback_url})
        return self.next_call_sid

    async def send_dtmf(self, *, call_sid: str, digits: str) -> None:
        self.dtmf_sent.append({"call_sid": call_sid, "digits": digits})

    async def hang_up(self, *, call_sid: str) -> None:
        self.hangups.append(call_sid)
