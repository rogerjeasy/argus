import json


def build_directory_json(entries_by_venue: dict[str, list[dict]]) -> bytes:
    """The venue directory's on-disk/fetched shape: {venue_id: [{"target":
    ..., "value": ..., "aliases": [...]}]}. A plain JSON document — no zip,
    unlike GTFS static feeds — since a venue directory is a small,
    hand-authored dataset, not an interchange-format export."""
    return json.dumps(entries_by_venue).encode("utf-8")
