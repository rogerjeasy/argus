import threading

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Tracer

from app.core.config import get_settings

_provider_initialized = False
_provider_lock = threading.Lock()


def _ensure_provider() -> None:
    global _provider_initialized
    if _provider_initialized:
        return
    with _provider_lock:
        if _provider_initialized:
            return
        settings = get_settings()
        resource = Resource.create({"service.name": "argus-backend"})
        provider = TracerProvider(resource=resource)
        if settings.environment == "production":
            from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter

            provider.add_span_processor(BatchSpanProcessor(CloudTraceSpanExporter(project_id=settings.gcp_project_id)))
        else:
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(provider)
        _provider_initialized = True


def get_tracer(name: str) -> Tracer:
    _ensure_provider()
    return trace.get_tracer(name)


def use_in_memory_exporter():
    """Measurement/test-only seam (scripts/measure_latency.py, via
    conftest.py's pytest_configure) — swaps the tracer provider for one
    that exports to memory instead of Console/CloudTrace, and returns the
    exporter so spans can be read back after a run.

    MUST be called before any module-level `tracer = get_tracer(__name__)`
    statement executes in this process (orchestrator.py, ws/session.py both
    have one) — a Tracer object stays bound to the provider that created it
    forever; calling this after those modules are already imported would
    silently do nothing for their already-created tracers. This is why
    conftest.py calls it from pytest_configure, which runs before pytest
    collects (imports) any test module.

    `opentelemetry.trace.set_tracer_provider()` is guarded by a real
    `Once()` object that only ever permits one successful call per process
    — every later call is silently ignored (just a logged warning), which
    would make this function a no-op the second time anything in the
    process already set a provider. Directly clearing the internal guard
    first is the same pattern opentelemetry-python's own test suite uses;
    there is no public reset API."""
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from opentelemetry.util._once import Once

    global _provider_initialized
    exporter = InMemorySpanExporter()
    resource = Resource.create({"service.name": "argus-backend"})
    provider = TracerProvider(resource=resource)
    # SimpleSpanProcessor, not BatchSpanProcessor: spans must be readable
    # immediately after each test completes, not after an async batch delay.
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace._TRACER_PROVIDER = None
    trace._TRACER_PROVIDER_SET_ONCE = Once()
    trace.set_tracer_provider(provider)
    _provider_initialized = True
    return exporter
