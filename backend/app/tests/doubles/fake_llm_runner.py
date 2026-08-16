class FakeLlmAgentRunner:
    """Drop-in substitute for `LlmAgentRunner` in every reasoning agent's
    tests — returns scripted responses, proving the *agent's* handling of
    those responses rather than model quality.

    Use `next_response` for the common case of a single scripted reply.
    Use `responses` (substring of the prompt -> response text) when a test
    needs different agents/prompts within the same fake to get different
    answers; the first key found as a substring of the prompt wins, falling
    back to `next_response` when nothing matches.
    """

    def __init__(self, next_response: str = "") -> None:
        self.next_response = next_response
        self.responses: dict[str, str] = {}
        self.calls: list[dict] = []

    async def invoke(self, *, user_id: str, session_id: str, prompt: str) -> str:
        self.calls.append({"user_id": user_id, "session_id": session_id, "prompt": prompt})
        for substring, response in self.responses.items():
            if substring in prompt:
                return response
        return self.next_response
