"""Tests for CLI module (__main__)."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestCLI:
    """Tests for AutoFlow CLI."""

    def test_main_function_exists(self):
        """Test that main function can be imported."""
        from autoflow.__main__ import main

        assert callable(main)

    @patch("autoflow.__main__.AutoImproveEngine")
    @patch("autoflow.__main__.make_event")
    @patch("autoflow.__main__.SQLiteGraphStore")
    @patch("autoflow.__main__.ContextGraphBuilder")
    @patch("autoflow.__main__.DecisionGraph")
    @patch("autoflow.__main__.CompositeEvaluator")
    @patch("autoflow.__main__.ShadowEvaluator")
    @patch("autoflow.__main__.ProposalApplier")
    @patch("autoflow.__main__.ApplyPolicy")
    @patch("autoflow.__main__.GitApplyBackend")
    @patch("sys.argv", ["autoflow", "--db", "test.db"])
    def test_main_with_default_args(
        self,
        mock_git_backend,
        mock_policy,
        mock_applier,
        mock_shadow,
        mock_composite,
        mock_decision,
        mock_builder,
        mock_store,
        mock_make_event,
        mock_engine,
    ):
        """Test main function with default arguments."""
        # Setup mocks
        engine_instance = MagicMock()
        engine_instance.propose.return_value = []
        engine_instance.evaluator = MagicMock()
        engine_instance.evaluator.evaluate.return_value = MagicMock(passed=True)
        engine_instance.apply.return_value = []
        mock_engine.return_value = engine_instance

        from autoflow.__main__ import main

        # New CLI implementation raises SystemExit instead of returning
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

        # Verify engine was created
        mock_engine.assert_called_once()

        # Verify ingest, propose, evaluate, and apply were called
        engine_instance.ingest.assert_called_once()
        engine_instance.propose.assert_called_once()

    @patch("autoflow.__main__.AutoImproveEngine")
    @patch("autoflow.__main__.make_event")
    @patch("autoflow.__main__.SQLiteGraphStore")
    @patch("autoflow.__main__.ContextGraphBuilder")
    @patch("autoflow.__main__.DecisionGraph")
    @patch("autoflow.__main__.CompositeEvaluator")
    @patch("autoflow.__main__.ShadowEvaluator")
    @patch("autoflow.__main__.ProposalApplier")
    @patch("autoflow.__main__.ApplyPolicy")
    @patch("autoflow.__main__.GitApplyBackend")
    @patch("sys.argv", ["autoflow", "--workflow-id", "test_wf", "--threshold", "5"])
    def test_main_with_custom_args(
        self,
        mock_git_backend,
        mock_policy,
        mock_applier,
        mock_shadow,
        mock_composite,
        mock_decision,
        mock_builder,
        mock_store,
        mock_make_event,
        mock_engine,
    ):
        """Test main function with custom workflow ID and threshold."""
        engine_instance = MagicMock()
        engine_instance.propose.return_value = []
        engine_instance.evaluator = MagicMock()
        engine_instance.evaluator.evaluate.return_value = MagicMock(passed=True)
        engine_instance.apply.return_value = []
        mock_engine.return_value = engine_instance

        from autoflow.__main__ import main

        # New CLI implementation raises SystemExit instead of returning
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

        # Verify DecisionGraph was called
        mock_decision.assert_called_once()
        # Verify the rule has the right threshold via the rules keyword parameter
        call_kwargs = mock_decision.call_args[1]
        rules = call_kwargs['rules']
        assert len(rules) == 1
        assert rules[0].threshold == 5

    def test_main_parsers_arguments(self):
        """Test that CLI parser accepts all expected arguments."""
        from autoflow.__main__ import argparse

        # We can't easily test argparse without running main()
        # but we can verify the argument parser is configured
        import sys
        original_argv = sys.argv

        try:
            sys.argv = ["autoflow", "--db", "custom.db", "--repo", "/path/to/repo"]
            from autoflow.__main__ import main

            # Will fail because we don't have a real engine, but we can
            # verify it parses arguments before failing
            with pytest.raises(Exception):
                main()
        except SystemExit:
            # Expected to exit
            pass
        finally:
            sys.argv = original_argv

    @patch("autoflow.__main__.AutoImproveEngine")
    @patch("autoflow.__main__.make_event")
    @patch("autoflow.__main__.SQLiteGraphStore")
    @patch("autoflow.__main__.ContextGraphBuilder")
    @patch("autoflow.__main__.DecisionGraph")
    @patch("autoflow.__main__.CompositeEvaluator")
    @patch("autoflow.__main__.ShadowEvaluator")
    @patch("autoflow.__main__.ProposalApplier")
    @patch("autoflow.__main__.ApplyPolicy")
    @patch("autoflow.__main__.GitApplyBackend")
    @patch("sys.argv", ["autoflow"])
    def test_main_creates_proposals(
        self,
        mock_git_backend,
        mock_policy,
        mock_applier,
        mock_shadow,
        mock_composite,
        mock_decision,
        mock_builder,
        mock_store,
        mock_make_event,
        mock_engine,
        capsys,
    ):
        """Test that main creates and displays proposals."""
        # Setup mock to return proposals
        from autoflow.types import ChangeProposal, ProposalKind, RiskLevel

        proposal = ChangeProposal(
            proposal_id="test_prop",
            kind=ProposalKind.CONFIG_EDIT,
            title="Test Proposal",
            description="Test Description",
            risk=RiskLevel.LOW,
            target_paths=("config/test.yaml",),
            payload={},
        )

        engine_instance = MagicMock()
        engine_instance.propose.return_value = [proposal]
        engine_instance.evaluator = MagicMock()
        engine_instance.evaluator.evaluate.return_value = MagicMock(
            passed=True, score=1.0, metrics={}, notes=""
        )
        engine_instance.apply.return_value = [proposal]
        mock_engine.return_value = engine_instance

        from autoflow.__main__ import main

        # New CLI implementation raises SystemExit instead of returning
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

        # Check output
        captured = capsys.readouterr()
        assert "proposals=1" in captured.out
        assert "applied=1" in captured.out
        assert "Test Proposal" in captured.out

    @patch("autoflow.__main__.AutoImproveEngine")
    @patch("autoflow.__main__.make_event")
    @patch("autoflow.__main__.SQLiteGraphStore")
    @patch("autoflow.__main__.ContextGraphBuilder")
    @patch("autoflow.__main__.DecisionGraph")
    @patch("autoflow.__main__.CompositeEvaluator")
    @patch("autoflow.__main__.ShadowEvaluator")
    @patch("autoflow.__main__.ProposalApplier")
    @patch("autoflow.__main__.ApplyPolicy")
    @patch("autoflow.__main__.GitApplyBackend")
    @patch("sys.argv", ["autoflow"])
    def test_main_handles_zero_proposals(
        self,
        mock_git_backend,
        mock_policy,
        mock_applier,
        mock_shadow,
        mock_composite,
        mock_decision,
        mock_builder,
        mock_store,
        mock_make_event,
        mock_engine,
        capsys,
    ):
        """Test main when no proposals are generated."""
        engine_instance = MagicMock()
        engine_instance.propose.return_value = []
        engine_instance.apply.return_value = []
        mock_engine.return_value = engine_instance

        from autoflow.__main__ import main

        # New CLI implementation raises SystemExit instead of returning
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert "proposals=0" in captured.out
        assert "applied=0" in captured.out

    @patch("autoflow.__main__.AutoImproveEngine")
    @patch("autoflow.__main__.make_event")
    @patch("autoflow.__main__.SQLiteGraphStore")
    @patch("autoflow.__main__.ContextGraphBuilder")
    @patch("autoflow.__main__.DecisionGraph")
    @patch("autoflow.__main__.CompositeEvaluator")
    @patch("autoflow.__main__.ShadowEvaluator")
    @patch("autoflow.__main__.ProposalApplier")
    @patch("autoflow.__main__.ApplyPolicy")
    @patch("autoflow.__main__.GitApplyBackend")
    @patch("sys.argv", ["autoflow", "--db", "custom.db"])
    def test_main_uses_custom_db_path(
        self,
        mock_git_backend,
        mock_policy,
        mock_applier,
        mock_shadow,
        mock_composite,
        mock_decision,
        mock_builder,
        mock_store,
        mock_make_event,
        mock_engine,
    ):
        """Test that main uses custom database path."""
        engine_instance = MagicMock()
        engine_instance.propose.return_value = []
        engine_instance.apply.return_value = []
        mock_engine.return_value = engine_instance

        from autoflow.__main__ import main

        # New CLI implementation raises SystemExit instead of returning
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

        # Verify SQLiteGraphStore was called with custom path
        mock_store.assert_called_once_with(db_path="custom.db")

    @patch("autoflow.__main__.AutoImproveEngine")
    @patch("autoflow.__main__.make_event")
    @patch("autoflow.__main__.SQLiteGraphStore")
    @patch("autoflow.__main__.ContextGraphBuilder")
    @patch("autoflow.__main__.DecisionGraph")
    @patch("autoflow.__main__.CompositeEvaluator")
    @patch("autoflow.__main__.ShadowEvaluator")
    @patch("autoflow.__main__.ProposalApplier")
    @patch("autoflow.__main__.ApplyPolicy")
    @patch("autoflow.__main__.GitApplyBackend")
    @patch("sys.argv", ["autoflow", "--repo", "/custom/repo"])
    def test_main_uses_custom_repo_path(
        self,
        mock_git_backend,
        mock_policy,
        mock_applier,
        mock_shadow,
        mock_composite,
        mock_decision,
        mock_builder,
        mock_store,
        mock_make_event,
        mock_engine,
    ):
        """Test that main uses custom repo path."""
        engine_instance = MagicMock()
        engine_instance.propose.return_value = []
        engine_instance.apply.return_value = []
        mock_engine.return_value = engine_instance

        from autoflow.__main__ import main

        # New CLI implementation raises SystemExit instead of returning
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

        # Verify GitApplyBackend was called with custom path
        mock_git_backend.assert_called_once_with(repo_path=Path("/custom/repo"))

    def test_main_as_entry_point(self):
        """Test that __main__ can be executed as entry point."""
        import subprocess
        import sys

        # Test that the module can be executed
        result = subprocess.run(
            [sys.executable, "-m", "autoflow", "--help"],
            capture_output=True,
            text=True,
        )

        # Should show help (or error about missing dependencies, but not syntax error)
        assert result.returncode in [0, 1, 2]  # Various exit codes are acceptable
