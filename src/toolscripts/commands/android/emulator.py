"""``android-emulator`` - list available AVDs and start the chosen one."""

from __future__ import annotations

import argparse
import sys

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.prompts import choice, yes_no
from toolscripts.core.shell import CommandNotFoundError, capture, require, run

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="android-emulator",
        description="List Android emulator AVDs and launch the chosen one.",
    )
    parser.add_argument(
        "--writable-system",
        action="store_true",
        help="start with -writable-system (skip prompt)",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        require("emulator")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        log.warning("install Android SDK platform-tools / emulator")
        sys.exit(1)

    output = capture(["emulator", "-list-avds"], check=False)
    avds = [line.strip() for line in output.splitlines() if line.strip() and "INFO" not in line]
    if not avds:
        log.warning("no emulator AVDs configured")
        return

    idx = choice("Please select emulator", avds, default=0)
    if idx is None:
        return
    avd = avds[idx]
    log.info("%s selected", avd)

    if args.writable_system:
        ws = True
    else:
        ws = yes_no("start with -writable-system?", default=False)

    cmd = ["emulator", "-avd", avd]
    if ws:
        cmd.append("-writable-system")
    run(cmd, check=False)


if __name__ == "__main__":
    main()
