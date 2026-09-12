"""Branch plumbing shared by ``git-*`` branch commands.

A single ``git for-each-ref`` pass collects local and remote-tracking
branches together with their tracking relationships (who tracks whom,
ahead/behind, gone upstreams, worktree occupancy), so commands can show
or act on the whole picture without re-deriving it per branch.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from toolscripts.core.shell import capture
from toolscripts.git_utils.repo import current_branch, repo_root

_HEADS = "refs/heads/"
_REMOTES = "refs/remotes/"

_FMT = (
    "%(refname)%09%(upstream)%09%(upstream:track,nobracket)%09"
    "%(worktreepath)%09%(objectname:short)%09%(committerdate:short)%09"
    "%(contents:subject)"
)


@dataclass
class LocalBranch:
    """A local branch plus its tracking state."""

    name: str
    ref: str
    upstream: str = ""  # full upstream ref, e.g. ``refs/remotes/origin/main``
    track: str = ""  # "", "gone", "ahead 1", "behind 2", "ahead 1, behind 2"
    merged_into_head: bool = False
    worktree: str = ""  # non-empty when checked out in any worktree
    sha: str = ""
    date: str = ""
    subject: str = ""

    @property
    def upstream_short(self) -> str:
        for prefix in (_REMOTES, _HEADS):
            if self.upstream.startswith(prefix):
                return self.upstream[len(prefix) :]
        return self.upstream

    @property
    def gone(self) -> bool:
        return self.track == "gone"

    @property
    def ahead(self) -> int:
        match = re.search(r"ahead (\d+)", self.track)
        return int(match.group(1)) if match else 0

    @property
    def behind(self) -> int:
        match = re.search(r"behind (\d+)", self.track)
        return int(match.group(1)) if match else 0

    @property
    def merged_into_upstream(self) -> bool:
        """In sync or strictly behind means every local commit is on the upstream."""
        return bool(self.upstream) and not self.gone and self.ahead == 0

    @property
    def safe_to_delete(self) -> bool:
        """True when ``git branch -d`` would accept this branch."""
        return self.merged_into_head or self.merged_into_upstream


@dataclass
class RemoteBranch:
    """A remote-tracking branch, e.g. ``origin/feat/x``."""

    remote: str  # "origin"
    name: str  # "feat/x" (remote prefix stripped)
    ref: str
    merged_into_head: bool = False
    sha: str = ""
    date: str = ""
    subject: str = ""

    @property
    def short(self) -> str:
        return f"{self.remote}/{self.name}"


@dataclass
class BranchSnapshot:
    """Everything worth knowing about a repo's branches, in one pass."""

    repo_name: str
    current: str  # "" on detached HEAD
    local: list[LocalBranch]
    remote_groups: list[tuple[str, list[RemoteBranch]]]  # (remote name, branches)
    local_by_ref: dict[str, LocalBranch] = field(default_factory=dict)
    remote_by_ref: dict[str, RemoteBranch] = field(default_factory=dict)

    def tracked_by(self, remote_ref: str) -> LocalBranch | None:
        """Return the local branch tracking ``remote_ref``, if any."""
        for b in self.local:
            if b.upstream == remote_ref:
                return b
        return None


def collect_snapshot(path: str | Path = ".") -> BranchSnapshot:
    """Collect local/remote branch info for the repo containing ``path``.

    Raises ``subprocess.CalledProcessError`` when not inside a git repo —
    guard with :func:`toolscripts.git_utils.repo.is_git_repo` first.
    """
    git = ["git", "-C", str(path)]
    rows = capture([*git, "for-each-ref", f"--format={_FMT}", _HEADS, _REMOTES])
    try:
        merged = set(
            capture(
                [
                    *git,
                    "for-each-ref",
                    "--format=%(refname)",
                    "--merged",
                    "HEAD",
                    _HEADS,
                    _REMOTES,
                ]
            ).splitlines()
        )
    except subprocess.CalledProcessError:
        # unborn HEAD (fresh repo): nothing is merged yet
        merged = set()
    remotes = sorted(capture([*git, "remote"]).splitlines(), key=len, reverse=True)
    current = current_branch(path)

    local: list[LocalBranch] = []
    remote_rows: list[RemoteBranch] = []
    for line in rows.splitlines():
        parts = line.split("\t", 6)
        if len(parts) < 7:
            continue
        ref, upstream, track, worktree, sha, date, subject = parts
        if ref.startswith(_HEADS):
            local.append(
                LocalBranch(
                    name=ref[len(_HEADS) :],
                    ref=ref,
                    upstream=upstream,
                    track=track,
                    merged_into_head=ref in merged,
                    worktree=worktree,
                    sha=sha,
                    date=date,
                    subject=subject,
                )
            )
        elif ref.startswith(_REMOTES):
            for remote in remotes:
                prefix = _REMOTES + remote + "/"
                if not ref.startswith(prefix) or ref == prefix + "HEAD":
                    continue
                remote_rows.append(
                    RemoteBranch(
                        remote=remote,
                        name=ref[len(prefix) :],
                        ref=ref,
                        merged_into_head=ref in merged,
                        sha=sha,
                        date=date,
                        subject=subject,
                    )
                )
                break

    local.sort(key=lambda b: (b.name != current, b.name))
    grouped: dict[str, list[RemoteBranch]] = {}
    for rb in remote_rows:
        grouped.setdefault(rb.remote, []).append(rb)
    remote_groups = [
        (remote, sorted(branches, key=lambda rb: rb.name))
        for remote, branches in sorted(grouped.items())
    ]

    snapshot = BranchSnapshot(
        repo_name=Path(repo_root(path)).name,
        current=current,
        local=local,
        remote_groups=remote_groups,
    )
    snapshot.local_by_ref = {b.ref: b for b in local}
    snapshot.remote_by_ref = {rb.ref: rb for _, branches in remote_groups for rb in branches}
    return snapshot
