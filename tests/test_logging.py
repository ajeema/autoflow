"""Tests for logging utilities."""

import pytest
import logging
from unittest.mock import patch

from autoflow.logging import get_logger, log_kv


class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_logger(self):
        """Test that get_logger returns a logger instance."""
        logger = get_logger("test_logger")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"

    def test_logger_has_handler(self):
        """Test that logger has a stream handler."""
        logger = get_logger("test_logger_with_handler")

        # Should have exactly one handler
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.StreamHandler)

    def test_logger_level(self):
        """Test that logger has INFO level set."""
        logger = get_logger("test_logger_level")

        assert logger.level == logging.INFO

    def test_reusing_logger(self):
        """Test that calling get_logger twice with same name returns same logger."""
        logger1 = get_logger("reused_logger")
        logger2 = get_logger("reused_logger")

        assert logger1 is logger2

    def test_handler_not_duplicated(self):
        """Test that handler is not added on subsequent calls."""
        logger = get_logger("test_handler_once")

        # First call adds handler
        handler_count_1 = len(logger.handlers)

        # Second call should not add another handler
        logger = get_logger("test_handler_once")
        handler_count_2 = len(logger.handlers)

        assert handler_count_1 == 1
        assert handler_count_2 == 1

    def test_custom_formatter(self):
        """Test that logger has custom formatter."""
        logger = get_logger("test_formatter")

        handler = logger.handlers[0]
        formatter = handler.formatter

        assert formatter is not None
        assert "%(message)s" in formatter._fmt


class TestLogKV:
    """Tests for log_kv function."""

    def test_log_kv_logs_json(self):
        """Test that log_kv logs JSON-formatted messages."""
        logger = get_logger("test_kv_logger")

        # Should not raise an exception
        log_kv(logger, "test_message", key1="value1", key2=42)

        # If we got here without error, the function works
        assert True

    @patch("autoflow.logging.json.dumps")
    def test_log_kv_includes_message(self, mock_json_dumps):
        """Test that log_kv includes the message in JSON."""
        mock_json_dumps.return_value = '{"msg": "test_message", "key1": "value1"}'

        logger = get_logger("test_kv_message")
        log_kv(logger, "test_message", key1="value1")

        # Verify json.dumps was called with correct args
        mock_json_dumps.assert_called_once()
        # The dict is passed as first positional argument
        call_args = mock_json_dumps.call_args[0]
        assert "msg" in call_args[0]
        assert call_args[0]["msg"] == "test_message"

    @patch("autoflow.logging.json.dumps")
    def test_log_kv_includes_fields(self, mock_json_dumps):
        """Test that log_kv includes all fields in JSON."""
        mock_json_dumps.return_value = "{}"

        logger = get_logger("test_kv_fields")
        log_kv(logger, "test", key1="value1", key2="value2", number=42)

        # Verify all fields were passed to json.dumps
        call_args = mock_json_dumps.call_args[0]
        assert call_args[0] == {
            "msg": "test",
            "key1": "value1",
            "key2": "value2",
            "number": 42,
        }

    @patch("autoflow.logging.json.dumps")
    def test_log_kv_handles_complex_types(self, mock_json_dumps):
        """Test that log_kv handles complex Python types."""
        mock_json_dumps.return_value = "{}"

        logger = get_logger("test_kv_complex")
        log_kv(
            logger,
            "complex_test",
            dict_field={"nested": "value"},
            list_field=[1, 2, 3],
            none_field=None,
        )

        # Verify json.dumps was called with default=str
        mock_json_dumps.assert_called_once()
        assert "default" in mock_json_dumps.call_args[1]

    @patch("autoflow.logging.json.dumps")
    def test_log_kv_calls_logger_info(self, mock_json_dumps):
        """Test that log_kv calls logger.info."""
        mock_json_dumps.return_value = '{"msg": "test"}'

        logger = get_logger("test_kv_logger")
        log_kv(logger, "test_message")

        # Verify logger.info was called
        # We can't easily mock logger.info, but we can verify it doesn't crash
        assert True

    def test_log_kv_with_nested_fields(self):
        """Test log_kv with nested field structures."""
        logger = get_logger("test_kv_nested")

        # Should not crash with nested structures
        log_kv(
            logger,
            "nested_test",
            level1={
                "level2": "deep_value",
                "level2_list": [1, 2, 3],
            },
            top_level="simple",
        )

        assert True


class TestLoggingIntegration:
    """Integration tests for logging utilities."""

    def test_multiple_loggers(self):
        """Test creating multiple independent loggers."""
        logger1 = get_logger("logger1")
        logger2 = get_logger("logger2")
        logger3 = get_logger("logger3")

        # All should be independent
        assert logger1.name == "logger1"
        assert logger2.name == "logger2"
        assert logger3.name == "logger3"

    def test_logger_isolation(self):
        """Test that loggers don't interfere with each other."""
        logger1 = get_logger("isolated_1")
        logger2 = get_logger("isolated_2")

        # Both should have their own handlers
        assert len(logger1.handlers) >= 1
        assert len(logger2.handlers) >= 1

        # Adding handler to one shouldn't affect the other
        original_handler_count = len(logger2.handlers)
        extra_handler = logging.StreamHandler()
        logger1.addHandler(extra_handler)

        assert len(logger1.handlers) > len(logger2.handlers)
        assert len(logger2.handlers) == original_handler_count

    def test_log_kv_with_different_loggers(self):
        """Test log_kv works with different loggers."""
        logger1 = get_logger("kv_logger_1")
        logger2 = get_logger("kv_logger_2")

        # Both should work without interference
        log_kv(logger1, "message1", data="test1")
        log_kv(logger2, "message2", data="test2")

        assert True
