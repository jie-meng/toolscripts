"""``android-screencast`` - launch scrcpy for the selected device."""

from __future__ import annotations

import argparse
import sys

from toolscripts.adb.devices import select_device
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import CommandNotFoundError, require, run

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="android-screencast",
        description="Launch scrcpy for the selected Android device.",
    )
    parser.add_argument("extra", nargs=argparse.REMAINDER, help="extra args forwarded to scrcpy")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        require("scrcpy")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        log.warning("install scrcpy: https://github.com/Genymobile/scrcpy")
        sys.exit(1)

    device = select_device()
    log.info("launching scrcpy for %s...", device)
    cmd = ["scrcpy", "-s", device, *args.extra]
    try:
        run(cmd)
    except Exception as exc:  # noqa: BLE001
        log.error("scrcpy failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
