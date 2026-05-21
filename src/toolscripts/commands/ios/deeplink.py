"""``ios-deeplink`` - launch a deeplink URL on a booted iOS simulator.

Requires macOS and `xcrun`.
"""

from __future__ import annotations

import argparse
import sys

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.platform import require_platform
from toolscripts.core.prompts import ask
from toolscripts.core.shell import require, run

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ios-deeplink",
        description="Launch a deeplink URL on a booted iOS simulator.",
    )
    parser.add_argument("url", nargs="?", help="deeplink URL (prompted if omitted)")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    require_platform("macos")
    require("xcrun")

    url = (args.url or ask("Enter the deeplink URL") or "").strip()
    if not url:
        log.error("no deeplink entered")
        sys.exit(1)

    cmd = ["xcrun", "simctl", "openurl", "booted", url]
    cmd_str = " ".join(cmd)
    log.info("%s", cmd_str)
    try:
        run(cmd)
        log.success("deeplink launched")
    except Exception as exc:  # noqa: BLE001
        log.error("failed to launch deeplink: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
