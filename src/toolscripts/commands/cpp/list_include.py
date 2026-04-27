"""``list-include-dirs-from-here`` and ``list-include-dirs-clang``."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import CommandNotFoundError, require

log = get_logger(__name__)


def _walk_includes(start: Path) -> list[Path]:
    result: list[Path] = []
    for entry in start.iterdir():
        if not entry.is_dir():
            continue
        if entry.name == "include":
            result.append(entry)
        else:
            result.extend(_walk_includes(entry))
    return result


def from_here_main() -> None:
    parser = argparse.ArgumentParser(
        prog="list-include-dirs-from-here",
        description="Recursively list directories named 'include' under the given path.",
    )
    parser.add_argument(
        "directory", nargs="?", default=".", help="root directory (default: cwd)"
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    root = Path(args.directory).expanduser().resolve()
    if not root.is_dir():
        log.error("not a directory: %s", root)
        sys.exit(1)
    for path in _walk_includes(root):
        print(path)


def clang_main() -> None:
    parser = argparse.ArgumentParser(
        prog="list-include-dirs-clang",
        description="Print the include search path used by clang++ for an empty C++ TU.",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        require("clang++")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)
    res = subprocess.run(
        ["clang++", "-E", "-x", "c++", "-", "-v"],
        input="",
        text=True,
        capture_output=True,
    )
    sys.stderr.write(res.stderr)
    if res.stdout:
        sys.stdout.write(res.stdout)
    sys.exit(res.returncode)


if __name__ == "__main__":
    from_here_main()
