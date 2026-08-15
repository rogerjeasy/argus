from typing import Any

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService, InMemorySessionService
from google.genai import types as genai_types


class LlmAgentRunner:
    """Thin wrapper around an ADK `LlmAgent` + `Runner` reduced to the one
    operation every reasoning agent in this codebase needs: send a prompt,
    get back the final response text. Keeping ADK's session/event machinery
    behind this one method is what lets every other agent's tests run
    without ADK, Gemini, or network access — see `FakeLlmAgentRunner`."""

    def __init__(
        self,
        *,
        agent: LlmAgent,
        app_name: str = "argus",
        session_service: BaseSessionService | None = None,
        runner: Any | None = None,
    ) -> None:
        self._app_name = app_name
        self._session_service = session_service or InMemorySessionService()
        self._runner = runner or Runner(agent=agent, app_name=app_name, session_service=self._session_service)

    async def invoke(self, *, user_id: str, session_id: str, prompt: str) -> str:
        await self._session_service.create_session(app_name=self._app_name, user_id=user_id, session_id=session_id)
        message = genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])
        final_text = ""
        async for event in self._runner.run_async(user_id=user_id, session_id=session_id, new_message=message):
            if event.is_final_response() and event.content and event.content.parts:
                final_text = event.content.parts[0].text or ""
        return final_text
