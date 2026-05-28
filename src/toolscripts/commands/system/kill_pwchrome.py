"""``kill-pwchrome`` - kill Playwright-launched Chrome/Chromium processes.

Only affects Chrome/Chromium instances started by Playwright (e.g. via
``playwright-mcp``), leaving your regular Chrome untouched.
"""

from __future__ import annotations

import argparse
import os
import signal

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.platform import require_platform
from toolscripts.core.prompts import yes_no
from toolscripts.core.shell import capture

log = get_logger(__name__)


def _find_playwright_chrome() -> list[tuple[str, str]]:
    """Return (pid, args) for every Playwright-launched Chrome/Chromium process."""
    output = capture(["ps", "-eo", "pid,args"], strip=False)
    matches: list[tuple[str, str]] = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) < 2:
            continue
        pid, args = parts
        if "Google Chrome" not in args and "Chromium" not in args:
            continue
        if "ms-playwright" not in args and "--remote-debugging-pipe" not in args:
            continue
        matches.append((pid, args))
    return matches


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="kill-pwchrome",
        description="Kill Playwright-launched Chrome/Chromium processes.",
    )
    parser.add_argument("-y", "--yes", action="store_true", help="kill without prompting")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    require_platform("macos")

    processes = _find_playwright_chrome()
    if not processes:
        log.info("no Playwright Chrome processes found")
        return

    log.info("found %d Playwright Chrome process(es):", len(processes))
    for pid, cmd in processes:
        short = cmd if len(cmd) < 120 else cmd[:117] + "..."
        print(f"  PID {pid:<7} {short}")

    if not args.yes and not yes_no("kill these processes?", default=False):
        log.info("cancelled")
        return

    for pid, _ in processes:
        try:
            os.kill(int(pid), signal.SIGTERM)
        except ProcessLookupError:
            log.warning("process %s already exited", pid)
        except PermissionError:
            log.error("permission denied to kill PID %s", pid)

    log.success("sent SIGTERM to %d process(es)", len(processes))


if __name__ == "__main__":
    main()
