#!/usr/bin/env python3
"""Runs the backend e2e regression suite N times, each in a fresh
subprocess (a fresh interpreter is required — see telemetry.use_in_memory_
exporter's docstring on why the tracer-provider swap can't happen mid-
process after modules are already imported), and reports p50/p95 latency
for the "agent.handle_goal" span — goal received to guidance text ready.

Scope, stated explicitly because it's easy to misread the number: this
measures the deterministic, offline-testable part of the pipeline (Router
-> Grounding -> Planner -> Guardrail -> Guidance text). It does NOT include
Gemini Live's own TTS network latency (goal transcription in, or synthesized
audio out) — the e2e suite's fakes don't touch a real Gemini session, and
neither does this script. The "real Gemini" half of the design doc's
latency target is a separate, live-network measurement that belongs in the
already-tracked pre-demo checklist (real-mic-to-real-session verification),
not something an offline script can produce.

Usage: python scripts/measure_latency.py [--runs N] [--out PATH]
"""
import argparse
import json
import os
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"


def _run_once() -> list[dict]:
    with tempfile.NamedTemporaryFile(mode="r", suffix=".json", delete=False) as tmp:
        report_path = tmp.name
    env = {
        **os.environ,
        "ARGUS_MEASURE_LATENCY": "1",
        "ARGUS_LATENCY_REPORT_PATH": report_path,
    }
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-k", "e2e", "-q"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pytest run failed:\n{result.stdout}\n{result.stderr}")
    with open(report_path, encoding="utf-8") as f:
        spans = json.load(f)
    os.unlink(report_path)
    return spans


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    all_durations_ms: list[float] = []
    for i in range(args.runs):
        print(f"run {i + 1}/{args.runs}...", file=sys.stderr)
        spans = _run_once()
        for span in spans:
            if span["name"] == "agent.handle_goal":
                duration_ms = (span["end_time_ns"] - span["start_time_ns"]) / 1_000_000
                all_durations_ms.append(duration_ms)

    if not all_durations_ms:
        print("No agent.handle_goal spans captured across any run — nothing to report.", file=sys.stderr)
        sys.exit(1)

    all_durations_ms.sort()
    p50 = statistics.median(all_durations_ms)
    p95_index = min(len(all_durations_ms) - 1, int(len(all_durations_ms) * 0.95))
    p95 = all_durations_ms[p95_index]

    report = {
        "runs": args.runs,
        "sample_count": len(all_durations_ms),
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "min_ms": round(min(all_durations_ms), 2),
        "max_ms": round(max(all_durations_ms), 2),
        "scope": "agent.handle_goal span only — Router through Guidance-text-ready, "
                 "offline fixtures, no real Gemini Live network latency included.",
    }
    print(json.dumps(report, indent=2))
    if args.out:
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
