from unittest.mock import MagicMock, patch

import pytest
from opentelemetry import trace
from opentelemetry.trace import Tracer

from app.core.telemetry import get_tracer, _provider_initialized


@pytest.fixture(autouse=True)
def reset_telemetry_state() -> None:
    """Reset telemetry global state between tests for isolation."""
    import app.core.telemetry as telemetry_module

    yield
    # Reset module-level state after test
    telemetry_module._provider_initialized = False
    # Reset the global tracer provider to avoid cross-test contamination
    trace.set_tracer_provider(trace.NoOpTracerProvider())


def test_get_tracer_returns_a_tracer_and_can_start_a_span() -> None:
    tracer = get_tracer("test")
    assert isinstance(tracer, Tracer)
    with tracer.start_as_current_span("unit-test-span") as span:
        span.set_attribute("argus.test", True)


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
