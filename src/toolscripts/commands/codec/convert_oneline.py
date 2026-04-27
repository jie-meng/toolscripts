"""``convert-oneline`` - join all lines of a file into a single line and copy it."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from toolscripts.core.clipboard import copy_to_clipboard
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="convert-oneline",
        description="Read a file, join all lines into a single line, print and copy it.",
    )
    parser.add_argument("file", help="path to the file")
    parser.add_argument(
        "--no-copy", action="store_true", help="print only; do not touch clipboard"
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    path = Path(args.file).expanduser()
    if not path.is_file():
        log.error("file not found: %s", path)
        sys.exit(1)

    content = path.read_text(encoding="utf-8")
    oneline = "".join(content.splitlines())

    sys.stdout.write(oneline)
    sys.stdout.write("\n")

    if args.no_copy:
        return
    if copy_to_clipboard(oneline):
        log.success("copied to clipboard")
    else:
        log.warning("could not copy to clipboard")


if __name__ == "__main__":
    main()
