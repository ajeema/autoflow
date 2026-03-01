"""Tests for errors module."""

import pytest

from autoflow.errors import (
    AutoFlowError,
    ConfigurationError,
    PolicyViolation,
    StorageError,
    EvaluationError,
    ApplyError,
)


class TestAutoFlowError:
    """Tests for AutoFlowError base exception."""

    def test_is_exception(self):
        """Test that AutoFlowError is an exception."""
        assert issubclass(AutoFlowError, Exception)

    def test_raise_base_error(self):
        """Test raising base AutoFlowError."""
        with pytest.raises(AutoFlowError):
            raise AutoFlowError("Test error")

    def test_error_message(self):
        """Test error message is preserved."""
        error = AutoFlowError("Test message")
        assert str(error) == "Test message"


class TestConfigurationError:
    """Tests for ConfigurationError."""

    def test_is_autoflow_error(self):
        """Test that ConfigurationError inherits from AutoFlowError."""
        assert issubclass(ConfigurationError, AutoFlowError)

    def test_raise_configuration_error(self):
        """Test raising ConfigurationError."""
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("Invalid configuration")


class TestPolicyViolation:
    """Tests for PolicyViolation."""

    def test_is_autoflow_error(self):
        """Test that PolicyViolation inherits from AutoFlowError."""
        assert issubclass(PolicyViolation, AutoFlowError)

    def test_raise_policy_violation(self):
        """Test raising PolicyViolation."""
        with pytest.raises(PolicyViolation):
            raise PolicyViolation("Path not allowed")

    def test_policy_violation_message(self):
        """Test PolicyViolation message."""
        error = PolicyViolation("Risk exceeds policy limit")
        assert "Risk" in str(error)


class TestStorageError:
    """Tests for StorageError."""

    def test_is_autoflow_error(self):
        """Test that StorageError inherits from AutoFlowError."""
        assert issubclass(StorageError, AutoFlowError)

    def test_raise_storage_error(self):
        """Test raising StorageError."""
        with pytest.raises(StorageError):
            raise StorageError("Database connection failed")


class TestEvaluationError:
    """Tests for EvaluationError."""

    def test_is_autoflow_error(self):
        """Test that EvaluationError inherits from AutoFlowError."""
        assert issubclass(EvaluationError, AutoFlowError)

    def test_raise_evaluation_error(self):
        """Test raising EvaluationError."""
        with pytest.raises(EvaluationError):
            raise EvaluationError("Evaluation failed")

    def test_evaluation_error_with_cause(self):
        """Test EvaluationError with a cause."""
        original_error = ValueError("Original error")
        with pytest.raises(EvaluationError) as exc_info:
            raise EvaluationError("Wrapped error") from original_error

        assert exc_info.value.__cause__ is original_error


class TestApplyError:
    """Tests for ApplyError."""

    def test_is_autoflow_error(self):
        """Test that ApplyError inherits from AutoFlowError."""
        assert issubclass(ApplyError, AutoFlowError)

    def test_raise_apply_error(self):
        """Test raising ApplyError."""
        with pytest.raises(ApplyError):
            raise ApplyError("Failed to apply proposal")


class TestErrorHierarchy:
    """Tests for error hierarchy."""

    def test_all_errors_inherit_from_base(self):
        """Test that all custom errors inherit from AutoFlowError."""
        error_classes = [
            ConfigurationError,
            PolicyViolation,
            StorageError,
            EvaluationError,
            ApplyError,
        ]

        for error_class in error_classes:
            assert issubclass(error_class, AutoFlowError)

    def test_all_errors_are_exceptions(self):
        """Test that all errors are Exception subclasses."""
        error_classes = [
            AutoFlowError,
            ConfigurationError,
            PolicyViolation,
            StorageError,
            EvaluationError,
            ApplyError,
        ]

        for error_class in error_classes:
            assert issubclass(error_class, Exception)

    def test_catch_base_error(self):
        """Test that all errors can be caught as AutoFlowError."""
        errors = [
            ConfigurationError("config"),
            PolicyViolation("policy"),
            StorageError("storage"),
            EvaluationError("eval"),
            ApplyError("apply"),
        ]

        for error in errors:
            try:
                raise error
            except AutoFlowError:
                pass  # Should catch all
            else:
                pytest.fail(f"Failed to catch {error.__class__.__name__}")
