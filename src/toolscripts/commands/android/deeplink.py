"""``android-deeplink`` - launch a deeplink URL on a connected Android device."""

from __future__ import annotations

import argparse
import sys

from toolscripts.adb.devices import select_device
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.prompts import ask
from toolscripts.core.shell import run

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="android-deeplink",
        description="Launch a deeplink URL on a connected Android device.",
    )
    parser.add_argument("url", nargs="?", help="deeplink URL (prompted if omitted)")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    device = select_device()
    url = (args.url or ask("Enter the deeplink URL") or "").strip()
    if not url:
        log.error("no deeplink entered")
        sys.exit(1)

    cmd = ["adb", "-s", device, "shell", "am", "start", "-d", url]
    log.info("running: %s", " ".join(cmd))
    try:
        run(cmd)
        log.success("deeplink launched")
    except Exception as exc:  # noqa: BLE001
        log.error("failed to launch deeplink: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
