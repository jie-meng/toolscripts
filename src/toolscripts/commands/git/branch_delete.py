"""``git-branch-delete`` - interactively delete local/remote git branches."""

from __future__ import annotations

import argparse
import subprocess
import sys

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import CommandNotFoundError, capture, require, run
from toolscripts.core.ui_curses import select_many, select_one

log = get_logger(__name__)

_MENU = [
    "Fetch and prune remote branches",
    "Delete local branches",
    "Delete remote branches",
]


def _list_local_branches() -> list[str]:
    out = capture(["git", "branch"], check=False)
    branches = []
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("* "):
            continue  # skip current branch — cannot delete it
        if line:
            branches.append(line)
    return branches


def _list_remote_branches() -> list[str]:
    out = capture(["git", "branch", "-r"], check=False)
    branches = []
    for line in out.splitlines():
        line = line.strip()
        if line and "->" not in line:
            branches.append(line)
    return branches


def _fetch_and_prune() -> None:
    log.info("Fetching and pruning remote branches...")
    run(["git", "fetch", "-p"], check=False)
    log.success("fetch and prune completed")


def _delete_local() -> None:
    branches = _list_local_branches()
    if not branches:
        log.warning("no deletable local branches found")
        return

    chosen = select_many("Select local branches to delete:", branches)
    if not chosen:
        return

    targets = [branches[i] for i in chosen]
    successes: list[str] = []
    failures: list[tuple[str, str]] = []

    for b in targets:
        try:
            capture(["git", "branch", "-d", b])
            successes.append(b)
        except subprocess.CalledProcessError as exc:
            failures.append((b, exc.stderr.strip() or "unknown error"))

    log.info("total: %d, deleted: %d, failed: %d", len(targets), len(successes), len(failures))
    if not failures:
        return

    log.warning("the following branches have unmerged commits:")
    for name, _ in failures:
        print(f"  {name}")

    force_chosen = select_many(
        "Select branches to FORCE delete (git branch -D):",
        [name for name, _ in failures],
    )
    if not force_chosen:
        return

    fail_names = [name for name, _ in failures]
    for i in force_chosen:
        b = fail_names[i]
        try:
            capture(["git", "branch", "-D", b])
            log.success("force deleted %s", b)
        except subprocess.CalledProcessError as exc:
            log.error("failed to force delete %s: %s", b, exc.stderr.strip())


def _delete_remote() -> None:
    branches = _list_remote_branches()
    if not branches:
        log.warning("no remote branches found")
        return

    chosen = select_many("Select remote branches to delete:", branches)
    if not chosen:
        return

    targets = [branches[i] for i in chosen]
    successes: list[str] = []
    failures: list[tuple[str, str]] = []

    for b in targets:
        parts = b.split("/", 1)
        remote, short = (parts[0], parts[1]) if len(parts) == 2 else ("origin", parts[0])
        try:
            capture(["git", "push", "--delete", remote, short])
            successes.append(b)
        except subprocess.CalledProcessError as exc:
            err_msg = (exc.stderr or "unknown error").strip()
            failures.append((b, err_msg))

    log.info("total: %d, deleted: %d, failed: %d", len(targets), len(successes), len(failures))
    if failures:
        log.warning("failed remote branches:")
        for name, err in failures:
            indent = "    "
            err_lines = err.splitlines()
            print(f"  {name}:")
            for line in err_lines:
                print(f"{indent}{line}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="git-branch-delete",
        description="Interactive helper to fetch/prune and delete branches.",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        require("git")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)

    while True:
        idx = select_one("git-branch-delete — Select an operation:", _MENU)
        if idx is None:
            return
        print()
        if idx == 0:
            _fetch_and_prune()
        elif idx == 1:
            _delete_local()
        elif idx == 2:
            _delete_remote()
        print("-" * 28)
        try:
            input("Press Enter to return to menu…")
        except (EOFError, KeyboardInterrupt):
            print()
            return


if __name__ == "__main__":
    main()
