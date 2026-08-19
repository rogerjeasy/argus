import json
import os

# Latency-measurement seam (Phase 5 plan Task 9-10, scripts/measure_latency.py)
# — only active when ARGUS_MEASURE_LATENCY=1, so a normal pytest/make test/CI
# run is completely unaffected. MUST run before `from app.main import app`
# below — that import transitively imports orchestrator.py/ws/session.py,
# both of which bind a module-level `tracer = get_tracer(__name__)` at
# import time, and a Tracer stays bound to whichever provider was live when
# it was created, forever. Priming the in-memory exporter from a
# pytest_configure hook instead does NOT work: pytest must import
# conftest.py itself (running every top-level statement in it, including
# the `from app.main import app` below) before it can even find a
# pytest_configure function to call — confirmed by a smoke test that
# reported 0 captured spans despite pytest_configure being wired up per
# the textbook ordering. See use_in_memory_exporter()'s own docstring for
# the general rule this is one instance of.
_argus_latency_exporter = None
if os.environ.get("ARGUS_MEASURE_LATENCY") == "1":
    from app.core.telemetry import use_in_memory_exporter

    _argus_latency_exporter = use_in_memory_exporter()

import pytest  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_dependency_overrides():
    yield
    app.dependency_overrides.clear()


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if _argus_latency_exporter is None:
        return
    report_path = os.environ.get("ARGUS_LATENCY_REPORT_PATH")
    if not report_path:
        return
    spans = [
        {"name": s.name, "start_time_ns": s.start_time, "end_time_ns": s.end_time}
        for s in _argus_latency_exporter.get_finished_spans()
    ]
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(spans, f)
