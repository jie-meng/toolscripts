"""``brew-upgrade`` - update, upgrade and clean up Homebrew packages.

Requires the ``brew`` binary on PATH (macOS / Linux only). Runs
``brew update``, ``brew upgrade`` then ``brew cleanup``, echoing each command
as it runs, and pipes ``yes`` into each so any interactive ``y/n`` prompt is
answered automatically — no keyboard input needed.
"""

from __future__ import annotations

import argparse

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.platform import require_platform
from toolscripts.core.shell import capture, require, run

log = get_logger(__name__)


def main() -> None:
    require_platform("macos", "linux")
    require("brew")

    parser = argparse.ArgumentParser(
        prog="brew-upgrade",
        description="Run ``brew update``, ``brew upgrade`` and ``brew cleanup`` and auto-answer any y/n prompts.",
    )
    parser.add_argument(
        "--no-output",
        action="store_true",
        help="suppress brew's own output; only show the commands being run and status messages",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    # `yes |` feeds an endless stream of "y" to brew's stdin via bash, so any
    # prompt is confirmed without user input.
    action_commands = [
        "yes | brew update",
        "yes | brew upgrade",
        "yes | brew cleanup",
    ]
    for cmd in action_commands:
        log.info("$ %s", cmd)
        if args.no_output:
            capture(["bash", "-c", cmd])
        else:
            run(["bash", "-c", cmd])

    log.success("brew is up to date and cleaned up")


if __name__ == "__main__":
    main()
