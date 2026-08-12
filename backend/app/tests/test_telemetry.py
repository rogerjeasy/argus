from opentelemetry.trace import Tracer

from app.core.telemetry import get_tracer


def test_get_tracer_returns_a_tracer_and_can_start_a_span() -> None:
    tracer = get_tracer("test")
    assert isinstance(tracer, Tracer)
    with tracer.start_as_current_span("unit-test-span") as span:
        span.set_attribute("argus.test", True)
