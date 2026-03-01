"""
Apply backends for AutoFlow proposals.

Backends are responsible for actually applying proposals to the codebase.
"""

from autoflow.types import ChangeProposal


class NoOpBackend:
    """Backend that doesn't actually apply anything.

    Useful for shadow evaluation, testing, and when you only want
    to generate proposals without applying them.
    """

    def apply(self, proposal: ChangeProposal) -> None:
        """No-op - logs the proposal but doesn't apply it."""
        pass


class LoggingBackend:
    """Backend that logs proposals instead of applying them."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def apply(self, proposal: ChangeProposal) -> None:
        """Log the proposal details."""
        if self.verbose:
            print(f"[PROPOSAL] {proposal.title}")
            print(f"  Kind: {proposal.kind}")
            print(f"  Risk: {proposal.risk}")
            print(f"  Paths: {proposal.target_paths}")
            print(f"  Description: {proposal.description}")
        else:
            print(f"[PROPOSAL] {proposal.title}")


class CallbackBackend:
    """Backend that calls a user-provided function for each proposal."""

    def __init__(self, callback):
        """
        Args:
            callback: Function that accepts a ChangeProposal
        """
        self.callback = callback

    def apply(self, proposal: ChangeProposal) -> None:
        """Call the user-provided callback."""
        self.callback(proposal)


__all__ = ["NoOpBackend", "LoggingBackend", "CallbackBackend"]
