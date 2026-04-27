"""``ios-log`` - tail the iOS simulator log filtered by a substring."""

from __future__ import annotations

import argparse
import subprocess
import sys

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.platform import require_platform
from toolscripts.core.shell import CommandNotFoundError, require

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ios-log",
        description="Tail logs from the booted iOS simulator, grep-filtered by a pattern.",
    )
    parser.add_argument("pattern", help="filter substring passed to grep")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    require_platform("macos")
    try:
        require("xcrun")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)

    log_proc = subprocess.Popen(
        [
            "xcrun", "simctl", "spawn", "booted",
            "log", "stream", "--level", "debug", "--style", "compact",
        ],
        stdout=subprocess.PIPE,
    )
    grep_proc = subprocess.Popen(
        ["grep", "--line-buffered", args.pattern],
        stdin=log_proc.stdout,
    )
    if log_proc.stdout is not None:
        log_proc.stdout.close()

    try:
        grep_proc.wait()
    except KeyboardInterrupt:
        grep_proc.terminate()
        log_proc.terminate()
        print()


if __name__ == "__main__":
    main()
