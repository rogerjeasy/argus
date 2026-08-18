import json
import unicodedata
from dataclasses import dataclass, field


def _fold(text: str) -> str:
    """Case- and diacritic-insensitive comparison key — same normalization
    GtfsStaticIndex uses (app/domains/transit/static_index.py) for the same
    reason: spoken transcripts may or may not preserve accents."""
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


@dataclass(frozen=True)
class VenueDirectoryEntry:
    target: str
    value: str
    aliases: tuple[str, ...] = field(default_factory=tuple)


class VenueDirectoryIndex:
    """Parses a venue directory JSON document once. Same StaticIndex-shaped
    pattern as GtfsStaticIndex (design doc §3) — same interface, a plain
    JSON directory instead of a GTFS zip as the data source."""

    def __init__(self, directory_bytes: bytes) -> None:
        raw: dict[str, list[dict]] = json.loads(directory_bytes)
        self._entries: dict[str, list[VenueDirectoryEntry]] = {
            venue_id: [
                VenueDirectoryEntry(target=e["target"], value=e["value"], aliases=tuple(e.get("aliases", [])))
                for e in entries
            ]
            for venue_id, entries in raw.items()
        }

    def has_data_for(self, venue_id: str) -> bool:
        return bool(self._entries.get(venue_id))

    def resolve(self, venue_id: str, goal_text: str) -> VenueDirectoryEntry | None:
        folded_goal = _fold(goal_text)
        for entry in self._entries.get(venue_id, []):
            names = (entry.target, *entry.aliases)
            if any(_fold(name) in folded_goal for name in names):
                return entry
        return None
