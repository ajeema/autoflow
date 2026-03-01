"""
Authentication and Authorization layer for Context Graph Framework.

This module provides pluggable security for controlling who can access
and modify the graph. Designed to be flexible for different use cases:
- API key based auth
- OAuth/JWT tokens
- RBAC (role-based access control)
- ABAC (attribute-based access control)
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Optional, Callable, Set, List
from enum import Enum
import hashlib
import json

# Pydantic for validation and serialization
from pydantic import BaseModel, Field, field_validator, ConfigDict, model_validator


class Permission(str, Enum):
    """Standard permissions for graph operations."""

    # Read permissions
    READ_ENTITY = "read_entity"
    READ_RELATIONSHIP = "read_relationship"
    TRAVERSE = "traverse"
    SEARCH = "search"
    QUERY = "query"

    # Write permissions
    CREATE_ENTITY = "create_entity"
    CREATE_RELATIONSHIP = "create_relationship"
    UPDATE_ENTITY = "update_entity"
    UPDATE_RELATIONSHIP = "update_relationship"
    DELETE_ENTITY = "delete_entity"
    DELETE_RELATIONSHIP = "delete_relationship"

    # Admin permissions
    MANAGE_SCHEMA = "manage_schema"
    MANAGE_USERS = "manage_users"
    EXPORT_DATA = "export_data"


class ResourceType(str, Enum):
    """Types of resources that can be protected."""

    ENTITY = "entity"
    RELATIONSHIP = "relationship"
    GRAPH = "graph"
    SCHEMA = "schema"
    USER = "user"
    DOMAIN = "domain"


class AuthContext(BaseModel):
    """
    Context about an authenticated request.

    Created by Authenticator and passed to Authorizer for decisions.
    """

    # Pydantic configuration
    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
        arbitrary_types_allowed=True,
        use_enum_values=True,
    )

    user_id: str
    username: Optional[str] = None
    roles: Set[str] = Field(default_factory=set)  # Empty set = no roles
    permissions: Set[Permission] = Field(default_factory=set)  # Pre-computed permissions
    attributes: dict[str, Any] = Field(default_factory=dict)  # For ABAC (e.g., department, tier)
    authenticated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    token: Optional[str] = None  # Original token for reference

    @property
    def is_authenticated(self) -> bool:
        """Check if context represents an authenticated user."""
        return bool(self.user_id)

    @property
    def is_expired(self) -> bool:
        """Check if authentication has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def has_permission(self, permission: Permission) -> bool:
        """Check if context has a specific permission."""
        return permission in self.permissions

    def has_role(self, role: str) -> bool:
        """Check if context has a specific role."""
        return role in self.roles

    def can(self, permission: Permission, resource: Optional[Any] = None) -> bool:
        """
        Check if context can perform an action.

        This is a convenience method that calls into Authorizer.
        For complex auth, use Authorizer directly.
        """
        return permission in self.permissions


class AuthResult(BaseModel):
    """Result of an authentication attempt."""

    # Pydantic configuration
    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
        arbitrary_types_allowed=True,
    )

    success: bool
    context: Optional[AuthContext] = None
    error: Optional[str] = None
    error_code: Optional[str] = None  # For API responses (e.g., "INVALID_TOKEN")


class Authenticator(ABC):
    """
    Abstract base for authenticators.

    Implementations validate credentials and create AuthContext.
    """

    @abstractmethod
    def authenticate(self, credentials: Any) -> AuthResult:
        """
        Authenticate a request.

        Args:
            credentials: The credentials to validate (token, api_key, etc.)

        Returns:
            AuthResult with AuthContext if successful
        """
        pass

    @abstractmethod
    def validate_token(self, token: str) -> AuthResult:
        """
        Validate an authentication token.

        Args:
            token: The token to validate

        Returns:
            AuthResult with AuthContext if valid
        """
        pass


class APIKeyAuthenticator(Authenticator):
    """
    Simple API key authentication.

    Useful for internal services, integrations, or simple deployments.
    Maps API keys to users with predefined roles/permissions.
    """

    def __init__(
        self,
        api_keys: dict[str, dict[str, Any]] = None,
        key_prefix: str = "ctx_",
    ):
        """
        Initialize API key authenticator.

        Args:
            api_keys: Dict mapping {api_key: {user_id, roles, permissions, attributes}}
                     If None, uses environment variables
            key_prefix: Required prefix for API keys (prevents accidental use)

        Example:
            ```python
            authenticator = APIKeyAuthenticator(api_keys={
                "ctx_prod_123abc": {
                    "user_id": "user_123",
                    "roles": {"analyst"},
                    "permissions": {Permission.READ_ENTITY, Permission.TRAVERSE},
                    "attributes": {"department": "marketing", "tier": "basic"}
                }
            })
            ```
        """
        self.key_prefix = key_prefix

        if api_keys is not None:
            self.api_keys = api_keys
        else:
            # Load from environment or config file
            self.api_keys = self._load_from_env()

    def _load_from_env(self) -> dict[str, dict[str, Any]]:
        """Load API keys from environment variables."""
        import os

        keys = {}
        # Format: CTX_API_KEY_user_id=roles:permission1,permission2
        for key, value in os.environ.items():
            if key.startswith("CTX_API_KEY_"):
                api_key = f"{self.key_prefix}{value.split(':')[0]}"
                user_id = key[len("CTX_API_KEY_"):].lower()

                keys[api_key] = {
                    "user_id": user_id,
                    "roles": set(),
                    "permissions": {Permission.READ_ENTITY, Permission.TRAVERSE},
                    "attributes": {},
                }

        return keys

    def authenticate(self, credentials: Any) -> AuthResult:
        """Authenticate using an API key."""
        if not isinstance(credentials, str):
            return AuthResult(
                success=False,
                error="Credentials must be a string (API key)",
                error_code="INVALID_CREDENTIALS",
            )

        if not credentials.startswith(self.key_prefix):
            return AuthResult(
                success=False,
                error=f"API key must start with '{self.key_prefix}'",
                error_code="INVALID_API_KEY_FORMAT",
            )

        key_data = self.api_keys.get(credentials)
        if not key_data:
            return AuthResult(
                success=False,
                error="Invalid API key",
                error_code="INVALID_API_KEY",
            )

        context = AuthContext(
            user_id=key_data["user_id"],
            username=key_data.get("username"),
            roles=key_data.get("roles", set()),
            permissions=key_data.get("permissions", set()),
            attributes=key_data.get("attributes", {}),
        )

        return AuthResult(success=True, context=context)

    def validate_token(self, token: str) -> AuthResult:
        """Validate an API key (alias for authenticate)."""
        return self.authenticate(token)


class JWTAuthenticator(Authenticator):
    """
    JWT token authentication.

    Useful for web applications, SSO integrations, etc.
    Decodes JWTs and validates signatures/claims.
    """

    def __init__(
        self,
        secret: str,
        algorithm: str = "HS256",
        issuer: Optional[str] = None,
        audience: Optional[str] = None,
    ):
        """
        Initialize JWT authenticator.

        Args:
            secret: Secret key for verifying signatures
            algorithm: JWT algorithm (default: HS256)
            issuer: Expected issuer claim
            audience: Expected audience claim

        Note:
            Requires 'pyjwt' package: pip install pyjwt
        """
        try:
            import jwt
        except ImportError:
            raise ImportError("JWTAuthenticator requires 'pyjwt' package. Install with: pip install pyjwt")

        self.jwt = jwt
        self.secret = secret
        self.algorithm = algorithm
        self.issuer = issuer
        self.audience = audience

    def authenticate(self, credentials: Any) -> AuthResult:
        """Authenticate using a JWT token."""
        if not isinstance(credentials, str):
            return AuthResult(
                success=False,
                error="Credentials must be a string (JWT token)",
                error_code="INVALID_CREDENTIALS",
            )

        return self.validate_token(credentials)

    def validate_token(self, token: str) -> AuthResult:
        """Validate and decode a JWT token."""
        try:
            # Decode and validate
            payload = self.jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm],
                issuer=self.issuer,
                audience=self.audience,
            )

            # Extract claims
            user_id = payload.get("sub", payload.get("user_id"))
            if not user_id:
                return AuthResult(
                    success=False,
                    error="Token missing 'sub' or 'user_id' claim",
                    error_code="INVALID_TOKEN",
                )

            # Extract roles and permissions
            roles = set(payload.get("roles", []))
            permissions = {p if isinstance(p, Permission) else Permission(p) for p in payload.get("permissions", [])}

            # Create context
            context = AuthContext(
                user_id=user_id,
                username=payload.get("username", payload.get("name")),
                roles=roles,
                permissions=permissions,
                attributes=payload.get("attributes", {}),
                expires_at=datetime.fromtimestamp(payload["exp"]) if "exp" in payload else None,
                token=token,
            )

            if context.is_expired:
                return AuthResult(
                    success=False,
                    error="Token has expired",
                    error_code="TOKEN_EXPIRED",
                )

            return AuthResult(success=True, context=context)

        except self.jwt.ExpiredSignatureError:
            return AuthResult(
                success=False,
                error="Token has expired",
                error_code="TOKEN_EXPIRED",
            )
        except self.jwt.InvalidTokenError as e:
            return AuthResult(
                success=False,
                error=f"Invalid token: {str(e)}",
                error_code="INVALID_TOKEN",
            )


class Authorizer(ABC):
    """
    Abstract base for authorizers.

    Implementations check if a given AuthContext can perform an action.
    """

    @abstractmethod
    def can(
        self,
        context: AuthContext,
        permission: Permission,
        resource: Optional[Any] = None,
        resource_type: Optional[ResourceType] = None,
    ) -> bool:
        """
        Check if context can perform an action.

        Args:
            context: AuthContext from Authenticator
            permission: Permission being requested
            resource: The specific resource (e.g., entity_id)
            resource_type: Type of resource

        Returns:
            True if authorized, False otherwise
        """
        pass


class RBACAuthorizer(Authorizer):
    """
    Role-Based Access Control authorizer.

    Maps roles to permissions. Simple and widely used.
    """

    # Default role mappings
    DEFAULT_ROLE_PERMISSIONS: dict[str, set[Permission]] = {
        "admin": {p for p in Permission},  # All permissions
        "editor": {
            Permission.READ_ENTITY,
            Permission.READ_RELATIONSHIP,
            Permission.TRAVERSE,
            Permission.SEARCH,
            Permission.QUERY,
            Permission.CREATE_ENTITY,
            Permission.CREATE_RELATIONSHIP,
            Permission.UPDATE_ENTITY,
            Permission.UPDATE_RELATIONSHIP,
        },
        "analyst": {
            Permission.READ_ENTITY,
            Permission.READ_RELATIONSHIP,
            Permission.TRAVERSE,
            Permission.SEARCH,
            Permission.QUERY,
        },
        "viewer": {
            Permission.READ_ENTITY,
            Permission.READ_RELATIONSHIP,
        },
    }

    def __init__(self, role_permissions: Optional[dict[str, set[Permission]]] = None):
        """
        Initialize RBAC authorizer.

        Args:
            role_permissions: Custom role->permissions mapping
                             Uses defaults if not provided
        """
        self.role_permissions = role_permissions or self.DEFAULT_ROLE_PERMISSIONS.copy()

    def can(
        self,
        context: AuthContext,
        permission: Permission,
        resource: Optional[Any] = None,
        resource_type: Optional[ResourceType] = None,
    ) -> bool:
        """Check if context can perform an action via RBAC."""
        # Check direct permissions
        if permission in context.permissions:
            return True

        # Check role-based permissions
        for role in context.roles:
            role_perms = self.role_permissions.get(role, set())
            if permission in role_perms:
                return True

        return False


class ABACAuthorizer(Authorizer):
    """
    Attribute-Based Access Control authorizer.

    Uses policies that evaluate attributes of the user, resource, and action.
    More flexible than RBAC but more complex.
    """

    def __init__(self):
        """Initialize ABAC authorizer."""
        self.policies: list[Callable] = []

    def add_policy(self, policy: Callable[[AuthContext, Permission, Any], bool]) -> None:
        """
        Add a policy function.

        Args:
            policy: Function that takes (context, permission, resource) and returns bool

        Example:
            ```python
            authorizer.add_policy(
                lambda ctx, perm, res: (
                    perm == Permission.DELETE_ENTITY and
                    ctx.attributes.get("tier") == "premium"
                )
            )
            ```
        """
        self.policies.append(policy)

    def can(
        self,
        context: AuthContext,
        permission: Permission,
        resource: Optional[Any] = None,
        resource_type: Optional[ResourceType] = None,
    ) -> bool:
        """Check if context can perform an action via ABAC policies."""
        # Check direct permissions first
        if permission in context.permissions:
            return True

        # Evaluate policies
        for policy in self.policies:
            try:
                if policy(context, permission, resource):
                    return True
            except Exception:
                # Policy evaluation failed, deny access
                continue

        return False


class CompositeAuthorizer(Authorizer):
    """
    Composes multiple authorizers.

    Allows combining RBAC, ABAC, and custom logic.
    """

    def __init__(self, authorizers: Optional[list[Authorizer]] = None):
        """
        Initialize composite authorizer.

        Args:
            authorizers: List of authorizers to check (in order)

        Example:
            ```python
            authorizer = CompositeAuthorizer([
                RBACAuthorizer(),
                ABACAuthorizer(),
            ])
            ```
        """
        self.authorizers = authorizers or []

    def add_authorizer(self, authorizer: Authorizer) -> None:
        """Add an authorizer to the chain."""
        self.authorizers.append(authorizer)

    def can(
        self,
        context: AuthContext,
        permission: Permission,
        resource: Optional[Any] = None,
        resource_type: Optional[ResourceType] = None,
    ) -> bool:
        """Check if any authorizer grants permission."""
        # If no authorizers, deny by default
        if not self.authorizers:
            return False

        # Check each authorizer (any one allowing = allow)
        for authorizer in self.authorizers:
            if authorizer.can(context, permission, resource, resource_type):
                return True

        return False


class AuthMiddleware:
    """
    Middleware combining authentication and authorization.

    This is the main entry point for securing Context Graph operations.
    """

    def __init__(
        self,
        authenticator: Authenticator,
        authorizer: Authorizer,
        require_auth: bool = True,
    ):
        """
        Initialize auth middleware.

        Args:
            authenticator: The authenticator to use
            authorizer: The authorizer to use
            require_auth: Whether to require authentication (can be disabled for dev)
        """
        self.authenticator = authenticator
        self.authorizer = authorizer
        self.require_auth = require_auth

    def check(
        self,
        credentials: Any,
        permission: Permission,
        resource: Optional[Any] = None,
        resource_type: Optional[ResourceType] = None,
    ) -> tuple[bool, Optional[AuthContext], Optional[str]]:
        """
        Check if a request is authenticated and authorized.

        Args:
            credentials: The credentials to authenticate
            permission: The permission being requested
            resource: The resource being accessed
            resource_type: The type of resource

        Returns:
            Tuple of (is_allowed, auth_context, error_message)
        """
        # Skip if auth not required
        if not self.require_auth:
            return True, None, None

        # Authenticate
        auth_result = self.authenticator.authenticate(credentials)
        if not auth_result.success:
            return False, None, auth_result.error or "Authentication failed"

        context = auth_result.context

        # Check expiration
        if context.is_expired:
            return False, None, "Authentication expired"

        # Authorize
        if not self.authorizer.can(context, permission, resource, resource_type):
            return False, context, "Insufficient permissions"

        return True, context, None


# Convenience function for common use cases
def create_api_key_auth(
    api_keys: dict[str, dict[str, Any]],
    roles: Optional[dict[str, set[Permission]]] = None,
) -> AuthMiddleware:
    """
    Create API key authentication middleware.

    Args:
        api_keys: Mapping of API keys to user data
        roles: Optional custom role permissions

    Returns:
        Configured AuthMiddleware

    Example:
        ```python
        auth = create_api_key_auth({
            "ctx_prod_123abc": {
                "user_id": "user_123",
                "roles": {"analyst"},
                "attributes": {"department": "marketing"}
            }
        })

        allowed, context, error = auth.check(
            credentials="ctx_prod_123abc",
            permission=Permission.READ_ENTITY
        )
        ```
    """
    authenticator = APIKeyAuthenticator(api_keys)
    authorizer = RBACAuthorizer(role_permissions=roles)
    return AuthMiddleware(authenticator, authorizer)
