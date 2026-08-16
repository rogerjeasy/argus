import csv
import io
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import datetime, time


@dataclass(frozen=True)
class StaticStop:
    stop_id: str
    stop_name: str
    trip_id: str
    platform_code: str | None


def _fold(text: str) -> str:
    """Case- and diacritic-insensitive comparison key — needed for German-
    language Swiss stop names ("Zürich") to match a goal transcript that may
    or may not have preserved the umlaut."""
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def _parse_gtfs_time(value: str) -> time | None:
    """GTFS times can exceed 24:00:00 for post-midnight service; this index
    clamps into a same-day time-of-day for its "next departure" comparison.
    An after-midnight rollover is a known limitation, not exercised by this
    phase's fixtures."""
    try:
        hh, mm, ss = (int(p) for p in value.split(":"))
    except ValueError:
        return None
    return time(hour=hh % 24, minute=mm, second=ss)


class GtfsStaticIndex:
    """Parses a zipped GTFS static feed once and resolves a spoken stop
    name to the soonest-departing trip serving it. Every field read here is
    part of the GTFS static spec, not any one agency's convention — see the
    design doc §3's architectural rule."""

    def __init__(self, feed_bytes: bytes) -> None:
        self._stops_by_id: dict[str, dict] = {}
        self._stop_times_by_stop: dict[str, list[dict]] = {}
        self._load(feed_bytes)

    def _load(self, feed_bytes: bytes) -> None:
        with zipfile.ZipFile(io.BytesIO(feed_bytes)) as zf:
            self._stops_by_id = {row["stop_id"]: row for row in self._read_csv(zf, "stops.txt")}
            for row in self._read_csv(zf, "stop_times.txt"):
                self._stop_times_by_stop.setdefault(row["stop_id"], []).append(row)

    @staticmethod
    def _read_csv(zf: zipfile.ZipFile, name: str) -> list[dict]:
        with zf.open(name) as f:
            text = io.TextIOWrapper(f, encoding="utf-8-sig")
            return list(csv.DictReader(text))

    def resolve_stop(self, goal_text: str, *, now: time | None = None) -> StaticStop | None:
        """A deliberately simple "next departure at a name-matched station"
        heuristic — not a full trip planner (see the design doc's non-goals).
        Among every stop whose name appears in the goal text, picks the
        stop_time row with the soonest scheduled arrival at/after `now`."""
        folded_goal = _fold(goal_text)
        candidates = [
            stop_id for stop_id, row in self._stops_by_id.items() if _fold(row["stop_name"]) in folded_goal
        ]
        if not candidates:
            return None

        current = now if now is not None else datetime.now().time()
        best: tuple[str, time] | None = None
        best_row: dict | None = None
        for stop_id in candidates:
            for st in self._stop_times_by_stop.get(stop_id, []):
                arrival = _parse_gtfs_time(st["arrival_time"])
                if arrival is None or arrival < current:
                    continue
                if best is None or arrival < best[1]:
                    best = (stop_id, arrival)
                    best_row = st

        if best is None or best_row is None:
            return None
        stop_id = best[0]
        stop_row = self._stops_by_id[stop_id]
        return StaticStop(
            stop_id=stop_id,
            stop_name=stop_row["stop_name"],
            trip_id=best_row["trip_id"],
            platform_code=stop_row.get("platform_code") or None,
        )

    def platform_code_for(self, stop_id: str) -> str:
        row = self._stops_by_id.get(stop_id, {})
        return row.get("platform_code") or row.get("stop_name") or stop_id

    def sibling_stop_ids(self, stop_id: str) -> frozenset[str]:
        """All stop_ids sharing this stop's parent_station (falling back to
        its exact stop_name if it has none) — the set of platform-level
        stops a realtime feed might reassign this trip's arrival between."""
        row = self._stops_by_id.get(stop_id)
        if row is None:
            return frozenset({stop_id})
        key = row.get("parent_station") or row.get("stop_name")

        def _key_of(r: dict) -> str:
            return r.get("parent_station") or r.get("stop_name") or ""

        return frozenset(sid for sid, r in self._stops_by_id.items() if _key_of(r) == key)
