"""Tests for the git branch snapshot plumbing (``git_utils.branches``)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from toolscripts.git_utils.branches import collect_snapshot


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    work = tmp_path / "work"
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "-b", "master", "--bare", str(remote)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "master", str(work)], check=True)
    _git(work, "commit", "--allow-empty", "-qm", "init")
    _git(work, "remote", "add", "origin", str(remote))
    _git(work, "push", "-qu", "origin", "master")
    return work


def _branch_with_commit(work: Path, name: str, *, push: bool = False) -> None:
    _git(work, "checkout", "-qb", name)
    _git(work, "commit", "--allow-empty", "-qm", f"c-{name}")
    if push:
        _git(work, "push", "-qu", "origin", name)
    _git(work, "checkout", "-q", "master")


def test_snapshot_tracks_upstream_and_gone(repo: Path) -> None:
    _branch_with_commit(repo, "feat/login", push=True)
    _git(repo, "merge", "-q", "feat/login")
    _branch_with_commit(repo, "gone/api", push=True)
    _git(repo, "merge", "-q", "gone/api")
    _git(repo, "push", "-q", "origin", "--delete", "gone/api")
    _branch_with_commit(repo, "spike/local-only")

    snap = collect_snapshot(repo)

    assert snap.current == "master"
    assert snap.repo_name == "work"
    names = [b.name for b in snap.local]
    assert names[0] == "master"  # current branch is pinned first
    assert set(names) == {"master", "feat/login", "gone/api", "spike/local-only"}

    by_name = {b.name: b for b in snap.local}
    login = by_name["feat/login"]
    assert login.upstream_short == "origin/feat/login"
    assert login.merged_into_head and login.safe_to_delete
    assert not login.gone

    gone = by_name["gone/api"]
    assert gone.gone and gone.safe_to_delete  # merged into master, upstream deleted

    spike = by_name["spike/local-only"]
    assert not spike.upstream and not spike.safe_to_delete

    remote_names = {rb.short for _, branches in snap.remote_groups for rb in branches}
    assert remote_names == {"origin/feat/login", "origin/master"}
    assert snap.tracked_by("refs/remotes/origin/feat/login") is login
    assert snap.tracked_by("refs/remotes/origin/master").name == "master"


def test_snapshot_marks_unmerged_ahead(repo: Path) -> None:
    _branch_with_commit(repo, "feat/ahead", push=True)
    _git(repo, "checkout", "-q", "feat/ahead")
    _git(repo, "commit", "--allow-empty", "-qm", "extra")  # unpushed commit on the branch
    _git(repo, "checkout", "-q", "master")

    snap = collect_snapshot(repo)
    ahead = {b.name: b for b in snap.local}["feat/ahead"]
    assert ahead.ahead == 1 and ahead.behind == 0
    assert not ahead.safe_to_delete


def test_snapshot_on_unborn_repo(tmp_path: Path) -> None:
    work = tmp_path / "fresh"
    subprocess.run(["git", "init", "-q", "-b", "master", str(work)], check=True)
    snap = collect_snapshot(work)
    assert snap.current == "master"  # unborn branch is still reported
    assert snap.local == [] and snap.remote_groups == []
