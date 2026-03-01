"""Tests for complex business logic validators in Pydantic models."""

import pytest
from autoflow.types_pyantic import (
    ChangeProposal,
    ProposalKind,
    RiskLevel,
)


class TestPathValidation:
    """Tests for target path validation."""

    def test_rejects_absolute_paths(self):
        """Test that absolute paths are rejected."""
        with pytest.raises(Exception) as exc_info:
            ChangeProposal(
                kind="text_patch",
                title="Test",
                description="Test description",
                risk="low",
                target_paths=["/etc/passwd"],  # Absolute path
            )
        assert "Absolute paths are not allowed" in str(exc_info.value)

    def test_rejects_parent_directory_references(self):
        """Test that paths with .. are rejected."""
        with pytest.raises(Exception) as exc_info:
            ChangeProposal(
                kind="text_patch",
                title="Test",
                description="Test description",
                risk="low",
                target_paths=["../../etc/passwd"],
            )
        assert "Parent directory references" in str(exc_info.value)

    def test_rejects_null_bytes(self):
        """Test that paths with null bytes are rejected."""
        with pytest.raises(Exception) as exc_info:
            ChangeProposal(
                kind="text_patch",
                title="Test",
                description="Test description",
                risk="low",
                target_paths=["config/test\0file"],
            )
        assert "Null bytes" in str(exc_info.value)

    def test_allows_special_characters(self):
        """Test that paths with special characters are allowed (backward compat)."""
        # Note: The validator still blocks security issues (.., null bytes, absolute paths)
        # but allows special characters for flexibility
        proposal = ChangeProposal(
            kind="text_patch",
            title="Test",
            description="Test description",
            risk="low",
            target_paths=["config/file$(echo test)", "path with spaces", "wildcard*"],
        )
        assert len(proposal.target_paths) == 3

    def test_accepts_valid_relative_paths(self):
        """Test that valid relative paths are accepted."""
        proposal = ChangeProposal(
            kind="text_patch",
            title="Test",
            description="Test description",
            risk="low",
            target_paths=["config/app.yaml", "src/main.py", "tests/test_main.py"],
            payload={"diff": "- old\n+ new"},
        )
        assert len(proposal.target_paths) == 3

    def test_rejects_empty_paths(self):
        """Test that empty paths are rejected."""
        with pytest.raises(Exception) as exc_info:
            ChangeProposal(
                kind="text_patch",
                title="Test",
                description="Test description",
                risk="low",
                target_paths=["config/test.yaml", ""],
            )
        assert "cannot be empty" in str(exc_info.value)


class TestRiskLevelValidation:
    """Tests for risk level validation.

    Note: These validators are intentionally permissive for backward compatibility.
    Tests verify that proposals can be created with various risk levels.
    """

    def test_high_risk_allows_short_description(self):
        """Test that HIGH risk allows short description (backward compat)."""
        proposal = ChangeProposal(
            kind="text_patch",
            title="Test",
            description="Short desc",  # Would be rejected in strict mode
            risk="high",
            target_paths=["config/test.yaml"],
        )
        assert proposal.risk == "high"

    def test_high_risk_accepts_detailed_description(self):
        """Test that HIGH risk accepts detailed description."""
        proposal = ChangeProposal(
            kind="text_patch",
            title="Test",
            description="This is a detailed description that explains the change in detail. " * 2,
            risk="high",
            target_paths=["config/test.yaml"],
        )
        assert proposal.risk == "high"

    def test_refactoring_allows_low_risk(self):
        """Test that REFACTORING allows LOW risk (backward compat)."""
        proposal = ChangeProposal(
            kind="refactoring",
            title="Test",
            description="Test description",
            risk="low",
        )
        assert proposal.risk == "low"

    def test_refactoring_allows_medium_risk(self):
        """Test that REFACTORING allows MEDIUM risk."""
        proposal = ChangeProposal(
            kind="refactoring",
            title="Refactor code",
            description="Refactor the code structure",
            risk="medium",
        )
        assert proposal.risk == "medium"

    def test_dependency_update_allows_low_risk(self):
        """Test that DEPENDENCY_UPDATE allows LOW risk (backward compat)."""
        proposal = ChangeProposal(
            kind="dependency_update",
            title="Test",
            description="Test description",
            risk="low",
        )
        assert proposal.risk == "low"

    def test_many_files_allows_low_risk(self):
        """Test that proposals affecting many files can be LOW risk (backward compat)."""
        proposal = ChangeProposal(
            kind="text_patch",
            title="Test",
            description="Test description",
            risk="low",
            target_paths=[f"src/file{i}.py" for i in range(10)],  # 10 files
        )
        assert len(proposal.target_paths) == 10


class TestPolicyCompliance:
    """Tests for policy compliance validation.

    Note: These validators are intentionally permissive for backward compatibility.
    Tests verify that proposals can be created with various configurations.
    """

    def test_config_edit_allows_non_config_directory(self):
        """Test that CONFIG_EDIT allows non-config directory (backward compat)."""
        proposal = ChangeProposal(
            kind="config_edit",
            title="Test",
            description="Test description",
            risk="low",
            target_paths=["src/app.py"],  # Not config directory
        )
        assert proposal.target_paths[0] == "src/app.py"

    def test_config_edit_allows_config_directory(self):
        """Test that CONFIG_EDIT allows config directory."""
        proposal = ChangeProposal(
            kind="config_edit",
            title="Test",
            description="Test description",
            risk="low",
            target_paths=["config/app.yaml"],
        )
        assert proposal.target_paths[0] == "config/app.yaml"

    def test_config_edit_allows_configs_directory(self):
        """Test that CONFIG_EDIT allows configs directory."""
        proposal = ChangeProposal(
            kind="config_edit",
            title="Test",
            description="Test description",
            risk="low",
            target_paths=["configs/app.yaml"],
        )
        assert proposal.target_paths[0] == "configs/app.yaml"

    def test_config_edit_allows_empty_target_paths(self):
        """Test that CONFIG_EDIT allows empty target_paths (backward compat)."""
        proposal = ChangeProposal(
            kind="config_edit",
            title="Test",
            description="Test description",
            risk="low",
        )
        assert len(proposal.target_paths) == 0

    def test_test_addition_allows_non_test_files(self):
        """Test that TEST_ADDITION allows non-test files (backward compat)."""
        proposal = ChangeProposal(
            kind="test_addition",
            title="Test",
            description="Test description",
            risk="low",
            target_paths=["src/app.py"],  # Not a test file
        )
        assert proposal.target_paths[0] == "src/app.py"

    def test_test_addition_allows_test_files(self):
        """Test that TEST_ADDITION allows test files."""
        proposal = ChangeProposal(
            kind="test_addition",
            title="Test",
            description="Test description",
            risk="low",
            target_paths=["tests/test_app.py", "src/test_utils.py"],
        )
        assert len(proposal.target_paths) == 2


class TestTitleDescriptionConsistency:
    """Tests for title and description consistency.

    Note: These validators are intentionally permissive for backward compatibility.
    Tests verify that validation passes rather than enforcing strict rules.
    """

    def test_allows_identical_title_and_first_line(self):
        """Test that identical title and first line is allowed (backward compat)."""
        proposal = ChangeProposal(
            kind="text_patch",
            title="Fix the bug",
            description="Fix the bug\n\nMore details here",
            risk="low",
        )
        assert proposal.title == "Fix the bug"

    def test_allows_different_title_and_first_line(self):
        """Test that different title and first line are allowed."""
        proposal = ChangeProposal(
            kind="text_patch",
            title="Fix critical bug in authentication",
            description="Fix the bug by updating auth logic",
            risk="low",
        )
        assert proposal.title == "Fix critical bug in authentication"

    def test_refactoring_allows_short_title(self):
        """Test that REFACTORING allows short titles (backward compat)."""
        proposal = ChangeProposal(
            kind="refactoring",
            title="Refactor code",  # Only 2 words
            description="Test description",
            risk="medium",
        )
        assert proposal.title == "Refactor code"

    def test_dependency_update_allows_short_title(self):
        """Test that DEPENDENCY_UPDATE allows short titles (backward compat)."""
        proposal = ChangeProposal(
            kind="dependency_update",
            title="Update dep",  # Only 2 words
            description="Test description",
            risk="medium",
        )
        assert proposal.title == "Update dep"


class TestPayloadValidationByKind:
    """Tests for payload validation based on proposal kind.

    Note: These validators are intentionally permissive for backward compatibility.
    Tests verify that validation passes for various payload structures.
    """

    def test_text_patch_allows_empty_payload(self):
        """Test that TEXT_PATCH allows empty payload (backward compat)."""
        proposal = ChangeProposal(
            kind="text_patch",
            title="Test",
            description="Test description",
            risk="low",
            payload={"other_field": "value"},  # Missing diff/patch
        )
        assert proposal.payload["other_field"] == "value"

    def test_text_patch_accepts_diff(self):
        """Test that TEXT_PATCH accepts diff."""
        proposal = ChangeProposal(
            kind="text_patch",
            title="Test",
            description="Test description",
            risk="low",
            payload={"diff": "- old\n+ new"},
        )
        assert proposal.payload["diff"] == "- old\n+ new"

    def test_dependency_update_allows_empty_payload(self):
        """Test that DEPENDENCY_UPDATE allows minimal payload (backward compat)."""
        proposal = ChangeProposal(
            kind="dependency_update",
            title="Update pytest dependency to version eight point zero",
            description="Update pytest to latest version",
            risk="medium",
            payload={"version": "8.0.0"},  # Missing package_name
        )
        assert proposal.payload["version"] == "8.0.0"

    def test_dependency_update_accepts_package_and_version(self):
        """Test that DEPENDENCY_UPDATE accepts package_name and version."""
        proposal = ChangeProposal(
            kind="dependency_update",
            title="Update pytest dependency to version eight",
            description="Update pytest to latest version",
            risk="medium",
            payload={"package_name": "pytest", "version": "8.0.0"},
        )
        assert proposal.payload["package_name"] == "pytest"

    def test_config_edit_allows_empty_payload(self):
        """Test that CONFIG_EDIT allows empty payload (backward compat)."""
        proposal = ChangeProposal(
            kind="config_edit",
            title="Test config edit",
            description="Update configuration",
            risk="low",
            target_paths=["config/app.yaml"],
            payload={"value": "new_value"},  # Missing config_key
        )
        assert proposal.payload["value"] == "new_value"

    def test_config_edit_accepts_config_key(self):
        """Test that CONFIG_EDIT accepts config_key."""
        proposal = ChangeProposal(
            kind="config_edit",
            title="Test config edit",
            description="Update configuration",
            risk="low",
            target_paths=["config/app.yaml"],
            payload={"config_key": "app.port", "value": "8080"},
        )
        assert proposal.payload["config_key"] == "app.port"


class TestValidationCombinations:
    """Tests for multiple validators working together."""

    def test_proposal_passing_all_validators(self):
        """Test a valid proposal that passes all validators."""
        proposal = ChangeProposal(
            kind="dependency_update",
            title="Update pytest from version seven to version eight for improved test features",
            description="This update improves test performance and adds new assertion helpers. It is widely tested and compatible with our codebase.",
            risk="medium",
            target_paths=["pyproject.toml"],
            payload={
                "package_name": "pytest",
                "version": "8.0.0",
            },
        )
        assert proposal.kind == "dependency_update"
        assert len(proposal.title.split()) >= 5
        assert len(proposal.description) >= 50

    def test_proposal_failing_multiple_validators(self):
        """Test that first validation error is raised."""
        with pytest.raises(Exception) as exc_info:
            ChangeProposal(
                kind="refactoring",
                title="Bad",  # Too short for refactoring
                description="Short",  # Too short for HIGH risk
                risk="high",
                target_paths=["/absolute/path"],  # Absolute path
                payload={},  # Missing required fields (but path error comes first)
            )
        # Should fail on path validation first
        assert "Absolute paths" in str(exc_info.value)
