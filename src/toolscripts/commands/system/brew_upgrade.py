"""``brew-upgrade`` - update, upgrade and clean up Homebrew packages.

Requires the ``brew`` binary on PATH (macOS / Linux only). Runs
``brew update && brew upgrade && brew cleanup`` and pipes ``yes`` into each so
any interactive ``y/n`` prompt is answered automatically — no keyboard input
needed.
"""

from __future__ import annotations

import argparse

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.platform import require_platform
from toolscripts.core.shell import require, run

log = get_logger(__name__)


def main() -> None:
    require_platform("macos", "linux")
    require("brew")

    parser = argparse.ArgumentParser(
        prog="brew-upgrade",
        description="Run ``brew update && brew upgrade && brew cleanup`` and auto-answer any y/n prompts.",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    log.info("running: brew update && brew upgrade && brew cleanup (auto-answering y)")

    # `yes |` feeds an endless stream of "y" to brew's stdin, so any prompt is
    # confirmed without user input. Output still streams through to the terminal.
    run(["bash", "-c", "yes | brew update && yes | brew upgrade && yes | brew cleanup"])

    log.success("brew is up to date and cleaned up")


if __name__ == "__main__":
    main()
