"""``dirdiff`` - launch Vim's ``DirDiff`` on two directories."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import CommandNotFoundError, require, run

log = get_logger(__name__)


def _ask_directory(prompt: str) -> Path:
    try:
        raw = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(130)
    return Path(raw).expanduser()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="dirdiff",
        description="Launch Vim's DirDiff on two directories.",
    )
    parser.add_argument("dir1", nargs="?", help="first directory")
    parser.add_argument("dir2", nargs="?", help="second directory")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        require("vim")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)

    dir1 = Path(args.dir1).expanduser() if args.dir1 else _ask_directory("Enter the first directory: ")
    dir2 = Path(args.dir2).expanduser() if args.dir2 else _ask_directory("Enter the second directory: ")

    for d in (dir1, dir2):
        if not d.is_dir():
            log.error("not a directory: %s", d)
            sys.exit(1)

    run(["vim", "-c", f"DirDiff {dir1} {dir2}"])


if __name__ == "__main__":
    main()
