"""The capabilities Argus exposes to the live Gemini session as callable
function tools. Gemini is the conversational agent; these tools are how it
reaches real data and takes real action.

Every tool returns a plain ``dict`` that becomes the function response
Gemini sees. Errors are returned as ``{"error": "..."}`` rather than
raised, so one failed lookup never tears down the session.

Irreversible actions (placing a phone call, contacting someone) never fire
directly from a tool call — the toolbox stores them as a pending action and
only carries them out once ``confirm_pending_action`` is called after the
user has said yes out loud.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from google.genai import types as genai_types

from app.agents.grounding import GroundingAgent
from app.agents.memory import MemoryAgent
from app.domains.transit.domain import TransitDomain

logger = logging.getLogger(__name__)

SpeakCallback = Callable[[str], Awaitable[None]]


def _obj(properties: dict, required: list[str]) -> dict:
    return {"type": "OBJECT", "properties": properties, "required": required}


TOOL_DECLARATIONS: list[genai_types.FunctionDeclaration] = [
    genai_types.FunctionDeclaration(
        name="get_transit_directions",
        description=(
            "Look up the current real-time platform or track for the user's train at a named "
            "station, from live GTFS-Realtime transit data. Call this whenever the user asks "
            "which platform, track, or gate their train is on — never guess a platform number."
        ),
        parameters=_obj(
            {"station": {"type": "STRING", "description": "The station name the user said, e.g. 'North Station'."}},
            ["station"],
        ),
    ),
    genai_types.FunctionDeclaration(
        name="check_transit_disruptions",
        description=(
            "Check the live transit feed for service alerts or disruptions affecting the user's "
            "train at a named station. Call this when the user asks if their train is delayed, "
            "cancelled, or if there are problems on the line."
        ),
        parameters=_obj(
            {"station": {"type": "STRING", "description": "The station name the user said."}},
            ["station"],
        ),
    ),
    genai_types.FunctionDeclaration(
        name="remember",
        description=(
            "Store a short fact the user asks you to remember for next time — their home address, "
            "a regular route, a preference. Use a short lowercase key like 'home_address'."
        ),
        parameters=_obj(
            {"key": {"type": "STRING"}, "value": {"type": "STRING"}},
            ["key", "value"],
        ),
    ),
    genai_types.FunctionDeclaration(
        name="recall",
        description="Retrieve a fact the user previously asked you to remember, by its key.",
        parameters=_obj({"key": {"type": "STRING"}}, ["key"]),
    ),
    genai_types.FunctionDeclaration(
        name="place_phone_call",
        description=(
            "Place a real outbound phone call on the user's behalf to handle a task like confirming "
            "a prescription refill. This does NOT dial immediately: it returns a read-back for you "
            "to say to the user. Only after the user says yes out loud do you call "
            "confirm_pending_action to actually place the call."
        ),
        parameters=_obj(
            {
                "phone_number": {"type": "STRING", "description": "E.164 number, e.g. +16175551234."},
                "purpose": {"type": "STRING", "description": "The single bounded goal of the call."},
            },
            ["phone_number", "purpose"],
        ),
    ),
    genai_types.FunctionDeclaration(
        name="confirm_pending_action",
        description=(
            "Carry out (or cancel) the action that place_phone_call queued, once the user has "
            "answered. Pass confirmed=true only if the user clearly said yes."
        ),
        parameters=_obj({"confirmed": {"type": "BOOLEAN"}}, ["confirmed"]),
    ),
]

SYSTEM_INSTRUCTION = (
    "You are Argus, a real-time voice copilot for blind and low-vision people. You help them "
    "get places and get things done in the real world, through their phone's camera and "
    "microphone.\n"
    "Speak in short, calm, concrete sentences — never long descriptions or lists read aloud. "
    "You can see the live camera; when the user asks what's around them or to read a sign, "
    "describe just what matters, and if you can't read something tell them how to move the "
    "phone.\n"
    "Never guess a platform number, a track, an address, or a schedule — call a tool to get "
    "real data. If a tool returns an error, say plainly that you couldn't get it.\n"
    "You never give physical-mobility or obstacle-avoidance directions — no 'step down', no "
    "'curb ahead'. That is not your job and you say so if asked.\n"
    "Before you place a phone call or contact anyone, say exactly what you are about to do and "
    "wait for the user to say yes."
)


class ArgusToolbox:
    """Holds the real backends the live tools reach, plus the single pending
    irreversible action awaiting the user's spoken confirmation."""

    def __init__(
        self,
        *,
        uid: str,
        transit_domains: list[TransitDomain],
        memory: MemoryAgent,
        call_executor: Any | None,
        speak: SpeakCallback,
    ) -> None:
        self._uid = uid
        self._transit = [(d, GroundingAgent(d)) for d in transit_domains]
        self._memory = memory
        self._call_executor = call_executor
        self._speak = speak
        self._pending: dict | None = None

    async def dispatch(self, name: str, args: dict) -> dict:
        try:
            return await self._dispatch(name, dict(args))
        except Exception:
            logger.exception("agent_tool_failed", extra={"tool": name})
            return {"error": "That didn't work. Please try again."}

    async def _dispatch(self, name: str, args: dict) -> dict:
        if name == "get_transit_directions":
            return await self._get_transit_directions(str(args.get("station", "")))
        if name == "check_transit_disruptions":
            return await self._check_transit_disruptions(str(args.get("station", "")))
        if name == "remember":
            await self._memory.remember(self._uid, str(args.get("key", "")), str(args.get("value", "")))
            return {"status": "stored"}
        if name == "recall":
            value = await self._memory.recall(self._uid, str(args.get("key", "")))
            return {"value": value} if value is not None else {"error": "I don't have anything stored for that."}
        if name == "place_phone_call":
            return self._queue_phone_call(str(args.get("phone_number", "")), str(args.get("purpose", "")))
        if name == "confirm_pending_action":
            return await self._resolve_pending(bool(args.get("confirmed", False)))
        return {"error": f"Unknown tool {name}."}

    async def _get_transit_directions(self, station: str) -> dict:
        if not station:
            return {"error": "I need a station name."}
        for domain, grounding in self._transit:
            fact = await grounding.ground("platform", raw_goal_text=station)
            if fact.confidence > 0 and fact.value:
                return {
                    "platform": fact.value,
                    "station": station,
                    "source": fact.source,
                    "as_of": fact.as_of.isoformat(),
                    "agency": domain.domain_id,
                }
        return {"error": f"I couldn't find a live platform for a train at {station} right now."}

    async def _check_transit_disruptions(self, station: str) -> dict:
        if not station:
            return {"error": "I need a station name."}
        for domain, _ in self._transit:
            summary = await domain.check_disruption(station)
            if summary is not None:
                return {
                    "station": summary.stop_name,
                    "alert": summary.header_text,
                    "detail": summary.description_text or "",
                }
        return {"no_disruptions": True, "station": station}

    def _queue_phone_call(self, phone_number: str, purpose: str) -> dict:
        if self._call_executor is None:
            return {"error": "Outbound calling isn't set up on this account yet."}
        if not phone_number or not purpose:
            return {"error": "I need both a number and what the call is for."}
        self._pending = {"kind": "phone_call", "phone_number": phone_number, "purpose": purpose}
        return {
            "status": "confirmation_required",
            "read_back": f"I'm going to call {phone_number} to {purpose}. Say yes to go ahead.",
        }

    async def _resolve_pending(self, confirmed: bool) -> dict:
        pending, self._pending = self._pending, None
        if pending is None:
            return {"error": "There's nothing waiting to confirm."}
        if not confirmed:
            return {"status": "cancelled"}
        if pending["kind"] == "phone_call":
            return await self._place_call(pending)
        return {"error": "I've lost track of what to confirm."}

    async def _place_call(self, pending: dict) -> dict:
        from app.domains.personal_admin.models import CallGoal

        goal = CallGoal(
            target_phone_number=pending["phone_number"],
            purpose=pending["purpose"],
            structured_question=pending["purpose"],
        )
        raw = await self._call_executor.execute({
            "step_id": f"call-{self._uid}",
            "call_goal": goal.model_dump(),
        })
        status = raw.get("status", "failed")
        return {
            "status": status,
            "summary": raw.get("summary_text", ""),
            "data": raw.get("structured_data", {}),
        }

    @property
    def has_pending_action(self) -> bool:
        return self._pending is not None
