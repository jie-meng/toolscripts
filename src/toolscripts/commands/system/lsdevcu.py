"""``lsdevcu`` - list ``/dev/cu.*`` serial devices (macOS/Linux)."""

from __future__ import annotations

import argparse
import glob
import sys

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.platform import is_windows

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="lsdevcu",
        description="List /dev/cu.* serial devices (macOS).",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    if is_windows():
        log.warning("/dev/cu.* devices are not available on Windows; use Device Manager instead.")
        sys.exit(0)

    matches = glob.glob("/dev/cu.*")
    if not matches:
        log.info("no /dev/cu.* devices found")
        return
    for path in sorted(matches):
        print(path)


if __name__ == "__main__":
    main()
