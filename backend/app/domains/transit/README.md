# Transit domain — pre-demo checklist

This package's tests run entirely offline, against protobuf/CSV bytes built
in-process by `app/tests/fixtures/gtfs_builders.py` — real wire format, but
not a real captured snapshot. Before filming the demo:

1. **Register for a Switzerland token**: https://api-manager.opentransportdata.swiss/
   — populate `GTFS_CH_AUTH_TOKEN` (and the two `GTFS_CH_*_FEED_URL` vars,
   see `.env.example`) in your local `.env`.
2. **Smoke-test both feeds locally**: `make dev`, then a real session goal
   like "what platform is my train to Bern on" (Switzerland) or "what
   platform is my train at North Station" (MBTA) — confirm a real grounded
   platform comes back, not a confidence-0 fallback.
3. **Manual field test at a real Swiss station** (design doc §9, §11) —
   walk through with the app live, confirm the spoken guidance matches
   reality. MBTA's feed is fixture-only for CI/unit purposes; a matching
   Boston walk-through is not required unless convenient.
4. Optional but recommended: replace `gtfs_builders.py`'s synthetic fixture
   bytes in `test_gtfs_static_index.py`/`test_gtfs_realtime_poller.py` with
   real captured snapshots (`curl` the static zip and one `.pb` realtime
   response, save under a new `app/tests/fixtures/gtfs/{ch,mbta}/` folder,
   point the tests at the file bytes instead of the builder). Not required
   for correctness — the builders already exercise the genuine decode path
   — but closer to what the design doc originally specified.
