# Apply API

## Overview

The **Apply** module is responsible for safely applying evaluated proposals to your system. It combines:

- **Policy** - What changes are allowed (paths, risk levels)
- **Backend** - How to apply changes (git patch, PR, direct edit)

---

## Core Concepts

### ProposalApplier

```python
class ProposalApplier:
    def __init__(self, policy: ApplyPolicy, backend: object) -> None:
        self.policy = policy
        self.backend = backend

    def apply(self, proposal: ChangeProposal) -> None:
        self.policy.assert_allowed(proposal)  # May raise PolicyViolation
        self.backend.apply(proposal)
```

**Flow:**

```
Proposal → Policy Check → Backend Apply → System Updated
```

---

## Policy

### ApplyPolicy

```python
class ApplyPolicy:
    def __init__(
        self,
        allowed_paths_prefixes: tuple[str, ...],
        max_risk: RiskLevel = RiskLevel.LOW,
    ) -> None:
        self.allowed_paths_prefixes = allowed_paths_prefixes
        self.max_risk = max_risk
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `allowed_paths_prefixes` | `tuple[str, ...]` | Path prefixes that are allowed to be modified |
| `max_risk` | `RiskLevel` | Maximum risk level allowed (default: LOW) |

**Method:**

```python
def assert_allowed(self, proposal: ChangeProposal) -> None:
    """
    Check if proposal is allowed by policy.

    Raises:
        PolicyViolation: If proposal violates policy
    """
```

### Policy Violations

```python
from autoflow.errors import PolicyViolation

try:
    policy.assert_allowed(proposal)
except PolicyViolation as e:
    print(f"Proposal rejected: {e}")
```

---

## Basic Usage

### Example 1: Basic Policy

```python
from autoflow.apply.policy import ApplyPolicy
from autoflow.apply.applier import ProposalApplier
from autoflow.apply.git_backend import GitApplyBackend
from autoflow.types import RiskLevel, ChangeProposal

# Define policy
policy = ApplyPolicy(
    allowed_paths_prefixes=("config/", "prompts/"),
    max_risk=RiskLevel.LOW,
)

# Define backend
backend = GitApplyBackend(repo_path=Path("."))

# Create applier
applier = ProposalApplier(policy=policy, backend=backend)

# Apply proposal
proposal = ChangeProposal(
    proposal_id="prop_001",
    kind=ProposalKind.CONFIG_EDIT,
    title="Increase timeout",
    description="Fix timeout issues",
    risk=RiskLevel.LOW,
    target_paths=("config/workflows.yaml",),
    payload={"timeout_ms": 10000},
)

try:
    applier.apply(proposal)
    print("Proposal applied successfully")
except PolicyViolation as e:
    print(f"Proposal rejected: {e}")
```

### Example 2: Policy with Higher Risk

```python
# Allow MEDIUM risk for trusted ops team
policy = ApplyPolicy(
    allowed_paths_prefixes=("config/", "src/"),
    max_risk=RiskLevel.MEDIUM,
)

applier = ProposalApplier(
    policy=policy,
    backend=GitApplyBackend(repo_path=Path(".")),
)

# This will pass
medium_risk_proposal = ChangeProposal(
    proposal_id="prop_002",
    kind=ProposalKind.CONFIG_EDIT,
    title="Add new feature flag",
    description="Enable feature beta",
    risk=RiskLevel.MEDIUM,
    target_paths=("config/features.yaml",),
    payload={"feature_beta": True},
)

applier.apply(medium_risk_proposal)  # OK

# This will fail
high_risk_proposal = ChangeProposal(
    proposal_id="prop_003",
    kind=ProposalKind.CONFIG_EDIT,
    title="Database migration",
    description="Migrate to new schema",
    risk=RiskLevel.HIGH,
    target_paths=("config/database.yaml",),
    payload={},
)

applier.apply(high_risk_proposal)  # Raises PolicyViolation
```

### Example 3: Multiple Path Prefixes

```python
# Allow changes to multiple directories
policy = ApplyPolicy(
    allowed_paths_prefixes=(
        "config/workflows/",
        "config/prompts/",
        "config/models/",
    ),
    max_risk=RiskLevel.LOW,
)

# These proposals will pass
applier.apply(ChangeProposal(
    ...,
    target_paths=("config/workflows/api.yaml",),
))

applier.apply(ChangeProposal(
    ...,
    target_paths=("config/prompts/qa.txt",),
))

# This proposal will fail
applier.apply(ChangeProposal(
    ...,
    target_paths=("config/secrets.yaml",),  # Not in allowed prefixes
))
```

---

## Backends

### GitApplyBackend

Applies proposals using git (creates patches/commits).

```python
from autoflow.apply.git_backend import GitApplyBackend
from pathlib import Path

backend = GitApplyBackend(repo_path=Path("/path/to/repo"))
```

**Current Implementation:**
- Stub implementation that logs proposals
- Production version would:
  - Apply patches safely
  - Create git commits
  - Push to remote
  - Optionally create pull requests

**Usage:**

```python
backend = GitApplyBackend(repo_path=Path("."))

proposal = ChangeProposal(
    proposal_id="prop_001",
    kind=ProposalKind.TEXT_PATCH,
    title="Fix bug in parser",
    description="Add error handling",
    risk=RiskLevel.LOW,
    target_paths=("src/parser.py",),
    payload={
        "patch": """
--- a/src/parser.py
+++ b/src/parser.py
@@ -15,6 +15,10 @@
 def parse(data):
+    if not data:
+        return None
     return json.loads(data)
""",
        "format": "unified",
    },
)

backend.apply(proposal)
# Output: [APPLY] Fix bug in parser
```

---

## Creating Custom Backends

### Pattern 1: Filesystem Backend

```python
from pathlib import Path
from autoflow.types import ChangeProposal, ProposalKind

class FilesystemApplyBackend:
    """Apply proposals directly to filesystem."""

    def __init__(self, root_path: Path):
        self.root_path = root_path

    def apply(self, proposal: ChangeProposal) -> None:
        if proposal.kind == ProposalKind.CONFIG_EDIT:
            self._apply_config_edit(proposal)
        elif proposal.kind == ProposalKind.TEXT_PATCH:
            self._apply_text_patch(proposal)
        else:
            raise ValueError(f"Unsupported kind: {proposal.kind}")

    def _apply_config_edit(self, proposal: ChangeProposal) -> None:
        import yaml

        for path in proposal.target_paths:
            full_path = self.root_path / path

            # Load current config
            with open(full_path) as f:
                config = yaml.safe_load(f)

            # Apply change
            payload = proposal.payload
            if "op" in payload:
                if payload["op"] == "set":
                    # Set value at path
                    keys = payload["path"].split(".")
                    value = payload["value"]

                    # Navigate to parent
                    current = config
                    for key in keys[:-1]:
                        current = current[key]

                    # Set value
                    current[keys[-1]] = value

            # Write back
            with open(full_path, "w") as f:
                yaml.dump(config, f)

            print(f"[APPLY] Updated {path}")

    def _apply_text_patch(self, proposal: ChangeProposal) -> None:
        import subprocess

        patch_content = proposal.payload.get("patch", "")

        for path in proposal.target_paths:
            full_path = self.root_path / path

            # Apply patch
            subprocess.run(
                ["patch", str(full_path)],
                input=patch_content,
                text=True,
                check=True,
            )

            print(f"[APPLY] Patched {path}")
```

### Pattern 2: Pull Request Backend

```python
import requests
from autoflow.types import ChangeProposal

class PullRequestBackend:
    """Apply proposals by creating GitHub pull requests."""

    def __init__(self, repo: str, token: str, base_branch: str = "main"):
        self.repo = repo
        self.token = token
        self.base_branch = base_branch
        self.api_url = f"https://api.github.com/repos/{repo}"

    def apply(self, proposal: ChangeProposal) -> None:
        # Create branch
        branch_name = f"autoflow/{proposal.proposal_id}"
        self._create_branch(branch_name)

        # Apply changes
        if proposal.kind == ProposalKind.TEXT_PATCH:
            self._apply_patch(proposal, branch_name)
        elif proposal.kind == ProposalKind.CONFIG_EDIT:
            self._apply_config_edit(proposal, branch_name)

        # Create PR
        pr_url = self._create_pull_request(
            branch=branch_name,
            title=f"[AutoFlow] {proposal.title}",
            body=f"{proposal.description}\n\n**Risk:** {proposal.risk}",
        )

        print(f"[APPLY] Created PR: {pr_url}")

    def _create_branch(self, branch_name: str) -> None:
        requests.post(
            f"{self.api_url}/git/refs",
            headers={"Authorization": f"token {self.token}"},
            json={
                "ref": f"refs/heads/{branch_name}",
                "sha": self._get_head_sha(),
            },
        )

    def _apply_patch(self, proposal: ChangeProposal, branch: str) -> None:
        # Apply patch to files in branch
        for path in proposal.target_paths:
            patch_content = proposal.payload.get("patch", "")

            # Get current file content
            current_content = self._get_file_content(path, branch)

            # Apply patch
            new_content = self._apply_unified_patch(current_content, patch_content)

            # Commit to branch
            self._commit_file(path, new_content, branch, proposal.title)

    def _create_pull_request(self, branch: str, title: str, body: str) -> str:
        response = requests.post(
            f"{self.api_url}/pulls",
            headers={"Authorization": f"token {self.token}"},
            json={
                "title": title,
                "body": body,
                "head": branch,
                "base": self.base_branch,
            },
        )
        response.raise_for_status()
        return response.json()["html_url"]
```

### Pattern 3: Kubernetes ConfigMap Backend

```python
from kubernetes import client, config

class KubernetesConfigMapBackend:
    """Apply proposals to Kubernetes ConfigMaps."""

    def __init__(self, namespace: str = "default"):
        config.load_kube_config()
        self.api = client.CoreV1Api()
        self.namespace = namespace

    def apply(self, proposal: ChangeProposal) -> None:
        if proposal.kind != ProposalKind.CONFIG_EDIT:
            raise ValueError("Only CONFIG_EDIT supported")

        for path in proposal.target_paths:
            # Parse path: "configmaps/my-config"
            parts = path.split("/")
            if len(parts) != 2 or parts[0] != "configmaps":
                continue

            configmap_name = parts[1]

            # Get current ConfigMap
            configmap = self.api.read_namespaced_config_map(
                name=configmap_name,
                namespace=self.namespace,
            )

            # Apply change
            payload = proposal.payload
            if payload["op"] == "set":
                key = payload["path"]
                value = payload["value"]

                # Update ConfigMap data
                configmap.data[key] = str(value)

                # Apply update
                self.api.patch_namespaced_config_map(
                    name=configmap_name,
                    namespace=self.namespace,
                    body=configmap,
                )

                print(f"[APPLY] Updated ConfigMap {configmap_name}")
```

### Pattern 4: Database Migration Backend

```python
import psycopg
from autoflow.types import ChangeProposal

class DatabaseMigrationBackend:
    """Apply schema proposals as database migrations."""

    def __init__(self, connection_string: str):
        self.conn_string = connection_string

    def apply(self, proposal: ChangeProposal) -> None:
        if proposal.kind != ProposalKind.CONFIG_EDIT:
            raise ValueError("Only CONFIG_EDIT supported")

        with psycopg.connect(self.conn_string) as conn:
            with conn.cursor() as cur:
                # Generate migration SQL from proposal
                migration_sql = self._generate_migration(proposal)

                # Run migration
                cur.execute(migration_sql)

                # Log migration
                cur.execute("""
                    INSERT INTO autoflow_migrations (proposal_id, applied_at)
                    VALUES (%s, NOW())
                """, (proposal.proposal_id,))

                conn.commit()

                print(f"[APPLY] Applied migration {proposal.proposal_id}")

    def _generate_migration(self, proposal: ChangeProposal) -> str:
        """Generate SQL from proposal payload."""

        if proposal.payload.get("op") == "add_column":
            return f"""
                ALTER TABLE {proposal.payload['table']}
                ADD COLUMN {proposal.payload['column']} {proposal.payload['type']}
            """

        elif proposal.payload.get("op") == "create_index":
            return f"""
                CREATE INDEX IF NOT EXISTS {proposal.payload['index_name']}
                ON {proposal.payload['table']} ({proposal.payload['columns']})
            """

        else:
            raise ValueError(f"Unknown migration op: {proposal.payload}")
```

---

## Apply Best Practices

### DO ✅

**1. Use Strict Policies in Production**

```python
# Good - very restrictive
policy = ApplyPolicy(
    allowed_paths_prefixes=("config/workflows/",),
    max_risk=RiskLevel.LOW,
)
```

**2. Validate Before Apply**

```python
# Always evaluate first
result = evaluator.evaluate(proposal)

if result.passed:
    applier.apply(proposal)
else:
    log_failure(result)
```

**3. Log All Applications**

```python
class LoggingApplyBackend:
    def __init__(self, backend: object):
        self.backend = backend

    def apply(self, proposal: ChangeProposal) -> None:
        logger.info(f"Applying proposal: {proposal.proposal_id}")
        logger.info(f"Title: {proposal.title}")
        logger.info(f"Risk: {proposal.risk}")

        try:
            self.backend.apply(proposal)
            logger.info(f"Successfully applied {proposal.proposal_id}")
        except Exception as e:
            logger.error(f"Failed to apply {proposal.proposal_id}: {e}")
            raise
```

**4. Use Git for Version Control**

```python
# Good - all changes are tracked
backend = GitApplyBackend(repo_path=Path("."))
applier = ProposalApplier(
    policy=policy,
    backend=backend,
)
```

### DON'T ❌

**1. Don't Allow Root Paths**

```python
# Avoid - too dangerous
policy = ApplyPolicy(
    allowed_paths_prefixes=("", "*", "."),
    max_risk=RiskLevel.HIGH,
)

# Good - specific paths
policy = ApplyPolicy(
    allowed_paths_prefixes=("config/workflows/",),
    max_risk=RiskLevel.LOW,
)
```

**2. Don't Apply Without Policy Check**

```python
# Avoid - bypasses policy
backend.apply(proposal)

# Good - policy enforces safety
applier = ProposalApplier(policy=policy, backend=backend)
applier.apply(proposal)
```

**3. Don't Apply High-Risk Changes Automatically**

```python
# Avoid - risky
policy = ApplyPolicy(
    allowed_paths_prefixes=("src/",),
    max_risk=RiskLevel.HIGH,
)

# Good - require manual approval for HIGH risk
policy = ApplyPolicy(
    allowed_paths_prefixes=("config/",),
    max_risk=RiskLevel.LOW,
)
```

**4. Don't Apply Without Backup**

```python
class SafeFilesystemBackend:
    def apply(self, proposal: ChangeProposal) -> None:
        for path in proposal.target_paths:
            # Create backup
            backup_path = f"{path}.backup"
            shutil.copy(path, backup_path)

            try:
                # Apply change
                self._apply_to_file(proposal, path)
            except Exception as e:
                # Restore from backup
                shutil.copy(backup_path, path)
                raise
```

---

## Apply Patterns

### Pattern 1: Dry-Run Mode

```python
class DryRunBackend:
    """Backend that only logs changes without applying."""

    def apply(self, proposal: ChangeProposal) -> None:
        print(f"[DRY-RUN] Would apply: {proposal.title}")
        print(f"  Target paths: {proposal.target_paths}")
        print(f"  Payload: {proposal.payload}")

# Usage
applier = ProposalApplier(
    policy=policy,
    backend=DryRunBackend(),
)
```

### Pattern 2: Approval Backend

```python
class ApprovalBackend:
    """Backend that requires manual approval."""

    def __init__(self, actual_backend: object, approver: str):
        self.backend = actual_backend
        self.approver = approver

    def apply(self, proposal: ChangeProposal) -> None:
        # Send approval request
        self._send_approval_request(proposal)

        # Wait for approval
        approved = self._wait_for_approval(proposal.proposal_id)

        if approved:
            self.backend.apply(proposal)
        else:
            raise Exception(f"Proposal {proposal.proposal_id} was not approved")
```

### Pattern 3: Rollback Backend

```python
class RollbackBackend:
    """Backend that can rollback changes."""

    def __init__(self, backend: object):
        self.backend = backend
        self.applied_proposals = []

    def apply(self, proposal: ChangeProposal) -> None:
        # Store current state for rollback
        self._snapshot_state(proposal)

        # Apply proposal
        self.backend.apply(proposal)

        # Track for rollback
        self.applied_proposals.append(proposal)

    def rollback(self, proposal_id: str) -> None:
        """Rollback a specific proposal."""
        proposal = next(
            p for p in self.applied_proposals
            if p.proposal_id == proposal_id
        )

        # Create inverse proposal
        inverse = self._create_inverse_proposal(proposal)

        # Apply inverse
        self.backend.apply(inverse)

        self.applied_proposals.remove(proposal)
```

---

## API Reference

### ProposalApplier

```python
class ProposalApplier:
    def __init__(self, policy: ApplyPolicy, backend: object) -> None:
        """
        Initialize applier with policy and backend.

        Args:
            policy: Policy to enforce before applying
            backend: Backend that applies proposals
        """

    def apply(self, proposal: ChangeProposal) -> None:
        """
        Apply a proposal if it passes policy check.

        Args:
            proposal: Proposal to apply

        Raises:
            PolicyViolation: If proposal violates policy
        """
```

### ApplyPolicy

```python
class ApplyPolicy:
    def __init__(
        self,
        allowed_paths_prefixes: tuple[str, ...],
        max_risk: RiskLevel = RiskLevel.LOW,
    ) -> None:
        """
        Initialize policy.

        Args:
            allowed_paths_prefixes: Path prefixes that can be modified
            max_risk: Maximum risk level allowed
        """

    def assert_allowed(self, proposal: ChangeProposal) -> None:
        """
        Check if proposal is allowed by policy.

        Args:
            proposal: Proposal to check

        Raises:
            PolicyViolation: If proposal violates policy
        """
```

### GitApplyBackend

```python
class GitApplyBackend:
    def __init__(self, repo_path: Path) -> None:
        """
        Initialize git backend.

        Args:
            repo_path: Path to git repository
        """

    def apply(self, proposal: ChangeProposal) -> None:
        """
        Apply proposal to git repository.

        Args:
            proposal: Proposal to apply
        """
```

---

## See Also

- [Proposals API](proposals.md) - Proposal structure
- [Evaluation API](evaluation.md) - How to evaluate before applying
- [Decision Graph API](decision_graph.md) - How proposals are generated
- [Examples](examples.md) - Complete apply examples
