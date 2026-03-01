"""Tests for OpenTelemetry integration."""

import pytest
from contextlib import contextmanager
from typing import Iterator
from unittest.mock import patch, MagicMock


class TestSpan:
    """Tests for span context manager."""

    def test_span_is_context_manager(self):
        """Test that span is a context manager."""
        from autoflow.otel import span

        # span is a function decorated with @contextmanager
        assert callable(span)
        # It can be used as a context manager
        with span("test"):
            pass

    @patch("autoflow.otel.trace", None)
    def test_span_without_opentelemetry(self):
        """Test that span works without OpenTelemetry installed."""
        from autoflow.otel import span

        # Should not crash even without OpenTelemetry
        with span("test_span"):
            pass

        # If we got here, it worked
        assert True

    @patch("autoflow.otel.trace")
    def test_span_with_opentelemetry_available(self, mock_trace):
        """Test that span works when OpenTelemetry is available."""
        # Setup mock - trace.get_tracer() returns a tracer
        mock_tracer = MagicMock()
        mock_span_context = MagicMock()

        # Configure the tracer's start_as_current_span to return a context manager
        mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock()
        mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock()

        # trace.get_tracer("autoflow") should return the mock_tracer
        mock_trace.get_tracer.return_value = mock_tracer

        from autoflow.otel import span

        # Should use OpenTelemetry
        with span("test_span"):
            pass

        # Verify OpenTelemetry was used
        mock_trace.get_tracer.assert_called_once_with("autoflow")
        mock_tracer.start_as_current_span.assert_called_once_with("test_span")

    @patch("autoflow.otel.trace", None)
    def test_span_returns_early_without_trace(self):
        """Test that span returns early when trace is None."""
        from autoflow.otel import span

        executed = False

        with span("test_span"):
            executed = True

        assert executed is True

    def test_span_name_parameter(self):
        """Test that span accepts name parameter."""
        from autoflow.otel import span

        # Should not crash
        with span("custom_span_name"):
            pass

    @patch("autoflow.otel.trace")
    def test_span_with_different_names(self, mock_trace):
        """Test span with various span names."""
        mock_tracer = MagicMock()
        mock_span_context = MagicMock()

        mock_tracer.get_tracer.return_value = mock_tracer
        mock_tracer.start_as_current_span.return_value = mock_span_context
        mock_span_context.__enter__ = MagicMock()
        mock_span_context.__exit__ = MagicMock(return_value=False)

        mock_trace.get_tracer.return_value = mock_tracer
        mock_trace.__bool__ = True

        from autoflow.otel import span

        span_names = [
            "operation_1",
            "database_query",
            "api_call",
            "workflow_execution",
        ]

        for span_name in span_names:
            with span(span_name):
                pass

            # Verify each span was created with correct name
            mock_tracer.start_as_current_span.assert_any_call(span_name)

    @patch("autoflow.otel.trace")
    def test_span_exception_handling(self, mock_trace):
        """Test that span handles exceptions properly."""
        mock_tracer = MagicMock()
        mock_span_context = MagicMock()

        mock_tracer.get_tracer.return_value = mock_tracer
        mock_tracer.start_as_current_span.return_value = mock_span_context
        mock_span_context.__enter__ = MagicMock()
        mock_span_context.__exit__ = MagicMock(return_value=False)

        mock_trace.get_tracer.return_value = mock_tracer
        mock_trace.__bool__ = True

        from autoflow.otel import span

        # Test normal execution
        with span("test_span"):
            result = 42

        assert result == 42
        mock_span_context.__enter__.assert_called_once()
        mock_span_context.__exit__.assert_called_once_with(None, None, None)

    @patch("autoflow.otel.trace")
    def test_span_with_exception(self, mock_trace):
        """Test that span handles exceptions."""
        mock_tracer = MagicMock()
        mock_span_context = MagicMock()

        mock_tracer.get_tracer.return_value = mock_tracer
        mock_tracer.start_as_current_span.return_value = mock_span_context
        mock_span_context.__enter__ = MagicMock()
        mock_span_context.__exit__ = MagicMock(return_value=False)

        mock_trace.get_tracer.return_value = mock_tracer
        mock_trace.__bool__ = True

        from autoflow.otel import span

        exception_raised = False

        try:
            with span("exception_span"):
                raise ValueError("Test exception")
        except ValueError:
            exception_raised = True

        assert exception_raised is True
        mock_span_context.__exit__.assert_called_once()


class TestOpenTelemetryIntegration:
    """Integration tests for OpenTelemetry module."""

    @patch("autoflow.otel.trace", None)
    def test_module_graceful_degradation(self):
        """Test that module gracefully degrades without OpenTelemetry."""
        import autoflow.otel as otel

        # Should not raise import error
        assert otel is not None

        # span should still work
        with otel.span("test"):
            pass

    def test_trace_attribute(self):
        """Test that trace attribute exists."""
        import autoflow.otel as otel

        # trace should be None (OpenTelemetry not installed)
        # or an actual trace module if it is installed
        assert hasattr(otel, "trace")

    @patch("autoflow.otel.trace")
    def test_trace_module_when_available(self, mock_trace):
        """Test trace module when OpenTelemetry is available."""
        mock_trace.__bool__ = True

        import autoflow.otel as otel

        assert otel.trace == mock_trace

    def test_span_function_usable(self):
        """Test that span function can be used in real code."""
        from autoflow.otel import span

        # Simulate real usage
        def operation():
            with span("database_query"):
                # Simulate work
                return "result"

        result = operation()
        assert result == "result"

    @patch("autoflow.otel.trace", None)
    def test_nested_spans_without_trace(self):
        """Test nested spans without OpenTelemetry."""
        from autoflow.otel import span

        with span("outer_span"):
            with span("inner_span_1"):
                pass
            with span("inner_span_2"):
                pass

        # Should complete without error
        assert True

    @patch("autoflow.otel.trace")
    def test_nested_spans_with_trace(self, mock_trace):
        """Test nested spans with OpenTelemetry available."""
        mock_tracer = MagicMock()
        mock_outer_span = MagicMock()
        mock_inner_span = MagicMock()

        # Configure the tracer
        mock_tracer.get_tracer.return_value = mock_tracer
        mock_tracer.start_as_current_span.side_effect = [
            mock_outer_span,
            mock_inner_span,
        ]

        mock_outer_span.__enter__ = MagicMock()
        mock_outer_span.__exit__ = MagicMock(return_value=False)
        mock_inner_span.__enter__ = MagicMock()
        mock_inner_span.__exit__ = MagicMock(return_value=False)

        mock_trace.get_tracer.return_value = mock_tracer

        from autoflow.otel import span

        with span("outer"):
            with span("inner"):
                pass

        # Should create nested spans - get_tracer called for each span
        assert mock_trace.get_tracer.call_count == 2
        assert mock_tracer.start_as_current_span.call_count == 2
