"""``git-delete-local-branches`` - delete all non-current local branches."""

from __future__ import annotations

import argparse
import subprocess
import sys

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.prompts import yes_no

log = get_logger(__name__)


def _run(args: list[str]) -> tuple[str, str, int]:
    result = subprocess.run(args, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="git-delete-local-branches",
        description="Delete all local branches except the currently checked out one.",
    )
    parser.add_argument("-f", "--force", action="store_true", help="use git branch -D")
    parser.add_argument("-y", "--yes", action="store_true", help="skip confirmation")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    out, _, rc = _run(["git", "branch", "--show-current"])
    if rc != 0 or not out:
        log.error("not a git repository or detached HEAD")
        sys.exit(1)
    current = out.strip()

    out, _, _ = _run(["git", "branch"])
    branches = [
        line.strip().lstrip("* ").strip()
        for line in out.splitlines()
        if line.strip() and current not in line.strip()
    ]
    branches = [b for b in branches if b and b != current]
    if not branches:
        log.info("no other local branches found")
        return

    print("The following branches will be deleted:")
    for b in branches:
        print(f"  {b}")

    if not args.yes and not yes_no("\nContinue with deletion?", default=False):
        log.warning("deletion cancelled")
        return

    if not args.force and not args.yes:
        force = yes_no("Force delete branches?", default=False)
    else:
        force = args.force

    flag = "-D" if force else "-d"
    for b in branches:
        _, err, rc = _run(["git", "branch", flag, b])
        if rc == 0:
            log.success("deleted %s", b)
        else:
            log.error("failed to delete %s: %s", b, err)


if __name__ == "__main__":
    main()
