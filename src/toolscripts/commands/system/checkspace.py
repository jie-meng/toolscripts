"""``checkspace`` - sort top-level entries in a directory by size."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)

_UNITS = {
    "b": 1,
    "k": 1024,
    "m": 1024 ** 2,
    "g": 1024 ** 3,
    "t": 1024 ** 4,
}


def _dir_size(path: Path) -> int:
    total = 0
    for root, _dirs, files in os.walk(path):
        for fname in files:
            try:
                total += (Path(root) / fname).stat().st_size
            except OSError:
                continue
    return total


def _entry_size(path: Path) -> int:
    try:
        if path.is_dir():
            return _dir_size(path)
        return path.stat().st_size
    except OSError:
        return 0


def _format(size: int, *, unit: str) -> str:
    factor = _UNITS[unit]
    return f"{size / factor:.2f}{unit.upper()}"


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="checkspace",
        description="List top-level entries of a directory sorted by size.",
    )
    parser.add_argument("directory", nargs="?", default=".", help="directory (default: cwd)")
    parser.add_argument(
        "-u",
        "--unit",
        choices=("b", "k", "m", "g", "t"),
        default="m",
        help="unit (default: m)",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    directory = Path(args.directory).expanduser().resolve()
    if not directory.is_dir():
        log.error("not a directory: %s", directory)
        sys.exit(1)

    entries = sorted(
        ((entry, _entry_size(entry)) for entry in directory.iterdir()),
        key=lambda item: item[1],
        reverse=True,
    )
    for entry, size in entries:
        print(f"{_format(size, unit=args.unit):>12}  {entry.name}")


if __name__ == "__main__":
    main()
