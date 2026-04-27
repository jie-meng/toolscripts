"""ADB device discovery and selection.

Used by every ``android-*`` command. Wraps ``adb devices`` and exposes a
small API:

    from toolscripts.adb import select_device, list_devices

    serial = select_device()        # may prompt the user
    serials = list_devices()        # returns all serials, no prompt
"""

from __future__ import annotations

import sys

from toolscripts.core import prompts
from toolscripts.core.log import get_logger
from toolscripts.core.shell import (
    CommandNotFoundError,
    capture,
    require,
)

log = get_logger(__name__)


def list_devices() -> list[str]:
    """Return the serials of all currently connected ADB devices."""
    try:
        require("adb")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)

    output = capture(["adb", "devices"], check=False)
    devices: list[str] = []
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("List of devices"):
            continue
        if "\t" not in line:
            continue
        serial, status = line.split("\t", 1)
        if status.strip() == "device":
            devices.append(serial)
    log.debug("found devices: %s", devices)
    return devices


def select_device(*, prompt: str = "Please select device") -> str:
    """Return a single connected device serial, prompting the user if needed.

    Exits the process with a clear error if no devices are connected or the
    user cancels selection.
    """
    devices = list_devices()
    if not devices:
        log.error("no Android devices connected; check `adb devices`")
        sys.exit(1)

    if len(devices) == 1:
        log.debug("single device, auto-selected: %s", devices[0])
        return devices[0]

    idx = prompts.choice(prompt, devices, default=0)
    if idx is None:
        log.error("no device selected")
        sys.exit(1)
    return devices[idx]
