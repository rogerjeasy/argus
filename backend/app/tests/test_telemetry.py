from unittest.mock import patch

import pytest
from opentelemetry import trace
from opentelemetry.trace import Tracer
from opentelemetry.util._once import Once

from app.core.telemetry import get_tracer


@pytest.fixture(autouse=True)
def reset_telemetry_state() -> None:
    """Reset telemetry global state between tests for isolation."""
    import app.core.telemetry as telemetry_module

    yield
    # Reset module-level state after test
    telemetry_module._provider_initialized = False
    # opentelemetry.trace.set_tracer_provider() is guarded by a real Once()
    # object that only ever permits ONE successful call per process — the
    # plain `trace.set_tracer_provider(...)` call this fixture used to end
    # with was silently ignored (just a logged warning) after the first
    # real provider was set anywhere in the test session, which every test
    # in this file happened not to notice until
    # test_use_in_memory_exporter_captures_finished_spans (Phase 5 plan
    # Task 9) actually depended on a second swap taking effect. There is no
    # public reset API; directly clearing the internal guard is the same
    # pattern opentelemetry-python's own test suite uses for cross-test
    # provider isolation.
    trace._TRACER_PROVIDER = None
    trace._TRACER_PROVIDER_SET_ONCE = Once()
    trace.set_tracer_provider(trace.NoOpTracerProvider())


def test_get_tracer_returns_a_tracer_and_can_start_a_span() -> None:
    tracer = get_tracer("test")
    assert isinstance(tracer, Tracer)
    with tracer.start_as_current_span("unit-test-span") as span:
        span.set_attribute("argus.test", True)


def test_use_in_memory_exporter_captures_finished_spans() -> None:
    from app.core.telemetry import use_in_memory_exporter

    exporter = use_in_memory_exporter()
    tracer = get_tracer("test-in-memory")
    with tracer.start_as_current_span("unit-test-span"):
        pass

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "unit-test-span"


def test_get_tracer_uses_cloud_trace_exporter_in_production() -> None:
    """Verify that production environment uses CloudTraceSpanExporter."""
    with patch("app.core.telemetry.get_settings") as mock_settings:
        with patch("opentelemetry.exporter.cloud_trace.CloudTraceSpanExporter") as mock_cloud_exporter:
            # Configure mock settings for production
            mock_settings.return_value.environment = "production"
            mock_settings.return_value.gcp_project_id = "test-project"

            # Import at module level to trigger conditional import
            import app.core.telemetry as telemetry_module

            # Reset to force reinitialization with mocked settings
            telemetry_module._provider_initialized = False

            # Call get_tracer to trigger provider initialization
            tracer = get_tracer("production-test")

            # Verify CloudTraceSpanExporter was instantiated with correct project_id
            mock_cloud_exporter.assert_called_once_with(project_id="test-project")
            assert isinstance(tracer, Tracer)
