"""``brew-upgrade`` - update, upgrade and clean up Homebrew packages.

Requires the ``brew`` binary on PATH (macOS / Linux only). Runs
``brew update``, ``brew upgrade`` then ``brew cleanup``, echoing each command
as it runs. Stdin is redirected from ``/dev/null`` so brew runs
non-interactively: its y/n confirmation prompt is skipped when stdin is not a
TTY, so no keyboard input is needed and no ``yes``-spam reaches the terminal.
"""

from __future__ import annotations

import argparse
import subprocess
import sys

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.platform import require_platform
from toolscripts.core.shell import capture, require, run

log = get_logger(__name__)


def main() -> None:
    require_platform("macos", "linux")
    require("brew")

    parser = argparse.ArgumentParser(
        prog="brew-upgrade",
        description="Run ``brew update``, ``brew upgrade`` and ``brew cleanup`` non-interactively (skips brew's y/n prompt).",
    )
    parser.add_argument(
        "--no-output",
        action="store_true",
        help="suppress brew's own output; only show the commands being run and status messages",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    # Redirect stdin from /dev/null so brew runs non-interactively: its y/n
    # confirmation prompt is skipped when stdin is not a TTY. Piping `yes |`
    # instead would flood the terminal with "y" lines — brew's sandbox copies
    # all of stdin into a PTY during installs and the PTY echoes every byte.
    action_commands = [
        "brew update </dev/null",
        "brew upgrade </dev/null",
        "brew cleanup </dev/null",
    ]
    failures: list[str] = []
    for cmd in action_commands:
        log.info("$ %s", cmd)
        try:
            if args.no_output:
                capture(["bash", "-c", cmd])
            else:
                run(["bash", "-c", cmd])
        except subprocess.CalledProcessError as exc:
            # brew can exit non-zero even after doing useful work (e.g. one
            # cask fails to upgrade while 10 formulae succeed). Keep going so
            # cleanup still runs, then report the failed steps at the end.
            log.warning("%s exited with status %d", cmd, exc.returncode)
            failures.append(cmd)

    if failures:
        log.error("failed steps: %s", ", ".join(failures))
        sys.exit(1)

    log.success("brew is up to date and cleaned up")


if __name__ == "__main__":
    main()
