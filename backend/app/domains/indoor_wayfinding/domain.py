import re
from datetime import datetime, timezone

from app.domains import GroundingRequest
from app.domains.indoor_wayfinding.config import VenueDirectoryConfig
from app.domains.indoor_wayfinding.directory_index import VenueDirectoryIndex
from app.models.agent_events import GroundedFact

#: A fast pre-filter, same role as TransitDomain's and PersonalAdminDomain's
#: own keyword lists. Word-boundary matching (not raw substring containment)
#: follows PersonalAdminDomain's fixed pattern, not TransitDomain's older
#: one — see the plan's Global Constraints. Deliberately includes
#: multi-word phrases (design doc §3's own examples): the word-boundary
#: regex matches a literal phrase just as well as a single word.
_WAYFINDING_KEYWORDS = (
    "breakfast room", "gate concourse", "department", "restroom", "elevator",
    "lobby", "lounge", "conference room", "gate", "check-in", "baggage claim",
)
_KEYWORD_PATTERN = re.compile("|".join(rf"\b{re.escape(k)}\b" for k in _WAYFINDING_KEYWORDS))

#: Deliberately below TransitDomain's authoritative-source confidence
#: (1.0) — a live camera OCR read carries real misread risk in a way a
#: directory lookup or a realtime feed doesn't, and this system's guiding
#: principle is never overstate certainty. Still clears Guardrail's
#: MIN_CONFIDENCE_FLOOR (0.5, app/agents/guardrail.py) so signage-only mode
#: can actually produce actionable guidance, not just always-denied noise.
_SIGNAGE_ONLY_CONFIDENCE = 0.6
_UNRESOLVED_CONFIDENCE = 0.0


class IndoorWayfindingDomain:
    """Config-driven third domain plugin — directory-backed grounding when
    a venue publishes one (same StaticIndex-shaped pattern as Transit's
    GtfsStaticIndex), pure live-signage reading otherwise. No external API
    dependency at all in the signage-only case, which is why the design
    doc (§3) recommends this as the lowest-integration-risk Tier 2 domain
    and its designated demo fallback if Transit's real feed is flaky."""

    def __init__(self, config: VenueDirectoryConfig, directory_index: VenueDirectoryIndex) -> None:
        self.domain_id = "indoor_wayfinding"
        self._config = config
        self._directory_index = directory_index
        self.executors: dict = {}  # informational domain only, same as TransitDomain

    def matches(self, goal_text: str) -> bool:
        return bool(_KEYWORD_PATTERN.search(goal_text.lower()))

    async def ground(self, request: GroundingRequest) -> GroundedFact:
        if self._directory_index.has_data_for(self._config.venue_id):
            entry = self._directory_index.resolve(self._config.venue_id, request.raw_goal_text)
            if entry is not None:
                return GroundedFact(
                    key=request.key, value=entry.value, source="venue_directory",
                    confidence=1.0, as_of=datetime.now(timezone.utc),
                )
            return GroundedFact(
                key=request.key, value="", source="venue_directory",
                confidence=_UNRESOLVED_CONFIDENCE, as_of=datetime.now(timezone.utc),
            )

        if request.scene_signal_text:
            return GroundedFact(
                key=request.key, value=request.scene_signal_text.strip(), source="signage_only",
                confidence=_SIGNAGE_ONLY_CONFIDENCE, as_of=datetime.now(timezone.utc),
            )
        return GroundedFact(
            key=request.key, value="unknown", source="signage_only",
            confidence=_UNRESOLVED_CONFIDENCE, as_of=datetime.now(timezone.utc),
        )

    def extract_signage_candidate(self, text: str) -> str | None:
        stripped = text.strip()
        if not stripped:
            return None
        if self._directory_index.has_data_for(self._config.venue_id):
            entry = self._directory_index.resolve(self._config.venue_id, stripped)
            return entry.value if entry is not None else None
        return stripped
