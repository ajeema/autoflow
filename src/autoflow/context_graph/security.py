"""
Security utilities for the Context Graph Framework.

This module provides input validation, sanitization, and security controls
that are configurable and extensible rather than rigid.
"""

import re
import string
from typing import Any, Optional, Callable, Set

# Pydantic for validation and serialization
from pydantic import BaseModel, Field, ConfigDict, field_validator

# Control characters to filter out (ASCII 0-31, except \t, \n, \r)
CONTROL_CHARS = set(chr(i) for i in range(32) if i not in (9, 10, 13))


# Module-level default sets for SecurityConfig
_DEFAULT_ENTITY_TYPES: Set[str] = {
    "brand",
    "company",
    "campaign",
    "creative",
    "publisher",
    "user",
    "product",
    "vertical",
    "domain",
    "goal",
    "inventory_category",
    "node",
    "entity",
}

_DEFAULT_RELATIONSHIP_TYPES: Set[str] = {
    "related_to",
    "belongs_to",
    "part_of",
    "competes_with",
    "acquired_by",
    "partnered_with",
    "advertised_on",
    "targets",
    "optimized_for",
    "uses_creative",
    "performed_on",
    "converted_from",
    "created_before",
    "created_after",
    "created_by",
    "ran_on",
    "performed_best_on",
    "performed_worst_on",
    "categorized_as",
    "has_audience",
    "safe_for",
    "owned_by",
    "mentions_brand",
    "contextual_topic",
    "in_vertical",
    "sells_to",
    "targets_demographic",
}


def _default_entity_types() -> Set[str]:
    return _DEFAULT_ENTITY_TYPES.copy()


def _default_relationship_types() -> Set[str]:
    return _DEFAULT_RELATIONSHIP_TYPES.copy()


class SecurityConfig(BaseModel):
    """
    Centralized security configuration.

    Defaults are provided but all fields are configurable
    to avoid being overly rigid.
    """

    # Pydantic configuration
    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
        arbitrary_types_allowed=True,
    )

    # Entity types - can be extended via allow_entity_type()
    DEFAULT_ENTITY_TYPES: Set[str] = _DEFAULT_ENTITY_TYPES
    DEFAULT_RELATIONSHIP_TYPES: Set[str] = _DEFAULT_RELATIONSHIP_TYPES

    # Resource limits
    DEFAULT_MAX_HOPS: int = 5
    DEFAULT_MAX_ENTITIES_PER_QUERY: int = 1000
    DEFAULT_MAX_PROPERTY_COUNT: int = 100
    DEFAULT_MAX_PROPERTY_VALUE_LENGTH: int = 10000

    # LLM limits
    DEFAULT_MAX_INPUT_LENGTH: int = 5000
    DEFAULT_MAX_OUTPUT_LENGTH: int = 10000

    # Instance fields
    enable_validation: bool = True
    enable_sanitization: bool = True
    allowed_entity_types: Set[str] = Field(default_factory=_default_entity_types)
    allowed_relationship_types: Set[str] = Field(default_factory=_default_relationship_types)
    max_hops: int = DEFAULT_MAX_HOPS
    max_entities_per_query: int = DEFAULT_MAX_ENTITIES_PER_QUERY
    max_property_count: int = DEFAULT_MAX_PROPERTY_COUNT
    max_property_value_length: int = DEFAULT_MAX_PROPERTY_VALUE_LENGTH
    max_input_length: int = DEFAULT_MAX_INPUT_LENGTH
    max_output_length: int = DEFAULT_MAX_OUTPUT_LENGTH

    def allow_entity_type(self, entity_type: str) -> None:
        """Add an entity type to the allowed list."""
        self.allowed_entity_types.add(entity_type.lower())

    def allow_relationship_type(self, relationship_type: str) -> None:
        """Add a relationship type to the allowed list."""
        self.allowed_relationship_types.add(relationship_type.lower())

    def disable_validation(self) -> None:
        """Disable validation (useful for testing)."""
        self.enable_validation = False

    # ========================================================================
    # Configuration Profiles
    # ========================================================================

    @classmethod
    def development(cls) -> "SecurityConfig":
        """
        Development-friendly configuration.

        Disables validation and sanitization for faster development iteration.
        """
        return cls(
            enable_validation=False,
            enable_sanitization=False,
        )

    @classmethod
    def testing(cls) -> "SecurityConfig":
        """
        Testing configuration.

        Enables validation but with relaxed limits for testing scenarios.
        """
        config = cls(
            enable_validation=True,
            enable_sanitization=True,
            max_hops=10,
        )
        config.max_entities_per_query = 10000
        config.max_property_count = 500
        config.max_property_value_length = 50000
        return config

    @classmethod
    def production(cls) -> "SecurityConfig":
        """
        Production configuration.

        Strict validation and sanitization with conservative limits.
        """
        return cls(
            enable_validation=True,
            enable_sanitization=True,
            max_hops=5,
            max_property_count=100,
            max_property_value_length=10000,
        )


class Validator:
    """
    Input validation with configurable rules.

    Validation is strict but can be disabled or extended.
    """

    # Regex patterns for validation
    PROPERTY_KEY_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
    ENTITY_ID_PATTERN = re.compile(r'^[a-zA-Z0-9:_\-\.]+$')
    SAFE_STRING_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-_\.@]+\Z')

    # Dangerous Cypher keywords
    CYpher_KEYWORDS = {
        "delete", "drop", "detach", "remove", "merge", "create",
        "set", "foreach", "load", "csv", "call", "with",
    }

    def __init__(self, config: Optional[SecurityConfig] = None):
        """
        Initialize validator.

        Args:
            config: Security configuration (uses defaults if None)
        """
        self.config = config or SecurityConfig()

    def validate_entity_type(self, entity_type: str) -> str:
        """
        Validate entity type against allowlist.

        Args:
            entity_type: The entity type to validate

        Returns:
            The normalized (lowercase) entity type

        Raises:
            ValueError: If validation enabled and type not in allowlist
        """
        if not self.config.enable_validation:
            return entity_type.lower()

        normalized = entity_type.lower()
        if normalized not in self.config.allowed_entity_types:
            raise ValueError(
                f"Invalid entity type '{entity_type}'. "
                f"Allowed types: {sorted(self.config.allowed_entity_types)}. "
                f"Add custom types with config.allow_entity_type('{entity_type}')"
            )

        return normalized

    def validate_relationship_type(self, relationship_type: str) -> str:
        """
        Validate relationship type against allowlist.

        Args:
            relationship_type: The relationship type to validate

        Returns:
            The normalized (lowercase) relationship type

        Raises:
            ValueError: If validation enabled and type not in allowlist
        """
        if not self.config.enable_validation:
            return relationship_type.lower()

        normalized = relationship_type.lower()
        if normalized not in self.config.allowed_relationship_types:
            raise ValueError(
                f"Invalid relationship type '{relationship_type}'. "
                f"Allowed types: {sorted(self.config.allowed_relationship_types)}. "
                f"Add custom types with config.allow_relationship_type('{relationship_type}')"
            )

        return normalized

    def validate_property_key(self, key: str) -> str:
        """
        Validate property key is safe for Cypher queries.

        Args:
            key: The property key to validate

        Returns:
            The validated key

        Raises:
            ValueError: If key contains unsafe characters
        """
        if not self.config.enable_validation:
            return key

        if not self.PROPERTY_KEY_PATTERN.match(key):
            raise ValueError(
                f"Invalid property key '{key}'. "
                f"Keys must match pattern: {self.PROPERTY_KEY_PATTERN.pattern}"
            )

        return key

    def validate_property_dict(self, properties: dict[str, Any]) -> dict[str, Any]:
        """
        Validate all property keys and values.

        Args:
            properties: Dictionary of properties to validate

        Returns:
            Validated properties dictionary

        Raises:
            ValueError: If validation fails
        """
        if not self.config.enable_validation:
            return properties

        if len(properties) > self.config.max_property_count:
            raise ValueError(
                f"Too many properties ({len(properties)}). "
                f"Maximum: {self.config.max_property_count}"
            )

        validated = {}
        for key, value in properties.items():
            # Validate key
            validated_key = self.validate_property_key(key)

            # Validate value (basic checks)
            if isinstance(value, str):
                if len(value) > self.config.max_property_value_length:
                    raise ValueError(
                        f"Property value for '{key}' too long. "
                        f"Maximum: {self.config.max_property_value_length}"
                    )

            validated[validated_key] = value

        return validated

    def validate_entity_id(self, entity_id: str) -> str:
        """
        Validate entity ID format.

        Args:
            entity_id: The entity ID to validate

        Returns:
            The validated entity ID

        Raises:
            ValueError: If ID format is invalid
        """
        if not self.config.enable_validation:
            return entity_id

        if not self.ENTITY_ID_PATTERN.match(entity_id):
            raise ValueError(
                f"Invalid entity ID '{entity_id}'. "
                f"IDs must match pattern: {self.ENTITY_ID_PATTERN.pattern}"
            )

        return entity_id

    def validate_max_hops(self, max_hops: int) -> int:
        """
        Validate and clamp max_hops to safe range.

        Args:
            max_hops: Requested max hops

        Returns:
            Clamped max hops
        """
        if not self.config.enable_validation:
            return max_hops

        return min(max_hops, self.config.max_hops)

    def is_safe_string(self, text: str) -> bool:
        """
        Check if string contains only safe characters.

        Args:
            text: String to check

        Returns:
            True if safe, False otherwise
        """
        return bool(self.SAFE_STRING_PATTERN.match(text))

    def validate_property_schema(
        self,
        entity_type: str,
        properties: dict[str, Any],
        schemas: Optional[dict[str, dict]] = None,
    ) -> dict[str, Any]:
        """
        Validate properties against optional schema.

        This is an optional stricter validation layer beyond basic type checking.
        Schemas define required properties, expected types, and valid choices.

        Args:
            entity_type: Type of entity
            properties: Properties to validate
            schemas: Optional schema mapping

        Schema format:
            {
                "brand": {
                    "name": (str, True),              # (type, required)
                    "tier": (str, False, ["premium", "basic", "mid_market"]),  # (type, required, choices)
                    "vertical": (str, False),
                }
            }

        Returns:
            Validated properties

        Raises:
            ValueError: If schema validation fails
        """
        if not self.config.enable_validation:
            return properties

        if not schemas or entity_type not in schemas:
            return properties

        schema = schemas[entity_type]
        validated = {}

        # Check required properties first
        for key, spec in schema.items():
            if len(spec) >= 2 and spec[1] and key not in properties:
                raise ValueError(
                    f"Required property '{key}' missing for entity type '{entity_type}'"
                )

            if key in properties:
                value = properties[key]
                expected_type = spec[0]

                # Type check
                if not isinstance(value, expected_type):
                    raise ValueError(
                        f"Property '{key}' must be of type {expected_type.__name__}, "
                        f"got {type(value).__name__}"
                    )

                # Choice check if provided
                if len(spec) >= 3 and value not in spec[2]:
                    raise ValueError(
                        f"Property '{key}' must be one of {spec[2]}, got '{value}'"
                    )

                validated[key] = value

        # Copy any other properties not in schema
        for key, value in properties.items():
            if key not in validated:
                validated[key] = value

        return validated


class Sanitizer:
    """
    Input sanitization for LLM prompts and user inputs.

    Removes common injection patterns while preserving legitimate content.
    """

    # Common prompt injection patterns
    INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?(previous\s+)?(instructions?|commands?)",
        r"forget\s+(all\s+)?(previous\s+)?(instructions?|commands?)",
        r"disregard\s+(all\s+)?(previous\s+)?(instructions?|commands?)",
        r"(instead|rather|alternatively)",
        r"system\s*:\s*you\s+are",
        r"(DROP|DELETE|TRUNCATE)\s+(TABLE|DATABASE|SCHEMA)",
        r"<\|[^\n]*\|>",  # Token manipulation
    ]

    def __init__(self, config: Optional[SecurityConfig] = None):
        """
        Initialize sanitizer.

        Args:
            config: Security configuration
        """
        self.config = config or SecurityConfig()
        self.injection_regex = re.compile("|".join(self.INJECTION_PATTERNS), re.IGNORECASE)

    def sanitize_llm_input(
        self,
        text: str,
        max_length: Optional[int] = None,
        remove_injections: bool = True,
    ) -> str:
        """
        Sanitize text for use in LLM prompts.

        Args:
            text: Input text to sanitize
            max_length: Maximum length (uses config default if None)
            remove_injections: Whether to remove injection patterns

        Returns:
            Sanitized text
        """
        if not self.config.enable_sanitization:
            return text

        # Truncate
        max_len = max_length or self.config.max_input_length
        text = text[:max_len]

        if remove_injections:
            # Remove injection patterns
            text = self.injection_regex.sub("", text)
            # Clean up extra whitespace
            text = re.sub(r"\s+", " ", text)

        return text.strip()

    def sanitize_property_value(self, value: Any) -> Any:
        """
        Sanitize property values.

        Args:
            value: Property value to sanitize

        Returns:
            Sanitized value
        """
        if not self.config.enable_sanitization:
            return value

        if isinstance(value, str):
            # Remove null bytes and control characters
            value = value.replace("\x00", "")
            value = "".join(char for char in value if char not in CONTROL_CHARS)
            # Truncate if too long
            if len(value) > self.config.max_property_value_length:
                value = value[: self.config.max_property_value_length]

        elif isinstance(value, (list, dict)):
            # Recursively sanitize collections
            if isinstance(value, list):
                return [self.sanitize_property_value(v) for v in value]
            else:
                return {k: self.sanitize_property_value(v) for k, v in value.items()}

        return value

    def sanitize_cypher_identifier(self, identifier: str) -> str:
        """
        Sanitize identifier for use in Cypher queries.

        Args:
            identifier: Identifier to sanitize

        Returns:
            Safe identifier (backtick-quoted if needed)
        """
        if not self.config.enable_sanitization:
            return identifier

        # If it matches safe pattern, return as-is
        if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier):
            return identifier

        # Otherwise, backtick-quote it (Neo4j's escaping mechanism)
        return f"`{identifier}`"


class SecurityAuditor:
    """
    Audit and logging for security events.

    Tracks validation failures, suspicious patterns, etc.
    """

    def __init__(self, enabled: bool = True):
        """
        Initialize auditor.

        Args:
            enabled: Whether to enable auditing
        """
        self.enabled = enabled
        self.violations: list[dict[str, Any]] = []

    def log_violation(
        self,
        violation_type: str,
        message: str,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Log a security violation.

        Args:
            violation_type: Type of violation (e.g., "invalid_entity_type")
            message: Human-readable message
            context: Additional context
        """
        if not self.enabled:
            return

        self.violations.append({
            "type": violation_type,
            "message": message,
            "context": context or {},
            "timestamp": None,  # Would use datetime.now() in production
        })

    def get_violations(self, violation_type: Optional[str] = None) -> list[dict[str, Any]]:
        """
        Get logged violations.

        Args:
            violation_type: Filter by violation type (None = all)

        Returns:
            List of violations
        """
        if violation_type:
            return [v for v in self.violations if v["type"] == violation_type]
        return self.violations.copy()

    def clear(self) -> None:
        """Clear all logged violations."""
        self.violations.clear()


# Global default configuration (can be overridden)
default_config = SecurityConfig()
default_validator = Validator(default_config)
default_sanitizer = Sanitizer(default_config)
default_auditor = SecurityAuditor()
