"""``timestamp-offset`` - print the timestamp N days from now."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="timestamp-offset",
        description="Print the millisecond timestamp N days from now.",
    )
    parser.add_argument("days", type=int, help="day offset from now (negative allowed)")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        now = datetime.now()
        target = now + timedelta(days=args.days)
        timestamp = int(target.timestamp() * 1000)
    except OverflowError:
        log.error("offset %s days is out of range", args.days)
        sys.exit(1)

    formatted = target.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
    print(f"Days offset: {args.days:+d}")
    print(f"Target time: {formatted}")
    print(f"Timestamp:   {timestamp}")


if __name__ == "__main__":
    main()
