from app.domains.indoor_wayfinding.directory_index import VenueDirectoryIndex
from app.tests.fixtures.venue_directory_builders import build_directory_json


def test_has_data_for_is_false_for_unknown_venue() -> None:
    index = VenueDirectoryIndex(build_directory_json({}))
    assert index.has_data_for("nowhere") is False


def test_has_data_for_is_true_when_venue_has_entries() -> None:
    entries = [{"target": "breakfast room", "value": "Level 2, East Wing, past the elevators"}]
    index = VenueDirectoryIndex(build_directory_json({"venue-a": entries}))
    assert index.has_data_for("venue-a") is True


def test_resolve_matches_the_canonical_target_name() -> None:
    entries = [{"target": "breakfast room", "value": "Level 2, East Wing"}]
    index = VenueDirectoryIndex(build_directory_json({"venue-a": entries}))

    entry = index.resolve("venue-a", "where's the breakfast room")

    assert entry is not None
    assert entry.value == "Level 2, East Wing"


def test_resolve_matches_an_alias() -> None:
    entries = [{"target": "breakfast room", "value": "Level 2, East Wing", "aliases": ["dining room", "morning buffet"]}]
    index = VenueDirectoryIndex(build_directory_json({"venue-a": entries}))

    entry = index.resolve("venue-a", "can you take me to the dining room")

    assert entry is not None
    assert entry.value == "Level 2, East Wing"


def test_resolve_is_case_and_diacritic_insensitive() -> None:
    entries = [{"target": "café lounge", "value": "Ground floor, near reception"}]
    index = VenueDirectoryIndex(build_directory_json({"venue-a": entries}))

    entry = index.resolve("venue-a", "I want the CAFE LOUNGE please")

    assert entry is not None
    assert entry.value == "Ground floor, near reception"


def test_resolve_returns_none_when_nothing_matches() -> None:
    entries = [{"target": "breakfast room", "value": "Level 2, East Wing"}]
    index = VenueDirectoryIndex(build_directory_json({"venue-a": entries}))

    assert index.resolve("venue-a", "what's the wifi password") is None
