"""``timestamp-now`` - print the current millisecond timestamp."""

from __future__ import annotations

import argparse
from datetime import datetime

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="timestamp-now",
        description="Print the current local time and its millisecond timestamp.",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    now = datetime.now()
    timestamp = int(now.timestamp() * 1000)
    formatted = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]

    log.debug("now=%s timestamp=%s", formatted, timestamp)
    print(f"Current time: {formatted}")
    print(f"Timestamp:    {timestamp}")


if __name__ == "__main__":
    main()
