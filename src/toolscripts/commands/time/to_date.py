"""``timestamp2date`` - convert a millisecond timestamp to a date string."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)


def convert(milliseconds: int | str) -> str:
    """Convert ``milliseconds`` since epoch to ``YYYY-MM-DDTHH:MM:SS.fff``."""
    ms = int(milliseconds)
    seconds = ms // 1000
    micros = (ms % 1000) * 1000
    dt = datetime.fromtimestamp(seconds) + timedelta(microseconds=micros)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="timestamp2date",
        description="Convert a millisecond timestamp to a local date-time string.",
    )
    parser.add_argument("milliseconds", help="millisecond unix timestamp")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        result = convert(args.milliseconds)
    except ValueError:
        log.error("not a valid integer timestamp: %r", args.milliseconds)
        sys.exit(1)

    print(result)


if __name__ == "__main__":
    main()
