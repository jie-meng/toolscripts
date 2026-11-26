"""Running Android emulators: find the one started from an AVD, and stop it.

from toolscripts.adb import find_emulator_serial, kill_emulator

serial = find_emulator_serial("Pixel_9")  # "emulator-5554", or None when not running
if serial:
    kill_emulator(serial)                  # waits until adb no longer lists it
"""

from __future__ import annotations

import time

from toolscripts.adb.devices import list_devices
from toolscripts.core.log import get_logger
from toolscripts.core.shell import capture, try_run

log = get_logger(__name__)

KILL_TIMEOUT_S = 30
POLL_S = 1


def find_emulator_serial(avd: str) -> str | None:
    """Return the serial of the running emulator started from ``avd``, or None."""
    for serial in list_devices():
        if not serial.startswith("emulator-"):
            continue
        output = capture(["adb", "-s", serial, "emu", "avd", "name"], check=False)
        name = next((line.strip() for line in output.splitlines() if line.strip()), "")
        if name == avd:
            return serial
    return None


def kill_emulator(serial: str, *, timeout_s: float = KILL_TIMEOUT_S) -> bool:
    """Stop the emulator ``serial`` and wait until adb no longer lists it. Returns False on timeout."""
    try_run(["adb", "-s", serial, "emu", "kill"])
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if serial not in list_devices():
            return True
        time.sleep(POLL_S)
    log.warning("%s still listed by adb after %ss", serial, timeout_s)
    return False
