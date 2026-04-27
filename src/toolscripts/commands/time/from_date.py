"""``date2timestamp`` - convert a date string to a millisecond timestamp."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)

_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"


def convert(date_str: str) -> int:
    """Parse ``YYYY-MM-DDTHH:MM:SS.fff`` and return milliseconds since epoch."""
    dt = datetime.strptime(date_str, _FORMAT)
    return int(dt.timestamp() * 1000)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="date2timestamp",
        description=(
            "Convert a local date-time string (YYYY-MM-DDTHH:MM:SS.fff) "
            "to a millisecond timestamp."
        ),
    )
    parser.add_argument("date", help="date string in the format YYYY-MM-DDTHH:MM:SS.fff")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        ts = convert(args.date)
    except ValueError as exc:
        log.error("could not parse date %r: %s", args.date, exc)
        sys.exit(1)

    print(ts)


if __name__ == "__main__":
    main()
