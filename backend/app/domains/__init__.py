from typing import Protocol

from pydantic import BaseModel

from app.models.agent_events import GroundedFact


class GroundingRequest(BaseModel):
    key: str


class Executor(Protocol):
    async def execute(self, payload: dict) -> dict: ...


class DomainPlugin(Protocol):
    domain_id: str

    def matches(self, goal_text: str) -> bool:
        """Fast pre-filter for the Domain Router's classification step —
        narrows candidates before the LLM call makes the final decision."""
        ...

    async def ground(self, request: GroundingRequest) -> GroundedFact: ...

    executors: dict[str, Executor]
