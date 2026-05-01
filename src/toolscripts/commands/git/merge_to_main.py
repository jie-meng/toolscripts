"""``git-merge-to-main`` - merge current branch into the main branch."""

from __future__ import annotations

import argparse
import contextlib
import subprocess
import sys

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.prompts import yes_no
from toolscripts.core.shell import CommandNotFoundError, capture, require, run
from toolscripts.core.ui_curses import select_one
from toolscripts.git_utils.repo import current_branch, is_git_repo

log = get_logger(__name__)

MAIN_BRANCH_CANDIDATES = ["main", "master"]


def _list_local_branches() -> list[str]:
    out = capture(["git", "branch"], check=False)
    return [line.strip().lstrip("* ") for line in out.splitlines() if line.strip()]


def _detect_main_branch() -> str | None:
    """Return the main branch name if exactly one candidate exists locally."""
    local = _list_local_branches()
    found = [b for b in MAIN_BRANCH_CANDIDATES if b in local]
    if len(found) == 1:
        return found[0]
    return None


def _pick_main_branch() -> str | None:
    """Let the user choose a main branch from candidates that exist locally."""
    local = _list_local_branches()
    candidates = [b for b in MAIN_BRANCH_CANDIDATES if b in local]
    if not candidates:
        log.error(
            "none of the main branch candidates (%s) exist locally",
            ", ".join(MAIN_BRANCH_CANDIDATES),
        )
        return None
    if len(candidates) == 1:
        return candidates[0]

    # Mark the preferred one with a star
    labels = []
    for b in candidates:
        labels.append(f"{b}  *" if b == candidates[0] else b)
    idx = select_one("Select the main branch to merge into:", labels)
    if idx is None:
        return None
    return candidates[idx]


def _remote_branch_exists(branch: str) -> bool:
    """Check if the remote tracking branch exists."""
    remote = capture(["git", "config", "--get", f"branch.{branch}.remote"], check=False)
    if not remote:
        return False
    merge_ref = capture(["git", "config", "--get", f"branch.{branch}.merge"], check=False)
    if not merge_ref:
        return False
    # merge_ref is like refs/heads/feat-xxx
    ref = merge_ref.replace("refs/heads/", "refs/remotes/" + remote + "/")
    return_code = subprocess.call(
        ["git", "show-ref", "--verify", "--quiet", ref],
        text=True,
    )
    return return_code == 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="git-merge-to-main",
        description=(
            "Merge the current branch into the main branch. "
            "Rebases current branch onto main first, then merges, "
            "and optionally deletes the source branch (local + remote)."
        ),
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        require("git")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)

    if not is_git_repo():
        log.error("not inside a git repository")
        sys.exit(1)

    branch = current_branch()
    if not branch:
        log.error("detached HEAD — cannot determine current branch")
        sys.exit(1)

    # Step 0: pick main branch
    main_branch = _detect_main_branch()
    if main_branch is None:
        main_branch = _pick_main_branch()
    if main_branch is None:
        sys.exit(1)

    if branch == main_branch:
        log.error("already on the main branch (%s), nothing to merge", main_branch)
        sys.exit(1)

    log.info("source branch: %s", branch)
    log.info("target branch: %s", main_branch)

    # Step 1: update main branch
    log.info("updating %s to latest...", main_branch)
    try:
        run(["git", "fetch", "origin", main_branch])
    except subprocess.CalledProcessError as exc:
        log.error("failed to fetch origin/%s", main_branch)
        _print_failure("fetch", exc)
        sys.exit(1)

    try:
        run(["git", "checkout", main_branch])
    except subprocess.CalledProcessError as exc:
        log.error("failed to checkout %s", main_branch)
        _print_failure("checkout", exc)
        sys.exit(1)

    try:
        run(["git", "pull", "--ff-only", "origin", main_branch])
    except subprocess.CalledProcessError as exc:
        log.error("failed to pull %s", main_branch)
        _print_failure("pull", exc)
        _restore_branch(branch)
        sys.exit(1)

    # Step 2: rebase current branch onto main
    log.info("rebasing %s onto %s...", branch, main_branch)
    try:
        run(["git", "checkout", branch])
    except subprocess.CalledProcessError as exc:
        log.error("failed to checkout %s", branch)
        _print_failure("checkout", exc)
        sys.exit(1)

    try:
        run(["git", "rebase", main_branch])
    except subprocess.CalledProcessError as exc:
        log.error("rebase failed — there may be conflicts")
        _print_failure("rebase", exc)
        log.info("you are now on branch %s with a conflicted rebase", branch)
        log.info("resolve conflicts, then run: git rebase --continue")
        sys.exit(1)

    # Step 3: merge into main
    log.info("merging %s into %s...", branch, main_branch)
    try:
        run(["git", "checkout", main_branch])
    except subprocess.CalledProcessError as exc:
        log.error("failed to checkout %s", main_branch)
        _print_failure("checkout", exc)
        sys.exit(1)

    try:
        run(["git", "merge", "--no-ff", "--no-edit", branch])
    except subprocess.CalledProcessError as exc:
        log.error("merge failed — there may be conflicts")
        _print_failure("merge", exc)
        log.info("you are now on branch %s", main_branch)
        _restore_branch(branch)
        sys.exit(1)

    log.success("%s merged into %s", branch, main_branch)

    has_errors = False

    # Step 4: delete local branch
    if yes_no(f"delete local branch '{branch}'?", default=True):
        try:
            capture(["git", "branch", "-d", branch])
            log.success("deleted local branch %s", branch)
        except subprocess.CalledProcessError as exc:
            log.warning("branch has unmerged commits")
            _print_failure("branch -d", exc)
            if yes_no(f"force delete local branch '{branch}'?", default=False):
                try:
                    capture(["git", "branch", "-D", branch])
                    log.success("force deleted local branch %s", branch)
                except subprocess.CalledProcessError as exc2:
                    log.error("failed to force delete local branch %s", branch)
                    _print_failure("branch -D", exc2)
                    has_errors = True
            else:
                has_errors = True

    # Step 5: delete remote branch if exists
    if _remote_branch_exists(branch):
        if yes_no(f"delete remote branch 'origin/{branch}'?", default=True):
            try:
                run(["git", "push", "origin", "--delete", "--no-verify", branch])
                log.success("deleted remote branch origin/%s", branch)
            except subprocess.CalledProcessError as exc:
                log.error("failed to delete remote branch origin/%s", branch)
                _print_failure("push --delete", exc)
                has_errors = True
    else:
        log.debug("no remote tracking branch for %s, skipping remote delete", branch)

    # Step 6: push main
    if yes_no(f"push {main_branch} to origin?", default=True):
        log.info("pushing %s...", main_branch)
        try:
            run(["git", "push", "origin", main_branch])
            log.success("pushed %s", main_branch)
        except subprocess.CalledProcessError as exc:
            log.error("failed to push %s", main_branch)
            _print_failure("push", exc)
            sys.exit(1)
    else:
        log.warning("skipped push — %s is only updated locally", main_branch)

    if has_errors:
        log.warning("completed with errors (see above)")
    else:
        log.success("done!")


def _restore_branch(branch: str) -> None:
    """Best-effort checkout back to the given branch."""
    with contextlib.suppress(FileNotFoundError):
        subprocess.run(
            ["git", "checkout", branch],
            check=False,
            text=True,
            capture_output=True,
        )


def _print_failure(step: str, exc: subprocess.CalledProcessError) -> None:
    """Print details of a failed git subprocess."""
    stderr = (exc.stderr or "").strip()
    stdout = (exc.stdout or "").strip()
    if stderr:
        print(f"\n--- git stderr ---\n{stderr}", file=sys.stderr)
    if stdout:
        print(f"\n--- git stdout ---\n{stdout}", file=sys.stderr)
    print(f"\nfailed at step: {step}\n", file=sys.stderr)


if __name__ == "__main__":
    main()
