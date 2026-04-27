"""Common git operations used by ``git-*`` commands."""

from __future__ import annotations

import subprocess
from pathlib import Path

from toolscripts.core.shell import capture


def is_git_repo(path: str | Path = ".") -> bool:
    """Return True if ``path`` is inside a git working tree."""
    try:
        capture(
            ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def repo_root(path: str | Path = ".") -> str:
    """Return the absolute path of the repo root containing ``path``."""
    return capture(["git", "-C", str(path), "rev-parse", "--show-toplevel"])


def current_branch(path: str | Path = ".") -> str:
    """Return the current branch name (or empty for detached HEAD)."""
    return capture(["git", "-C", str(path), "branch", "--show-current"])


def get_diff(
    *,
    staged: bool = False,
    against: str | None = None,
    path: str | Path = ".",
) -> str:
    """Return ``git diff`` output.

    Args:
        staged:  use ``--cached`` (only staged changes).
        against: compare against the given ref (e.g. ``main``).
        path:    repo path.
    """
    cmd = ["git", "-C", str(path), "diff"]
    if staged:
        cmd.append("--cached")
    if against:
        cmd.append(against)
    return capture(cmd, strip=False)
