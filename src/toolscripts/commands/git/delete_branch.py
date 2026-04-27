"""``git-delete-branch`` - interactively delete local/remote git branches by prefix."""

from __future__ import annotations

import argparse
import subprocess

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)


def _run(args: list[str]) -> tuple[str, str, int]:
    result = subprocess.run(args, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def _list_branches(args: list[str]) -> list[str]:
    out, _, _ = _run(args)
    return [line.strip().lstrip("* ").strip() for line in out.splitlines() if line.strip()]


def _fetch_and_prune() -> None:
    log.info("Fetching and pruning remote branches...")
    out, err, _ = _run(["git", "fetch", "-p"])
    if err:
        log.error("error during fetch: %s", err)
    if out:
        print(out)
    log.success("fetch and prune completed")


def _delete_local() -> None:
    while True:
        branches = _list_branches(["git", "branch"])
        print("\nLocal branches:")
        for b in branches:
            print(b)

        print("\n1. Refresh branch list")
        print("2. Enter prefix to delete branches")
        print("0. Return to main menu")
        choice = input("Enter your choice: ").strip()
        if choice == "0":
            return
        if choice == "1":
            continue
        if choice != "2":
            continue

        prefix = input("Enter the prefix of branches to delete: ").strip()
        if not prefix:
            log.warning("no prefix entered")
            continue
        targets = [b for b in branches if b.startswith(prefix)]
        if not targets:
            log.warning("no branches found with prefix %r", prefix)
            continue

        successes: list[str] = []
        failures: list[tuple[str, str]] = []
        for b in targets:
            _, err, rc = _run(["git", "branch", "-d", b])
            if rc == 0:
                successes.append(b)
            else:
                failures.append((b, err or "unknown error"))

        log.info("total: %d, deleted: %d, failed: %d", len(targets), len(successes), len(failures))
        if failures:
            log.warning("failed branches:")
            for name, err in failures:
                print(f"  {name}: {err}")
            retry = input("Force delete the failed branches? (y/N): ").strip().lower()
            if retry == "y":
                for name, _ in failures:
                    _, err, rc = _run(["git", "branch", "-D", name])
                    if rc == 0:
                        log.success("force deleted %s", name)
                    else:
                        log.error("failed to force delete %s: %s", name, err)


def _delete_remote() -> None:
    while True:
        branches = _list_branches(["git", "branch", "-r"])
        print("\nRemote branches:")
        for b in branches:
            print(b)

        print("\n1. Refresh branch list")
        print("2. Enter prefix to delete remote branches")
        print("0. Return to main menu")
        choice = input("Enter your choice: ").strip()
        if choice == "0":
            return
        if choice == "1":
            continue
        if choice != "2":
            continue

        prefix = input("Enter the prefix of remote branches to delete: ").strip()
        if not prefix:
            log.warning("no prefix entered")
            continue
        targets = [b for b in branches if b.startswith(prefix)]
        if not targets:
            log.warning("no remote branches found with prefix %r", prefix)
            continue

        successes: list[str] = []
        failures: list[tuple[str, str]] = []
        for b in targets:
            short = b.split("/", 1)[-1]
            _, err, rc = _run(["git", "push", "--delete", "origin", short])
            if rc == 0:
                successes.append(b)
            else:
                failures.append((b, err or "unknown error"))

        log.info("total: %d, deleted: %d, failed: %d", len(targets), len(successes), len(failures))
        if failures:
            log.warning("failed remote branches:")
            for name, err in failures:
                print(f"  {name}: {err}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="git-delete-branch",
        description="Interactive helper to fetch/prune and delete branches by prefix.",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    while True:
        print("\nGit Branch Manager")
        print("1. Fetch and prune remote branches")
        print("2. Delete local branches by prefix")
        print("3. Delete remote branches by prefix")
        print("0. Exit")
        try:
            choice = input("Enter your choice: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if choice == "1":
            _fetch_and_prune()
        elif choice == "2":
            _delete_local()
        elif choice == "3":
            _delete_remote()
        elif choice == "0":
            return
        else:
            log.warning("invalid choice")


if __name__ == "__main__":
    main()
