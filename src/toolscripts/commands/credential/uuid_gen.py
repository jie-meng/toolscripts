"""``uuid`` - generate a random UUID4 and copy it to the clipboard."""

from __future__ import annotations

import argparse
import uuid

from toolscripts.core.clipboard import copy_to_clipboard
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="uuid",
        description="Generate a random UUID4 and copy it to the clipboard.",
    )
    parser.add_argument(
        "-n", "--count", type=int, default=1, help="number of UUIDs to generate (default: 1)"
    )
    parser.add_argument(
        "--no-copy", action="store_true", help="print only, do not touch the clipboard"
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    count = max(1, args.count)
    values = [str(uuid.uuid4()) for _ in range(count)]
    for v in values:
        print(v)

    if args.no_copy:
        return

    text = "\n".join(values)
    if copy_to_clipboard(text):
        log.success("copied %d UUID%s to clipboard", count, "" if count == 1 else "s")
    else:
        log.warning("could not copy to clipboard (clipboard tools not available)")


if __name__ == "__main__":
    main()
