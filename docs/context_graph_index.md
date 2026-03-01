# Context Graph Framework - Documentation Index

Complete documentation for the Context Graph Framework.

## Quick Links

| Want to... | Read This |
|-------------|------------|
| Get started quickly | [Context Graph Guide](context_graph.md) |
| Look up an API | [API Reference](api_reference.md) |
| Secure your deployment | [Auth & Audit Guide](auth_audit_guide.md) |
| See security features | [Security Module](security.md) |
| Understand the implementation | [This file](#implementation-details) |

---

## Getting Started

### 1. Context Graph Guide
**📄 [context_graph.md](context_graph.md)**

Start here for a complete introduction to the Context Graph Framework.

**Covers:**
- What is a context graph and why you need one
- Quick start examples
- Core concepts (entities, relationships, traversals)
- Backend options (Neo4j, InMemory)
- LLM integration patterns
- Example use cases
- When to use vector DB vs context graphs

**Time:** 15 min read

---

## API Documentation

### 2. API Reference
**📄 [api_reference.md](api_reference.md)**

Complete API documentation for all public APIs.

**Covers:**
- Core classes (Entity, Relationship, ContextGraph, etc.)
- Backends (InMemoryBackend, Neo4jBackend)
- LLM integration (GraphToContextAssembler, CypherQueryBuilder)
- Security (SecurityConfig, Validator, Sanitizer)
- Authentication (AuthMiddleware, APIKeyAuthenticator, JWTAuthenticator)
- Authorization (RBACAuthorizer, ABACAuthorizer)
- Audit logging (Auditor, AuditEvent, AuditContextManager)
- Domain modules (BrandDomain, CampaignDomain, PublisherDomain)
- Enums and type aliases

**Each API includes:**
- Method signatures
- Parameters
- Return types
- Raises
- Usage examples
- Best practices

**Time:** Reference - read as needed

---

## Security & Compliance

### 3. Auth & Audit Guide
**📄 [auth_audit_guide.md](auth_audit_guide.md)**

Complete guide for securing your context graph deployment.

**Covers:**
- Authentication setup (API keys, JWT)
- Authorization models (RBAC, ABAC, composite)
- Audit logging configuration
- Production deployment patterns
- Compliance checklists (SOC 2, GDPR, HIPAA)
- Troubleshooting security issues
- Best practices

**Deployment Patterns:**
- Development (no auth)
- Internal service (API keys)
- Production (JWT + RBAC + audit)

**Time:** 30 min read

---

## Implementation Details

### Security Module

**Files:**
- `src/autoflow/context_graph/security.py` (500+ lines)
- Integrated into: `core.py`, `backends.py`, `llm.py`

**Features:**
- Entity/relationship type validation (allowlist)
- Property key validation (regex)
- Value sanitization (control chars, null bytes)
- LLM prompt injection protection
- Resource limits (max_hops, max_properties, etc.)
- Configurable and can be disabled

**Key Classes:**
- `SecurityConfig` - Centralized configuration
- `Validator` - Input validation
- `Sanitizer` - Input sanitization

**Example:**
```python
from autoflow.context_graph.security import SecurityConfig

config = SecurityConfig(enable_validation=True)
config.allow_entity_type("flight")  # Add custom type
```

---

### Authentication Module

**File:**
- `src/autoflow/context_graph/auth.py` (600+ lines)

**Features:**
- API Key authentication
- JWT authentication
- Pluggable authenticators
- AuthContext with roles, permissions, attributes
- Token expiration handling
- AuthMiddleware for easy integration

**Key Classes:**
- `AuthContext` - Authenticated user context
- `AuthMiddleware` - Combines auth + authz
- `APIKeyAuthenticator` - Simple API key auth
- `JWTAuthenticator` - JWT token auth

**Example:**
```python
from autoflow.context_graph.auth import create_api_key_auth, Permission

auth = create_api_key_auth(api_keys)
allowed, context, error = auth.check(api_key, Permission.READ_ENTITY)
```

---

### Authorization Module

**File:**
- `src/autoflow/context_graph/auth.py` (included in auth.py)

**Features:**
- RBAC (Role-Based Access Control)
- ABAC (Attribute-Based Access Control)
- Composite authorization (combine both)
- 25+ fine-grained permissions
- Resource-level authorization

**Key Classes:**
- `RBACAuthorizer` - Role-based authorization
- `ABACAuthorizer` - Attribute-based with policies
- `CompositeAuthorizer` - Combine multiple authorizers

**Example:**
```python
from autoflow.context_graph.auth import RBACAuthorizer

authorizer = RBACAuthorizer()
if authorizer.can(context, Permission.READ_ENTITY):
    # Allow
    pass
```

---

### Audit Logging Module

**File:**
- `src/autoflow/context_graph/audit.py` (600+ lines)

**Features:**
- File backend (with rotation)
- Database backend (batch writes)
- Async backend (non-blocking)
- 20+ event types tracked
- Automatic timing with context managers
- JSON structured logs

**Key Classes:**
- `Auditor` - Main audit interface
- `AuditEvent` - Audit event record
- `AuditContextManager` - Automatic timing
- `FileAuditBackend` - File-based logging
- `DatabaseAuditBackend` - Database logging
- `AsyncAuditBackend` - Non-blocking async

**Example:**
```python
from autoflow.context_graph.audit import Auditor

auditor = Auditor(enabled=True)
auditor.log_read("entity", "brand:nike", user_id="user_001")
```

---

## Examples

### Security Demo
**📄 [examples/security_demo.py](../examples/security_demo.py)**

Demonstrates all security features:
- Input validation
- Custom entity types
- LLM input sanitization
- Disabling validation
- Resource limits

**Run:**
```bash
python examples/security_demo.py
```

---

### Auth & Audit Demo
**📄 [examples/auth_audit_demo.py](../examples/auth_audit_demo.py)**

Complete demonstration of:
- Authentication (API keys, custom roles)
- Authorization (RBAC, ABAC)
- Audit logging (all event types)
- Secured Context Graph

**Run:**
```bash
python examples/auth_audit_demo.py
```

---

### Context Graph Demo
**📄 [examples/context_graph_demo.py](../examples/context_graph_demo.py)**

Basic context graph demonstration:
- Creating entities and relationships
- Multi-hop traversals
- LLM context assembly
- Property search
- Neighbor queries

**Run:**
```bash
python examples/context_graph_demo.py
```

---

## Reference

### All Modules

| Module | File | Purpose |
|--------|------|---------|
| Core | `src/autoflow/context_graph/core.py` | Entity, Relationship, ContextGraph |
| Backends | `src/autoflow/context_graph/backends.py` | InMemoryBackend, Neo4jBackend |
| LLM | `src/autoflow/context_graph/llm.py` | LLM integration utilities |
| Security | `src/autoflow/context_graph/security.py` | Validation, sanitization, limits |
| Auth | `src/autoflow/context_graph/auth.py` | Authentication, authorization |
| Audit | `src/autoflow/context_graph/audit.py` | Audit logging |
| Brand Domain | `src/autoflow/context_graph/domains/brand.py` | Brand/company intelligence |
| Campaign Domain | `src/autoflow/context_graph/domains/campaign.py` | Campaign/creative intelligence |
| Publisher Domain | `src/autoflow/context_graph/domains/publisher.py` | Publisher/inventory intelligence |

### Installation

**Basic:**
```bash
pip install autoflow
```

**With Neo4j:**
```bash
pip install autoflow[neo4j]
```

**All optional dependencies:**
```bash
pip install autoflow[all]
```

**Development:**
```bash
pip install -e ".[dev]"
```

---

## Changelog

See [CHANGELOG.md](../CHANGELOG.md) for version history and changes.

---

## Support

- **Issues:** [GitHub Issues](https://github.com/your-org/autoflow/issues)
- **Documentation:** This file and linked guides
- **Examples:** See `examples/` directory

---

## License

MIT License - See [LICENSE](../LICENSE) for details.
