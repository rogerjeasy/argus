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
