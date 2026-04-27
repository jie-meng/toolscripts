"""``android-studio`` - open the current directory in Android Studio (macOS)."""

from __future__ import annotations

import argparse

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.platform import require_platform
from toolscripts.core.shell import run

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="android-studio",
        description="Open the current directory in Android Studio (macOS).",
    )
    parser.add_argument("path", nargs="?", default=".", help="directory to open (default: .)")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    require_platform("macos")
    log.info("opening %s in Android Studio", args.path)
    run(["open", "-b", "com.google.android.studio", args.path], check=False)


if __name__ == "__main__":
    main()
