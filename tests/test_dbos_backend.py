"""Tests for DBOS-backed apply backend."""

from pathlib import Path
from typing import Any
import pytest

from autoflow.apply.dbos_backend import (
    DBOSBackend,
    DBOSBackendUnavailable,
    DBOS_AVAILABLE,
    ApplyResult,
    _is_dbos_installed,
)
from autoflow.types import ChangeProposal, ProposalKind, RiskLevel
from autoflow.errors import ApplyError


class TestApplyResult:
    """Tests for ApplyResult model."""

    def test_init_success(self):
        """Test creating a successful result."""
        result = ApplyResult(success=True, reference="abc123")

        assert result.success is True
        assert result.reference == "abc123"
        assert result.error is None
        assert result.retried is False
        assert result.retry_count == 0

    def test_init_failure(self):
        """Test creating a failed result."""
        result = ApplyResult(
            success=False,
            error="Patch application failed"
        )

        assert result.success is False
        assert result.error == "Patch application failed"
        assert result.reference is None

    def test_init_with_retry(self):
        """Test creating a result with retry info."""
        result = ApplyResult(
            success=True,
            reference="abc123",
            retried=True,
            retry_count=2
        )

        assert result.retried is True
        assert result.retry_count == 2


class TestDBOSAvailability:
    """Tests for DBOS availability detection."""

    def test_is_dbos_installed_returns_bool(self):
        """Test that _is_dbos_installed returns a boolean."""
        result = _is_dbos_installed()
        assert isinstance(result, bool)

    def test_dbos_available_is_bool(self):
        """Test that DBOS_AVAILABLE is a boolean."""
        assert isinstance(DBOS_AVAILABLE, bool)


class TestDBOSBackendUnavailable:
    """Tests for DBOSBackendUnavailable fallback."""

    def test_init_raises_import_error(self):
        """Test that DBOSBackendUnavailable raises ImportError."""
        with pytest.raises(ImportError, match="DBOS backend is enabled but not installed"):
            DBOSBackendUnavailable()

    def test_init_with_args_raises_import_error(self):
        """Test that DBOSBackendUnavailable raises with any args."""
        with pytest.raises(ImportError, match="pip install"):
            DBOSBackendUnavailable(
                repo_path=Path("."),
                apply_mode="patch"
            )


class TestApplyResultValidation:
    """Tests for ApplyResult when Pydantic is available."""

    def test_apply_result_model_dump(self):
        """Test that ApplyResult can be serialized."""
        result = ApplyResult(success=True, reference="abc123")

        # Should have model_dump if Pydantic is available
        if hasattr(result, 'model_dump'):
            data = result.model_dump()
            assert data == {
                "success": True,
                "reference": "abc123",
                "error": None,
                "retried": False,
                "retry_count": 0
            }


@pytest.mark.skipif(not DBOS_AVAILABLE, reason="DBOS not installed")
class TestDBOSBackend:
    """Tests for DBOSBackend (requires DBOS installed)."""

    def test_init_patch_mode(self, tmp_path):
        """Test backend initialization in patch mode."""
        backend = DBOSBackend(
            repo_path=tmp_path,
            apply_mode="patch"
        )

        assert backend.repo_path == tmp_path
        assert backend.apply_mode == "patch"
        assert backend.pr_repository is None
        assert backend.pr_branch_prefix == "autoflow/"
        assert backend.custom_handler is None

    def test_init_pr_mode(self, tmp_path):
        """Test backend initialization in PR mode."""
        backend = DBOSBackend(
            repo_path=tmp_path,
            apply_mode="pr",
            pr_repository="myorg/myrepo"
        )

        assert backend.apply_mode == "pr"
        assert backend.pr_repository == "myorg/myrepo"

    def test_init_custom_branch_prefix(self, tmp_path):
        """Test backend with custom branch prefix."""
        backend = DBOSBackend(
            repo_path=tmp_path,
            apply_mode="pr",
            pr_repository="myorg/myrepo",
            pr_branch_prefix="custom/"
        )

        assert backend.pr_branch_prefix == "custom/"

    def test_init_custom_mode_with_handler(self, tmp_path):
        """Test backend in custom mode with handler."""

        def dummy_handler(proposal):
            return ApplyResult(success=True, reference="custom")

        backend = DBOSBackend(
            repo_path=tmp_path,
            apply_mode="custom",
            custom_handler=dummy_handler
        )

        assert backend.apply_mode == "custom"
        assert backend.custom_handler is dummy_handler

    def test_init_invalid_apply_mode(self, tmp_path):
        """Test that invalid apply mode raises ValueError."""
        with pytest.raises(ValueError, match="Invalid apply_mode"):
            DBOSBackend(
                repo_path=tmp_path,
                apply_mode="invalid_mode"
            )

    def test_init_pr_mode_requires_repository(self, tmp_path):
        """Test that PR mode requires pr_repository."""
        with pytest.raises(ValueError, match="apply_mode='pr' requires pr_repository"):
            DBOSBackend(
                repo_path=tmp_path,
                apply_mode="pr"
            )

    def test_init_custom_mode_requires_handler(self, tmp_path):
        """Test that custom mode requires custom_handler."""
        with pytest.raises(ValueError, match="apply_mode='custom' requires custom_handler"):
            DBOSBackend(
                repo_path=tmp_path,
                apply_mode="custom"
            )

    def test_generate_patch_from_proposal_with_patch(self, tmp_path):
        """Test generating patch from proposal with direct patch."""
        backend = DBOSBackend(repo_path=tmp_path, apply_mode="patch")

        proposal = ChangeProposal(
            proposal_id="test_prop",
            kind=ProposalKind.CONFIG_EDIT,
            title="Test",
            description="Test",
            risk=RiskLevel.LOW,
            target_paths=("config/test.yaml",),
            payload={"patch": "--- a/file.txt\n+++ b/file.txt\n@@ -1,1 +1,1 @@\n-old\n+new"}
        )

        patch = backend._generate_patch_from_proposal(proposal)
        assert patch == proposal.payload["patch"]

    def test_generate_patch_from_proposal_with_unified_diff(self, tmp_path):
        """Test generating patch from proposal with unified_diff."""
        backend = DBOSBackend(repo_path=tmp_path, apply_mode="patch")

        proposal = ChangeProposal(
            proposal_id="test_prop",
            kind=ProposalKind.CONFIG_EDIT,
            title="Test",
            description="Test",
            risk=RiskLevel.LOW,
            target_paths=("config/test.yaml",),
            payload={"unified_diff": "--- a/file.txt\n+++ b/file.txt\n@@ -1,1 +1,1 @@\n-old\n+new"}
        )

        patch = backend._generate_patch_from_proposal(proposal)
        assert patch == proposal.payload["unified_diff"]

    def test_generate_patch_from_proposal_with_edits(self, tmp_path):
        """Test generating patch from proposal with file edits."""
        backend = DBOSBackend(repo_path=tmp_path, apply_mode="patch")

        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("old content")

        proposal = ChangeProposal(
            proposal_id="test_prop",
            kind=ProposalKind.CONFIG_EDIT,
            title="Test",
            description="Test",
            risk=RiskLevel.LOW,
            target_paths=("test.txt",),
            payload={
                "edits": [
                    {"path": str(test_file), "content": "new content"}
                ]
            }
        )

        patch = backend._generate_patch_from_proposal(proposal)
        assert patch is not None
        assert "---" in patch
        assert "+++" in patch
        assert "-old content" in patch
        assert "+new content" in patch

    def test_generate_patch_from_proposal_with_config_changes(self, tmp_path):
        """Test generating patch from proposal with config changes."""
        backend = DBOSBackend(repo_path=tmp_path, apply_mode="patch")

        # Create a test file
        test_file = tmp_path / "config.yaml"
        test_file.write_text("key: oldvalue")

        proposal = ChangeProposal(
            proposal_id="test_prop",
            kind=ProposalKind.CONFIG_EDIT,
            title="Test",
            description="Test",
            risk=RiskLevel.LOW,
            target_paths=("config.yaml",),
            payload={
                "config_changes": {
                    str(test_file): "key: newvalue"
                }
            }
        )

        patch = backend._generate_patch_from_proposal(proposal)
        assert patch is not None
        assert "---" in patch
        assert "+++" in patch

    def test_generate_patch_from_proposal_no_patch_data(self, tmp_path):
        """Test generating patch when no patch data exists."""
        backend = DBOSBackend(repo_path=tmp_path, apply_mode="patch")

        proposal = ChangeProposal(
            proposal_id="test_prop",
            kind=ProposalKind.CONFIG_EDIT,
            title="Test",
            description="Test",
            risk=RiskLevel.LOW,
            target_paths=("config/test.yaml",),
            payload={}
        )

        patch = backend._generate_patch_from_proposal(proposal)
        assert patch is None

    def test_simple_diff(self, tmp_path):
        """Test simple diff generation."""
        backend = DBOSBackend(repo_path=tmp_path, apply_mode="patch")

        old_content = "line 1\nline 2\nline 3\n"
        new_content = "line 1\nline 2 modified\nline 3\n"

        diff = backend._simple_diff("test.txt", old_content, new_content)

        assert "--- a/test.txt" in diff
        assert "+++ b/test.txt" in diff
        assert "-line 2" in diff
        assert "+line 2 modified" in diff

    def test_apply_sync_custom_mode(self, tmp_path):
        """Test _apply_sync in custom mode."""

        def custom_handler(proposal):
            return ApplyResult(success=True, reference="custom-ref")

        backend = DBOSBackend(
            repo_path=tmp_path,
            apply_mode="custom",
            custom_handler=custom_handler
        )

        proposal = ChangeProposal(
            proposal_id="test_prop",
            kind=ProposalKind.CONFIG_EDIT,
            title="Test",
            description="Test",
            risk=RiskLevel.LOW,
            target_paths=(),
            payload={}
        )

        result = backend._apply_sync(proposal)

        assert result.success is True
        assert result.reference == "custom-ref"

    def test_apply_sync_patch_mode_no_patch(self, tmp_path):
        """Test _apply_sync in patch mode with no patch data."""
        backend = DBOSBackend(repo_path=tmp_path, apply_mode="patch")

        proposal = ChangeProposal(
            proposal_id="test_prop",
            kind=ProposalKind.CONFIG_EDIT,
            title="Test",
            description="Test",
            risk=RiskLevel.LOW,
            target_paths=(),
            payload={}
        )

        result = backend._apply_sync(proposal)

        assert result.success is False
        assert "No patch content" in result.error


@pytest.mark.skipif(not DBOS_AVAILABLE, reason="DBOS not installed")
class TestDBOSBackendWithGit:
    """Tests for DBOSBackend with git operations (requires git)."""

    def test_git_apply_with_valid_patch(self, tmp_path):
        """Test git apply with a valid patch."""
        # Initialize a git repo
        import subprocess
        subprocess.run(
            ["git", "init"],
            cwd=tmp_path,
            capture_output=True,
            check=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            capture_output=True,
            check=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            capture_output=True,
            check=True
        )

        # Create a file and commit
        test_file = tmp_path / "test.txt"
        test_file.write_text("original content")
        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=tmp_path,
            capture_output=True,
            check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=tmp_path,
            capture_output=True,
            check=True
        )

        # Modify the file and create a proper patch using git diff
        test_file.write_text("modified content")
        subprocess.run(
            ["git", "diff", "test.txt"],
            cwd=tmp_path,
            capture_output=True,
            check=True
        )
        patch_result = subprocess.run(
            ["git", "diff", "test.txt"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True
        )
        patch_content = patch_result.stdout

        # Restore original content for the test
        test_file.write_text("original content")

        backend = DBOSBackend(repo_path=tmp_path, apply_mode="patch")

        result = backend._git_apply(patch_content)

        assert result.success is True

        # Verify the file was modified
        assert test_file.read_text() == "modified content"

    def test_git_commit_creates_commit(self, tmp_path):
        """Test that git commit creates a commit."""
        import subprocess

        # Initialize a git repo
        subprocess.run(
            ["git", "init"],
            cwd=tmp_path,
            capture_output=True,
            check=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            capture_output=True,
            check=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            capture_output=True,
            check=True
        )

        # Create and commit a file
        (tmp_path / "test.txt").write_text("content")
        subprocess.run(
            ["git", "add", "."],
            cwd=tmp_path,
            capture_output=True,
            check=True
        )

        backend = DBOSBackend(repo_path=tmp_path, apply_mode="patch")

        commit_hash = backend._git_commit(
            title="Test commit",
            description="Test description",
            proposal_id="prop-123"
        )

        assert commit_hash is not None
        assert len(commit_hash) == 40  # Full SHA-1 hash

        # Verify commit message
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=%B"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True
        )
        commit_msg = result.stdout
        assert "Test commit" in commit_msg
        assert "Test description" in commit_msg
        assert "prop-123" in commit_msg

    def test_create_branch(self, tmp_path):
        """Test creating a branch."""
        import subprocess

        # Initialize a git repo
        subprocess.run(
            ["git", "init"],
            cwd=tmp_path,
            capture_output=True,
            check=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            capture_output=True,
            check=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            capture_output=True,
            check=True
        )

        # Create initial commit
        (tmp_path / "test.txt").write_text("content")
        subprocess.run(
            ["git", "add", "."],
            cwd=tmp_path,
            capture_output=True,
            check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=tmp_path,
            capture_output=True,
            check=True
        )

        backend = DBOSBackend(repo_path=tmp_path, apply_mode="pr", pr_repository="myorg/myrepo")

        # Create branch
        backend._create_branch("feature-branch")

        # Verify we're on the new branch
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True
        )
        assert result.stdout.strip() == "feature-branch"

        # Calling again should be idempotent (branch already exists)
        backend._create_branch("feature-branch")


@pytest.mark.skipif(DBOS_AVAILABLE, reason="Test only applies when DBOS is not installed")
class TestDBOSBackendWithoutDBOS:
    """Tests for behavior when DBOS is not installed."""

    def test_init_raises_import_error_without_dbos(self, tmp_path):
        """Test that DBOSBackend raises ImportError when DBOS is not installed."""
        with pytest.raises(ImportError, match="DBOS is not installed"):
            DBOSBackend(
                repo_path=tmp_path,
                apply_mode="patch"
            )
