# Real Fixture Recording SOP

Two directories under `backend/app/tests/real_fixtures/`, gitignored (this
project keeps `docs/` gitignored; these recordings are the same category —
large, environment-specific, not meant to live in git history). Populate
before the demo; every test below no-ops (skips, not fails) until you do.

## `real_fixtures/redteam/` (design doc §4)

1. `low_light_blurred_frame.jpg` — one short, genuinely poor-quality frame:
   low light, motion blur, from a real phone camera pointed at any signage.
   Deliberately bad enough that no human could confidently read it either.
2. `conflicting_signage.jpg` — one frame with two real, contradictory signs
   both legible in frame (e.g. two platform signs pointing opposite
   directions, or two different departure times for the same claimed train).

Each needs a matching `.expected.json`:
```json
{"reported_confidence": 0.35}
```
for `low_light_blurred_frame.expected.json` (whatever confidence a human
grader assigns after looking at the real frame — must be below
`MIN_CONFIDENCE_FLOOR` (0.5) for the red-team assertion to mean anything),
and:
```json
{"position": "center", "signage_text": "Platform 4 / Platform 9", "reported_confidence": 0.4}
```
for `conflicting_signage.expected.json`.

## `real_fixtures/transit_stations/` (design doc §5)

1. `station_a_daylight/` — ≥30s of real video + audio from one real transit
   station, normal daylight.
2. `station_b_lowlight_or_different_time/` — either a second real station,
   or the same station at a different time of day/lighting.
3. `non_english_signage/` — ≥1 clip with real non-English signage in frame
   (Switzerland's German/French/Italian signage is the easiest source given
   this project's own primary feed — see Phase 2 design doc).

Each of the first two needs a matching `expected.json`:
```json
{"expected_guidance_text": "Head to platform 4."}
```
`non_english_signage/` needs:
```json
{"source_language": "de", "expected_guidance_text": "..."}
```

## Known limitation (recorded honestly, not silently)

`test_fixture_regression_recorded.py`'s station tests validate the fixture
files are well-formed — they do **not** replay the recorded audio/video
through a live Gemini Live session end-to-end. Building that offline replay
harness (faking Gemini Live's own streaming session against pre-recorded
bytes) is out of this plan's scope. Actually running each station's
recording through the real pipeline is a **manual step**: start the app,
feed the recording through the frontend's mic/camera capture (or a local
script that pipes the file's bytes into the same WS frames), and compare
the spoken guidance against `expected_guidance_text` by ear/eye.
