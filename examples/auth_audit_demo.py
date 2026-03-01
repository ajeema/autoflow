"""
Authentication, Authorization, and Audit Logging Demo

Demonstrates how to secure the Context Graph with auth and track all operations.
"""

from autoflow.context_graph.core import Entity, Relationship, ContextGraph, TraversalPattern
from autoflow.context_graph.backends import InMemoryBackend
from autoflow.context_graph.auth import (
    AuthMiddleware,
    APIKeyAuthenticator,
    RBACAuthorizer,
    Permission,
    AuthContext,
    create_api_key_auth,
)
from autoflow.context_graph.audit import (
    Auditor,
    FileAuditBackend,
    AuditEventType,
    AuditContextManager,
)


def demo_basic_auth():
    """Demonstrate basic authentication."""
    print("=== Authentication Demo ===\n")

    # Setup API key authentication
    api_keys = {
        "ctx_admin_abc123": {
            "user_id": "admin_001",
            "username": "alice",
            "roles": {"admin"},
            "permissions": {p for p in Permission},  # All permissions
            "attributes": {"tier": "premium", "department": "engineering"},
        },
        "ctx_analyst_xyz789": {
            "user_id": "analyst_001",
            "username": "bob",
            "roles": {"analyst"},
            "permissions": {
                Permission.READ_ENTITY,
                Permission.TRAVERSE,
                Permission.SEARCH,
                Permission.QUERY,
            },
            "attributes": {"tier": "basic", "department": "marketing"},
        },
    }

    auth_middleware = create_api_key_auth(api_keys)

    # Test 1: Valid admin key
    print("Test 1: Authenticating with admin API key")
    allowed, context, error = auth_middleware.check(
        credentials="ctx_admin_abc123",
        permission=Permission.DELETE_ENTITY,
    )
    print(f"  Result: {'✅ ALLOWED' if allowed else '❌ DENIED'}")
    print(f"  User: {context.username if context else 'N/A'}")
    print(f"  Roles: {context.roles if context else 'N/A'}")
    if error:
        print(f"  Error: {error}")

    # Test 2: Valid analyst key (for read)
    print("\nTest 2: Analyst attempting READ operation")
    allowed, context, error = auth_middleware.check(
        credentials="ctx_analyst_xyz789",
        permission=Permission.READ_ENTITY,
    )
    print(f"  Result: {'✅ ALLOWED' if allowed else '❌ DENIED'}")
    print(f"  User: {context.username if context else 'N/A'}")

    # Test 3: Analyst trying to delete (should fail)
    print("\nTest 3: Analyst attempting DELETE operation (should fail)")
    allowed, context, error = auth_middleware.check(
        credentials="ctx_analyst_xyz789",
        permission=Permission.DELETE_ENTITY,
    )
    print(f"  Result: {'✅ ALLOWED' if allowed else '❌ DENIED'}")
    print(f"  Reason: {error}")

    # Test 4: Invalid API key
    print("\nTest 4: Invalid API key")
    allowed, context, error = auth_middleware.check(
        credentials="invalid_key",
        permission=Permission.READ_ENTITY,
    )
    print(f"  Result: {'✅ ALLOWED' if allowed else '❌ DENIED'}")
    print(f"  Error: {error}")


def demo_custom_roles():
    """Demonstrate custom role definitions."""
    print("\n\n=== Custom Roles Demo ===\n")

    # Define custom roles
    custom_roles = {
        "data_scientist": {
            Permission.READ_ENTITY,
            Permission.TRAVERSE,
            Permission.SEARCH,
            Permission.QUERY,
            Permission.EXPORT_DATA,  # Custom permission
        },
        "content_manager": {
            Permission.READ_ENTITY,
            Permission.CREATE_ENTITY,
            Permission.UPDATE_ENTITY,
            Permission.DELETE_ENTITY,
        },
    }

    api_keys = {
        "ctx_ds_key123": {
            "user_id": "ds_001",
            "username": "carol",
            "roles": {"data_scientist"},
            "permissions": custom_roles["data_scientist"],
            "attributes": {"department": "data_science"},
        },
    }

    auth_middleware = create_api_key_auth(api_keys, roles=custom_roles)

    print("Test: Data scientist attempting export")
    allowed, context, error = auth_middleware.check(
        credentials="ctx_ds_key123",
        permission=Permission.EXPORT_DATA,
    )
    print(f"  Result: {'✅ ALLOWED' if allowed else '❌ DENIED'}")
    print(f"  User: {context.username if context else 'N/A'}")
    print(f"  Has EXPORT_DATA permission: {context.has_permission(Permission.EXPORT_DATA) if context else False}")


def demo_attribute_based_auth():
    """Demonstrate attribute-based access control."""
    print("\n\n=== Attribute-Based Auth Demo ===\n")

    from autoflow.context_graph.auth import ABACAuthorizer, CompositeAuthorizer

    # Setup ABAC with custom policy
    abac = ABACAuthorizer()

    # Policy: Only premium tier can delete entities
    abac.add_policy(
        lambda ctx, perm, res: (
            perm == Permission.DELETE_ENTITY and
            ctx.attributes.get("tier") == "premium"
        )
    )

    # Policy: Users can only read entities from their department
    abac.add_policy(
        lambda ctx, perm, res: (
            perm == Permission.READ_ENTITY and
            isinstance(res, dict) and
            res.get("department") == ctx.attributes.get("department")
        )
    )

    # Combine with RBAC
    rbac = RBACAuthorizer()
    composite = CompositeAuthorizer([rbac, abac])

    authenticator = APIKeyAuthenticator({
        "ctx_premium_123": {
            "user_id": "user_001",
            "roles": {"viewer"},  # Limited role
            "permissions": {Permission.READ_ENTITY},
            "attributes": {"tier": "premium", "department": "marketing"},
        },
    })

    auth_middleware = AuthMiddleware(authenticator, composite)

    # Test: Premium user with viewer role can delete (via ABAC policy)
    print("Test: Premium viewer attempting DELETE")
    allowed, context, error = auth_middleware.check(
        credentials="ctx_premium_123",
        permission=Permission.DELETE_ENTITY,
    )
    print(f"  Result: {'✅ ALLOWED' if allowed else '❌ DENIED'} (via ABAC tier policy)")
    print(f"  User tier: {context.attributes.get('tier') if context else 'N/A'}")

    # Test: Same user reading from their department
    print("\nTest: User reading from their department")
    allowed, context, error = auth_middleware.check(
        credentials="ctx_premium_123",
        permission=Permission.READ_ENTITY,
        resource={"department": "marketing"},  # Resource metadata
    )
    print(f"  Result: {'✅ ALLOWED' if allowed else '❌ DENIED'}")


def demo_audit_logging():
    """Demonstrate audit logging."""
    print("\n\n=== Audit Logging Demo ===\n")

    # Setup auditor with file backend
    auditor = Auditor(
        backend=FileAuditBackend(filepath="demo_audit.log"),
        enabled=True,
    )

    # Log authentication event
    print("Logging authentication events...")
    auditor.log_auth(success=True, user_id="user_001", username="alice")
    auditor.log_auth(success=False, user_id=None, error_message="Invalid API key")

    # Log read operation
    print("\nLogging read operation...")
    auditor.log_read(
        resource_type="entity",
        resource_id="brand:nike",
        user_id="user_001",
        duration_ms=15.3,
    )

    # Log write operation
    print("\nLogging write operation...")
    auditor.log_write(
        resource_type="entity",
        resource_id="brand:adidas",
        user_id="user_002",
        metadata={"properties": {"name": "Adidas", "vertical": "Apparel"}},
    )

    # Log security event
    print("\nLogging security event...")
    auditor.log_security_event(
        event_type=AuditEventType.INJECTION_ATTEMPT,
        details="SQL injection attempt blocked",
        user_id="unknown",
        metadata={"ip_address": "192.168.1.100", "input": "'; DROP TABLE--"},
    )

    # Demonstrate context manager
    print("\nUsing context manager for automatic timing...")
    with AuditContextManager(
        auditor=auditor,
        event_type=AuditEventType.GRAPH_TRAVERSE,
        operation="traverse",
        user_id="user_001",
        resource_id="brand:nike",
    ) as ctx:
        # Simulate work
        import time
        time.sleep(0.01)

    # Read the audit log
    print("\n--- Audit Log Contents ---")
    try:
        with open("demo_audit.log", "r") as f:
            for line in f:
                if line.strip():
                    import json
                    event = json.loads(line)
                    print(f"\n  Event: {event['event_type']}")
                    print(f"  User: {event.get('user_id', 'N/A')}")
                    print(f"  Operation: {event.get('operation', 'N/A')}")
                    print(f"  Success: {event.get('success', True)}")
                    if event.get('duration_ms'):
                        print(f"  Duration: {event['duration_ms']:.2f}ms")
    except FileNotFoundError:
        print("  (No log file created)")

    auditor.close()


def demo_secured_context_graph():
    """Demonstrate a fully secured Context Graph."""
    print("\n\n=== Secured Context Graph Demo ===\n")

    # Setup auth and audit
    api_keys = {
        "ctx_editor_123": {
            "user_id": "editor_001",
            "username": "dave",
            "roles": {"editor"},
            "permissions": {
                Permission.READ_ENTITY,
                Permission.CREATE_ENTITY,
                Permission.TRAVERSE,
            },
            "attributes": {"department": "content"},
        },
    }

    auth = create_api_key_auth(api_keys)
    auditor = Auditor(enabled=True)  # In production, use proper backend

    # Initialize graph
    graph = ContextGraph(backend=InMemoryBackend())

    # Simulate creating an entity with auth check
    api_key = "ctx_editor_123"

    # Check permissions
    allowed, context, error = auth.check(
        credentials=api_key,
        permission=Permission.CREATE_ENTITY,
    )

    print(f"Creating entity as {context.username if context else 'anonymous'}...")
    print(f"  Authenticated: {allowed}")
    print(f"  User ID: {context.user_id if context else 'N/A'}")

    if allowed:
        # Create entity
        entity = Entity(
            type="brand",
            properties={"name": "Nike", "vertical": "Apparel"},
        )
        entity_id = graph.add_entity(entity)

        # Log the operation
        auditor.log_write(
            resource_type="entity",
            resource_id=entity_id,
            user_id=context.user_id,
            metadata={"entity_type": "brand", "name": "Nike"},
        )

        print(f"  ✅ Entity created: {entity_id}")
    else:
        print(f"  ❌ Operation denied: {error}")

    # Try unauthorized operation
    print("\nAttempting unauthorized DELETE...")
    allowed, context, error = auth.check(
        credentials=api_key,
        permission=Permission.DELETE_ENTITY,
    )

    print(f"  Result: {'✅ ALLOWED' if allowed else '❌ DENIED'}")
    if not allowed:
        # Log the denied attempt
        auditor.log_authz(
            granted=False,
            user_id=context.user_id if context else None,
            permission="DELETE_ENTITY",
            error_message="Insufficient permissions",
        )

    auditor.close()


def main():
    """Run all demos."""
    print("Context Graph - Auth & Audit Demo\n")
    print("=" * 60)

    demo_basic_auth()
    demo_custom_roles()
    demo_attribute_based_auth()
    demo_audit_logging()
    demo_secured_context_graph()

    print("\n" + "=" * 60)
    print("\nKey Takeaways:")
    print("  1. Authentication: API keys, JWT, or custom")
    print("  2. Authorization: RBAC, ABAC, or combined")
    print("  3. Audit: All operations logged with context")
    print("  4. Flexible: Can be disabled for development")
    print("\nIntegration Example:")
    print("  ```python")
    print("  auth = create_api_key_auth(api_keys)")
    print("  auditor = Auditor(enabled=True)")
    print("  ")
    print("  # Check before operation")
    print("  allowed, ctx, err = auth.check(key, Permission.READ_ENTITY)")
    print("  if allowed:")
    print("      entity = graph.get_entity(entity_id)")
    print("      auditor.log_read('entity', entity_id, ctx.user_id)")
    print("  ```")


if __name__ == "__main__":
    main()
