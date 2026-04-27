"""``android-adbsync`` - remount the device, sync, and restart the framework."""

from __future__ import annotations

import argparse

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import run

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="android-adbsync",
        description="Remount, sync, and restart the device framework via adb.",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    for cmd in (
        ["adb", "remount"],
        ["adb", "sync"],
        ["adb", "shell", "stop"],
        ["adb", "shell", "start"],
    ):
        log.info("running: %s", " ".join(cmd))
        run(cmd, check=False)


if __name__ == "__main__":
    main()
