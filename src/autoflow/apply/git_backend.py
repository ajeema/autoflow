from pathlib import Path

from autoflow.types import ChangeProposal


class GitApplyBackend:
    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path

    def apply(self, proposal: ChangeProposal) -> None:
        # Stub for publishable version.
        # Real implementation would apply patch safely.
        print(f"[APPLY] {proposal.title}")