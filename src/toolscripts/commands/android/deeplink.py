"""``android-deeplink`` - launch a deeplink URL on a connected device.

Supports Android (adb am start) and iOS simulator (xcrun simctl openurl).
"""

from __future__ import annotations

import argparse
import sys

from toolscripts.adb.devices import select_device
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.platform import require_platform
from toolscripts.core.prompts import ask
from toolscripts.core.shell import require, run

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="android-deeplink",
        description="Launch a deeplink URL on a connected Android device or iOS simulator.",
    )
    parser.add_argument("url", nargs="?", help="deeplink URL (prompted if omitted)")
    parser.add_argument(
        "--ios",
        "-i",
        action="store_true",
        help="use iOS simulator via `xcrun simctl openurl booted <url>`",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    url = (args.url or ask("Enter the deeplink URL") or "").strip()
    if not url:
        log.error("no deeplink entered")
        sys.exit(1)

    if args.ios:
        require_platform("macos")
        require("xcrun")
        cmd = ["xcrun", "simctl", "openurl", "booted", url]
    else:
        device = select_device()
        cmd = ["adb", "-s", device, "shell", "am", "start", "-d", url]

    cmd_str = " ".join(cmd)
    log.info("%s", cmd_str)
    try:
        run(cmd)
        log.success("deeplink launched")
        log.info("%s", cmd_str)
    except Exception as exc:  # noqa: BLE001
        log.error("failed to launch deeplink: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
