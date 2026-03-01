# Authentication, Authorization, and Audit Logging Guide

Complete guide for securing the Context Graph Framework.

## Overview

Three complementary security layers:

1. **Authentication** - Who are you?
2. **Authorization** - What can you do?
3. **Audit Logging** - What did you do?

---

## Authentication

### What It Does

Validates credentials and creates an `AuthContext` with:
- User identity (user_id, username)
- Roles (admin, analyst, editor, etc.)
- Permissions (read_entity, delete_entity, etc.)
- Attributes (department, tier, etc.) - for ABAC

### Supported Methods

#### 1. API Key Authentication (Simplest)

```python
from autoflow.context_graph.auth import APIKeyAuthenticator, create_api_key_auth

# Define your API keys
api_keys = {
    "ctx_prod_abc123": {
        "user_id": "user_001",
        "username": "alice",
        "roles": {"admin"},
        "permissions": {Permission.READ_ENTITY, Permission.DELETE_ENTITY},
        "attributes": {"department": "engineering", "tier": "premium"}
    }
}

# Create auth middleware
auth = create_api_key_auth(api_keys)

# Check a request
allowed, context, error = auth.check(
    credentials="ctx_prod_abc123",
    permission=Permission.DELETE_ENTITY
)

if allowed:
    print(f"User {context.username} is authorized")
else:
    print(f"Denied: {error}")
```

**Best for:**
- Internal services
- Simple deployments
- Testing/development

#### 2. JWT Authentication (Production)

```python
from autoflow.context_graph.auth import JWTAuthenticator

authenticator = JWTAuthenticator(
    secret="your-secret-key",
    algorithm="HS256",
    issuer="your-app.com"
)

# Validate a JWT token
result = authenticator.validate_token(jwt_token)

if result.success:
    context = result.context
    print(f"Authenticated: {context.username}")
    print(f"Expires: {context.expires_at}")
```

**Best for:**
- Web applications
- SSO integrations
- Distributed systems
- Third-party access

### Custom Authenticators

```python
from autoflow.context_graph.auth import Authenticator, AuthResult, AuthContext

class CustomAuthenticator(Authenticator):
    def authenticate(self, credentials):
        # Your custom logic (OAuth, SAML, etc.)
        user = validate_with_your_service(credentials)

        if user:
            context = AuthContext(
                user_id=user.id,
                username=user.name,
                roles=user.roles,
                permissions=user.permissions
            )
            return AuthResult(success=True, context=context)

        return AuthResult(success=False, error="Invalid credentials")
```

---

## Authorization

### What It Does

Checks if an authenticated user can perform specific actions on resources.

### Supported Models

#### 1. Role-Based Access Control (RBAC)

```python
from autoflow.context_graph.auth import RBACAuthorizer

# Define roles and their permissions
role_permissions = {
    "admin": {p for p in Permission},  # All permissions
    "analyst": {
        Permission.READ_ENTITY,
        Permission.TRAVERSE,
        Permission.QUERY,
    },
    "viewer": {
        Permission.READ_ENTITY,
    }
}

authorizer = RBACAuthorizer(role_permissions)

# Check authorization
if authorizer.can(context, Permission.READ_ENTITY):
    # Allow
    pass
```

**How it works:**
1. User has roles: `{"analyst"}`
2. Role "analyst" has permissions: `{READ_ENTITY, TRAVERSE, QUERY}`
3. User requests: `READ_ENTITY`
4. Check: Is `READ_ENTITY` in analyst's permissions? → **ALLOWED**

#### 2. Attribute-Based Access Control (ABAC)

```python
from autoflow.context_graph.auth import ABACAuthorizer

authorizer = ABACAuthorizer()

# Policy 1: Premium tier can delete
authorizer.add_policy(
    lambda ctx, perm, res: (
        perm == Permission.DELETE_ENTITY and
        ctx.attributes.get("tier") == "premium"
    )
)

# Policy 2: Users can only read their department's entities
authorizer.add_policy(
    lambda ctx, perm, res: (
        perm == Permission.READ_ENTITY and
        res.get("department") == ctx.attributes.get("department")
    )
)
```

**How it works:**
- Evaluates policies against user attributes and resource properties
- More flexible than RBAC
- Can implement complex rules like:
  - "Users can only edit entities they created"
  - "Premium tier can delete, basic cannot"
  - "Marketing can only read marketing entities"

#### 3. Combined (RBAC + ABAC)

```python
from autoflow.context_graph.auth import CompositeAuthorizer

authorizer = CompositeAuthorizer([
    RBACAuthorizer(role_permissions),
    ABACAuthorizer(),  # With policies added
])

# Checks both - allows if either grants permission
```

### Available Permissions

```python
from autoflow.context_graph.auth import Permission

# Read operations
Permission.READ_ENTITY
Permission.READ_RELATIONSHIP
Permission.TRAVERSE
Permission.SEARCH
Permission.QUERY

# Write operations
Permission.CREATE_ENTITY
Permission.CREATE_RELATIONSHIP
Permission.UPDATE_ENTITY
Permission.UPDATE_RELATIONSHIP
Permission.DELETE_ENTITY
Permission.DELETE_RELATIONSHIP

# Admin operations
Permission.MANAGE_SCHEMA
Permission.MANAGE_USERS
Permission.EXPORT_DATA
```

---

## Audit Logging

### What It Does

Records all operations for:
- Security monitoring
- Compliance (SOC 2, HIPAA, GDPR, etc.)
- Debugging
- Forensics

### Setup

```python
from autoflow.context_graph.audit import Auditor, FileAuditBackend

# File-based (simple)
auditor = Auditor(
    backend=FileAuditBackend(filepath="audit.log"),
    enabled=True
)

# Async (non-blocking)
from autoflow.context_graph.audit import AsyncAuditBackend

auditor = Auditor(
    backend=AsyncAuditBackend(
        backend=FileAuditBackend(),
        queue_size=10000
    )
)
```

### Logging Events

```python
# Authentication
auditor.log_auth(success=True, user_id="user_001", username="alice")

# Authorization
auditor.log_authz(
    granted=True,
    user_id="user_001",
    permission="DELETE_ENTITY",
    resource_id="brand:nike"
)

# Read operations
auditor.log_read(
    resource_type="entity",
    resource_id="brand:nike",
    user_id="user_001",
    duration_ms=15.3
)

# Write operations
auditor.log_write(
    resource_type="entity",
    resource_id="brand:adidas",
    user_id="user_002",
    metadata={"name": "Adidas", "vertical": "Apparel"}
)

# Security events
auditor.log_security_event(
    event_type=AuditEventType.INJECTION_ATTEMPT,
    details="SQL injection blocked",
    user_id="unknown",
    metadata={"ip": "192.168.1.100"}
)
```

### Automatic Timing

```python
from autoflow.context_graph.audit import AuditContextManager

with AuditContextManager(
    auditor=auditor,
    event_type=AuditEventType.GRAPH_TRAVERSE,
    operation="traverse",
    user_id="user_001",
    resource_id="brand:nike"
):
    # Do work
    result = graph.traverse("brand:nike", pattern)

# Automatically logs duration when exiting context
```

### Audit Event Structure

```json
{
  "event_type": "entity_read",
  "timestamp": "2026-02-28T12:34:56.789Z",
  "user_id": "user_001",
  "username": "alice",
  "operation": "read",
  "resource_type": "entity",
  "resource_id": "brand:nike",
  "success": true,
  "metadata": {"caller_file": "/app/api.py", "caller_line": 42},
  "duration_ms": 15.3
}
```

---

## Putting It All Together

### Secured API Endpoint Example

```python
from flask import Flask, request, jsonify
from autoflow.context_graph.auth import create_api_key_auth, Permission
from autoflow.context_graph.audit import Auditor

app = Flask(__name__)

# Setup auth and audit
auth = create_api_key_auth(api_keys)
auditor = Auditor(enabled=True)

@app.route("/entities/<entity_id>", methods=["GET"])
def get_entity(entity_id):
    # Extract credentials
    api_key = request.headers.get("X-API-Key")

    # Check authorization
    allowed, context, error = auth.check(
        credentials=api_key,
        permission=Permission.READ_ENTITY,
        resource_id=entity_id,
    )

    if not allowed:
        auditor.log_authz(
            granted=False,
            user_id=context.user_id if context else None,
            permission="READ_ENTITY",
            resource_id=entity_id,
            error_message=error
        )
        return jsonify({"error": error}), 403

    # Perform operation
    import time
    start = time.time()

    entity = graph.get_entity(entity_id)

    duration_ms = (time.time() - start) * 1000

    # Log the read
    auditor.log_read(
        resource_type="entity",
        resource_id=entity_id,
        user_id=context.user_id,
        duration_ms=duration_ms
    )

    return jsonify(entity.to_dict())
```

### Secured Context Graph Wrapper

```python
class SecuredContextGraph:
    """Wrapper that adds auth/audit to ContextGraph."""

    def __init__(self, graph, auth_middleware, auditor):
        self.graph = graph
        self.auth = auth_middleware
        self.auditor = auditor

    def add_entity(self, entity, credentials):
        # Check authorization
        allowed, context, error = self.auth.check(
            credentials,
            Permission.CREATE_ENTITY
        )

        if not allowed:
            self.auditor.log_write(
                resource_type="entity",
                user_id=context.user_id if context else None,
                success=False,
                error_message=error
            )
            raise PermissionError(error)

        # Perform operation
        entity_id = self.graph.add_entity(entity)

        # Log success
        self.auditor.log_write(
            resource_type="entity",
            resource_id=entity_id,
            user_id=context.user_id
        )

        return entity_id

    def get_entity(self, entity_id, credentials):
        # Check authorization
        allowed, context, error = self.auth.check(
            credentials,
            Permission.READ_ENTITY
        )

        if not allowed:
            raise PermissionError(error)

        # Perform operation with audit
        with AuditContextManager(
            auditor=self.auditor,
            event_type=AuditEventType.ENTITY_READ,
            user_id=context.user_id,
            resource_id=entity_id
        ):
            return self.graph.get_entity(entity_id)
```

---

## Deployment Patterns

### Pattern 1: Development (No Auth)

```python
# Disable all security
from autoflow.context_graph.security import default_config
default_config.disable_validation()

# Use graph without auth
graph = ContextGraph(backend=InMemoryBackend())
```

### Pattern 2: Internal Service (API Keys)

```python
# Simple API key auth
auth = create_api_key_auth(api_keys)
auditor = Auditor(enabled=True)

# Check before each operation
allowed, context, _ = auth.check(api_key, Permission.READ_ENTITY)
if allowed:
    entity = graph.get_entity(entity_id)
    auditor.log_read("entity", entity_id, context.user_id)
```

### Pattern 3: Production (JWT + RBAC + Audit)

```python
# Full security stack
authenticator = JWTAuthenticator(secret=SECRET)
authorizer = CompositeAuthorizer([RBACAuthorizer(), ABACAuthorizer()])
auth = AuthMiddleware(authenticator, authorizer)

# Async audit logging
auditor = Auditor(
    backend=AsyncAuditBackend(
        backend=DatabaseAuditBackend(connection_string=DB_URL),
        queue_size=50000
    ),
    enabled=True
)

# Wrap graph
secured_graph = SecuredContextGraph(graph, auth, auditor)
```

---

## Best Practices

### Authentication
✅ **DO:**
- Use HTTPS for all credential transmission
- Rotate API keys regularly
- Use short-lived JWT tokens (15-60 minutes)
- Implement token refresh mechanisms

❌ **DON'T:**
- Store secrets in code
- Use long-lived tokens without expiration
- Log sensitive credentials

### Authorization
✅ **DO:**
- Use least privilege (default deny)
- Regularly audit permissions
- Document permission requirements
- Use roles for common patterns

❌ **DON'T:**
- Grant overly broad permissions
- Hardcode permission checks
- Skip authorization for "internal" calls

### Audit Logging
✅ **DO:**
- Log all auth failures
- Include request context (IP, user agent)
- Use structured logging (JSON)
- Protect audit logs (append-only, encryption)
- Regularly review logs for anomalies

❌ **DON'T:**
- Log sensitive data (passwords, tokens)
- Log only successful operations
- Store logs indefinitely without retention policy
- Allow audit log modification

---

## Troubleshooting

### "Invalid API key" error

**Cause:** API key doesn't match any configured key

**Fix:** Check:
1. Key prefix matches (default: `ctx_`)
2. Key exists in `api_keys` dict
3. Key hasn't been removed/rotated

### "Insufficient permissions" error

**Cause:** User doesn't have required permission

**Fix:** Check:
1. User's roles: `context.roles`
2. Role's permissions: `role_permissions`
3. Custom ABAC policies

### Audit logs not appearing

**Cause:** Auditor disabled or backend misconfigured

**Fix:** Check:
1. `auditor.enabled = True`
2. Backend file/database is writable
3. For async: queue not full

---

## Compliance Checklist

Use this checklist for compliance requirements:

### SOC 2 / ISO 27001
- ✅ All access authenticated
- ✅ Authorization checks on all operations
- ✅ Comprehensive audit logging
- ✅ Log retention (90+ days)
- ✅ Regular access reviews
- ✅ Change management for permissions

### GDPR
- ✅ Audit logs don't contain personal data (or are encrypted)
- ✅ Right to erasure (delete capability)
- ✅ Data access logging
- ✅ Data export capability

### HIPAA
- ✅ Audit trail for all PHI access
- ✅ Authentication for all users
- ✅ Role-based access controls
- ✅ Emergency access procedures
