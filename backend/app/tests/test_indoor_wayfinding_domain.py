import pytest

from app.domains import GroundingRequest
from app.domains.indoor_wayfinding.config import VenueDirectoryConfig
from app.domains.indoor_wayfinding.directory_index import VenueDirectoryIndex
from app.domains.indoor_wayfinding.domain import IndoorWayfindingDomain
from app.tests.fixtures.venue_directory_builders import build_directory_json

_ENTRIES = [{"target": "breakfast room", "value": "Level 2, East Wing, past the elevators"}]
_CONFIG = VenueDirectoryConfig(venue_id="venue-a", directory_data_url="https://example.org/directory.json")


def _domain(entries_by_venue: dict[str, list[dict]] | None = None) -> IndoorWayfindingDomain:
    index = VenueDirectoryIndex(build_directory_json(entries_by_venue or {}))
    return IndoorWayfindingDomain(_CONFIG, index)


def test_matches_recognizes_venue_relative_phrasing() -> None:
    domain = _domain()
    assert domain.matches("where's the breakfast room") is True
    assert domain.matches("take me to the gate concourse") is True
    assert domain.matches("what's for dinner tonight") is False


def test_matches_uses_word_boundaries_not_substrings() -> None:
    # "department" must not accidentally match inside an unrelated word —
    # this is the class of bug PersonalAdminDomain's own keyword fix
    # (Phase 3a) exists to prevent; new domains follow that pattern.
    domain = _domain()
    assert domain.matches("I need the pharmacy department") is True
    assert domain.matches("this is a departmental meeting") is False


@pytest.mark.asyncio
async def test_ground_resolves_from_the_directory_when_data_exists() -> None:
    domain = _domain({"venue-a": _ENTRIES})

    fact = await domain.ground(GroundingRequest(key="directory_entry", raw_goal_text="where's the breakfast room"))

    assert fact.value == "Level 2, East Wing, past the elevators"
    assert fact.source == "venue_directory"
    assert fact.confidence == 1.0


@pytest.mark.asyncio
async def test_ground_returns_low_confidence_when_directory_has_no_match() -> None:
    domain = _domain({"venue-a": _ENTRIES})

    fact = await domain.ground(GroundingRequest(key="directory_entry", raw_goal_text="where's the swimming pool"))

    assert fact.confidence == 0.0
    assert fact.source == "venue_directory"


@pytest.mark.asyncio
async def test_ground_returns_unknown_in_signage_only_mode_with_no_scene_signal_yet() -> None:
    domain = _domain()  # no directory data for venue-a at all

    fact = await domain.ground(GroundingRequest(key="directory_entry", raw_goal_text="where's the breakfast room"))

    assert fact.value == "unknown"
    assert fact.source == "signage_only"
    assert fact.confidence == 0.0


@pytest.mark.asyncio
async def test_ground_uses_scene_signal_text_as_the_value_in_signage_only_mode() -> None:
    domain = _domain()  # no directory data — pure signage-only mode

    fact = await domain.ground(
        GroundingRequest(key="directory_entry", raw_goal_text="where's the breakfast room", scene_signal_text="  Room 204  ")
    )

    assert fact.value == "Room 204"  # stripped
    assert fact.source == "signage_only"
    assert fact.confidence == 0.6


@pytest.mark.asyncio
async def test_ground_prefers_directory_over_scene_signal_text_when_directory_has_data() -> None:
    # The directory is the authoritative source when one exists — a scene
    # signal is only ever load-bearing in pure signage-only mode.
    domain = _domain({"venue-a": _ENTRIES})

    fact = await domain.ground(
        GroundingRequest(key="directory_entry", raw_goal_text="where's the breakfast room", scene_signal_text="Room 999")
    )

    assert fact.value == "Level 2, East Wing, past the elevators"
    assert fact.source == "venue_directory"
