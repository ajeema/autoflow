"""
Context Graph Framework exceptions.

Provides a hierarchy of exceptions for better error handling and debugging.
"""

from typing import Any, Optional


class ContextGraphError(Exception):
    """Base exception for all Context Graph errors."""

    pass


class EntityNotFoundError(ContextGraphError):
    """Entity not found in graph."""

    def __init__(self, entity_id: str, message: Optional[str] = None) -> None:
        """
        Initialize entity not found error.

        Args:
            entity_id: The entity ID that was not found
            message: Optional custom message
        """
        self.entity_id = entity_id
        super().__init__(message or f"Entity not found: {entity_id}")


class RelationshipNotFoundError(ContextGraphError):
    """Relationship not found in graph."""

    def __init__(self, relationship_id: str, message: Optional[str] = None) -> None:
        """
        Initialize relationship not found error.

        Args:
            relationship_id: The relationship ID that was not found
            message: Optional custom message
        """
        self.relationship_id = relationship_id
        super().__init__(message or f"Relationship not found: {relationship_id}")


class ValidationError(ContextGraphError):
    """Input validation failed."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
    ) -> None:
        """
        Initialize validation error.

        Args:
            message: Error message
            field: Optional field name that failed validation
            value: Optional value that failed validation
        """
        self.field = field
        self.value = value
        super().__init__(message)


class AuthenticationError(ContextGraphError):
    """Authentication failed."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
    ) -> None:
        """
        Initialize authentication error.

        Args:
            message: Error message
            error_code: Optional machine-readable error code
        """
        self.error_code = error_code
        super().__init__(message)


class AuthorizationError(ContextGraphError):
    """Authorization failed - insufficient permissions."""

    def __init__(
        self,
        message: str,
        required_permission: Optional[str] = None,
        resource: Optional[str] = None,
    ) -> None:
        """
        Initialize authorization error.

        Args:
            message: Error message
            required_permission: Optional permission that was required
            resource: Optional resource being accessed
        """
        self.required_permission = required_permission
        self.resource = resource
        super().__init__(message)


class QueryError(ContextGraphError):
    """Graph query execution failed."""

    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
    ) -> None:
        """
        Initialize query error.

        Args:
            message: Error message
            query: Optional query that failed
        """
        self.query = query
        super().__init__(message)


class BackendError(ContextGraphError):
    """Backend operation failed."""

    def __init__(
        self,
        message: str,
        backend: Optional[str] = None,
    ) -> None:
        """
        Initialize backend error.

        Args:
            message: Error message
            backend: Optional backend name/type
        """
        self.backend = backend
        super().__init__(message)


class ConfigurationError(ContextGraphError):
    """Invalid configuration."""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
    ) -> None:
        """
        Initialize configuration error.

        Args:
            message: Error message
            config_key: Optional configuration key that is invalid
        """
        self.config_key = config_key
        super().__init__(message)
