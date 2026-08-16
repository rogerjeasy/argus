"""Builds real-format GTFS static (zipped CSV) and GTFS-Realtime (protobuf)
bytes in-process, so every test in this plan exercises the genuine decode
path without a live network fetch. See test_gtfs_static_index.py and
test_gtfs_realtime_poller.py's module docstrings for why this stands in for
a captured real snapshot."""
import csv
import io
import zipfile

from google.transit import gtfs_realtime_pb2


def build_static_feed_zip(stops: list[dict], stop_times: list[dict]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w") as zf:
        _write_csv(zf, "stops.txt", stops)
        _write_csv(zf, "stop_times.txt", stop_times)
    return buffer.getvalue()


def _write_csv(zf: zipfile.ZipFile, name: str, rows: list[dict]) -> None:
    text = io.StringIO()
    writer = csv.DictWriter(text, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    zf.writestr(name, text.getvalue())


def build_trip_update_feed_message(trip_stop_pairs: list[tuple[str, str]]) -> bytes:
    """One FeedEntity per (trip_id, stop_id) pair, each a minimal valid
    TripUpdate with a single StopTimeUpdate — enough for TripUpdatePoller's
    trip_id + candidate-stop_id lookup."""
    message = gtfs_realtime_pb2.FeedMessage()
    message.header.gtfs_realtime_version = "2.0"
    message.header.timestamp = 1_700_000_000

    for i, (trip_id, stop_id) in enumerate(trip_stop_pairs):
        entity = message.entity.add()
        entity.id = f"entity-{i}"
        entity.trip_update.trip.trip_id = trip_id
        stu = entity.trip_update.stop_time_update.add()
        stu.stop_id = stop_id

    return message.SerializeToString()
