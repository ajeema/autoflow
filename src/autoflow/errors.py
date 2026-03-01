class AutoFlowError(Exception):
    """Base exception for AutoFlow."""


class ConfigurationError(AutoFlowError):
    """Raised when configuration is invalid."""


class PolicyViolation(AutoFlowError):
    """Raised when proposal violates policy."""


class StorageError(AutoFlowError):
    """Raised when graph storage fails."""


class EvaluationError(AutoFlowError):
    """Raised when evaluation fails."""


class ApplyError(AutoFlowError):
    """Raised when application of change fails."""