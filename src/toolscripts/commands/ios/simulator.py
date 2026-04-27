"""``ios-simulator`` - list iOS simulators and boot/open the chosen one."""

from __future__ import annotations

import argparse
import re
import sys

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.platform import require_platform
from toolscripts.core.shell import CommandNotFoundError, capture, require, run

log = get_logger(__name__)


def _list_devices() -> list[tuple[str, str, str, str]]:
    output = capture(["xcrun", "simctl", "list", "devices"], check=False)
    current_ios = ""
    devices: list[tuple[str, str, str, str]] = []
    for raw in output.splitlines():
        line = raw.strip()
        if line.startswith("--"):
            current_ios = line.strip("- ")
            continue
        if "(" not in line or ")" not in line:
            continue
        name = line.split("(")[0].strip()
        match = re.search(r"\(([^)]+)\)", line)
        if not match:
            continue
        uuid = match.group(1)
        status = "Booted" if "Booted" in line else "Shutdown"
        devices.append((name, uuid, status, current_ios))
    devices.sort(key=lambda d: (d[2] != "Booted", d[3], d[0]))
    return devices


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ios-simulator",
        description="List iOS simulators and boot/open the selected one.",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    require_platform("macos")
    try:
        require("xcrun")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)

    devices = _list_devices()
    if not devices:
        log.warning("no simulators found")
        return

    print("Available devices:")
    for i, (name, _uuid, status, ios) in enumerate(devices, 1):
        print(f"{i}. {name} ({ios}) - {status}")
    print("0. Shutdown all devices")

    try:
        raw = input("Enter the number of the device to boot/open (or 0 to shutdown all): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if raw == "0":
        run(["xcrun", "simctl", "shutdown", "all"])
        log.success("all simulators have been shut down")
        return

    if not raw.isdigit() or not 1 <= int(raw) <= len(devices):
        log.error("invalid choice")
        return

    name, uuid, status, _ = devices[int(raw) - 1]
    if status == "Booted":
        run(["open", "-a", "Simulator"])
        log.info("opening Simulator for %s", name)
    else:
        run(["open", "-a", "Simulator", "--args", "-CurrentDeviceUDID", uuid])
        log.info("booting and opening Simulator for %s", name)


if __name__ == "__main__":
    main()
