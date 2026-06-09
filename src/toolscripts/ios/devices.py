"""iOS device discovery and selection.

Used by ``ios-*`` commands. Wraps ``xcrun simctl`` and ``xcrun devicectl`` to
discover simulators and physical devices.

Usage::

    from toolscripts.ios.devices import select_device, list_devices, get_device_name

    device = select_device()        # may prompt the user
    devices = list_devices()        # returns all devices, no prompt
    name = get_device_name(device)  # human-readable device name
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass

from toolscripts.core.log import get_logger
from toolscripts.core.shell import CommandNotFoundError, capture, require
from toolscripts.core.ui_curses import select_one

log = get_logger(__name__)


@dataclass
class IOSDevice:
    """Represents an iOS device (simulator or physical)."""

    identifier: str  # UUID for simulators, UDID for physical devices
    name: str
    type: str  # "simulator" or "device"
    os_version: str = ""
    model: str = ""
    state: str = ""  # for simulators: "Shutdown", "Booted", etc.


def list_simulators(*, booted_only: bool = True) -> list[IOSDevice]:
    """Return available iOS simulators.

    Args:
        booted_only: If True (default), only return simulators that are currently booted.
    """
    try:
        require("xcrun")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)

    try:
        output = capture(
            ["xcrun", "simctl", "list", "devices", "--json"],
            check=False,
        )
        data = json.loads(output)
        devices = []
        for runtime, runtime_devices in data.get("devices", {}).items():
            for dev in runtime_devices:
                state = dev.get("state", "Unknown")
                if booted_only and state != "Booted":
                    continue
                devices.append(
                    IOSDevice(
                        identifier=dev["udid"],
                        name=dev["name"],
                        type="simulator",
                        os_version=runtime.split(".")[-1] if "." in runtime else "",
                        state=state,
                    )
                )
        log.debug("found %d simulators", len(devices))
        return devices
    except Exception as e:
        log.warning("failed to list simulators: %s", e)
        return []


def list_physical_devices(*, available_only: bool = False) -> list[IOSDevice]:
    """Return all connected physical iOS devices.

    Args:
        available_only: If True, only return devices that are available (paired).
    """
    try:
        require("xcrun")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)

    try:
        output = capture(
            ["xcrun", "devicectl", "list", "devices", "--json-output", "-"],
            check=False,
        )
        data = json.loads(output)
        devices = []
        for dev in data.get("result", {}).get("devices", []):
            # Skip if dev is not a dict
            if not isinstance(dev, dict):
                continue

            # Get device properties
            device_props = dev.get("deviceProperties", {})
            hardware_props = dev.get("hardwareProperties", {})
            connection_props = dev.get("connectionProperties", {})

            # Get state from connection properties
            pairing_state = connection_props.get("pairingState", "unknown")
            transport_type = connection_props.get("transportType", "")

            # Device is "connected" if it has wired transport
            # (localNetwork devices may not be actively connected)
            is_connected = transport_type == "wired"
            is_available = pairing_state == "paired" and is_connected

            if available_only and not is_available:
                continue

            # Get identifier - prefer hardware UDID for idevicesyslog compatibility
            identifier = hardware_props.get("udid", "")
            if not identifier:
                identifier = dev.get("identifier", "")
            if isinstance(identifier, dict):
                identifier = identifier.get("udid", "")
            if not identifier:
                hostnames = connection_props.get("potentialHostnames", [])
                if hostnames:
                    identifier = hostnames[0].split(".")[0]

            devices.append(
                IOSDevice(
                    identifier=identifier,
                    name=device_props.get("name", "Unknown"),
                    type="device",
                    model=hardware_props.get(
                        "marketingName", hardware_props.get("productType", "")
                    ),
                    state="available" if is_available else "unavailable",
                )
            )
        log.debug("found %d physical devices", len(devices))
        return devices
    except Exception as e:
        log.warning("failed to list physical devices: %s", e)
        return []


def list_devices(*, booted_only: bool = True) -> list[IOSDevice]:
    """Return available iOS devices (simulators and physical).

    Args:
        booted_only: If True (default), only return booted simulators and available devices.
    """
    devices = list_simulators(booted_only=booted_only) + list_physical_devices(
        available_only=booted_only
    )
    return devices


def select_device(*, prompt: str = "Please select iOS device") -> IOSDevice:
    """Return a single iOS device, prompting the user if needed.

    Exits the process with a clear error if no devices are available or the
    user cancels selection.
    """
    devices = list_devices()
    if not devices:
        log.error("no iOS devices found; check simulators or connect a device")
        sys.exit(1)

    # Prefer booted simulators or available physical devices
    booted = [d for d in devices if d.state in ("Booted", "available")]
    if len(booted) == 1:
        log.info("single active device found, auto-selected: %s", booted[0].name)
        return booted[0]

    if len(devices) == 1:
        log.info("single device found, auto-selected: %s", devices[0].name)
        return devices[0]

    # Build display list
    display_list = []
    for dev in devices:
        state_info = f" ({dev.state})" if dev.state and dev.state != "Booted" else ""
        type_info = f" [{dev.type}]"
        display_list.append(f"{dev.name}{type_info}{state_info}")

    idx = select_one(prompt, display_list)
    if idx is None:
        log.error("no device selected")
        sys.exit(1)
    return devices[idx]


def get_device_name(device: IOSDevice) -> str:
    """Return the human-readable name for an iOS device."""
    return device.name


def get_booted_simulator() -> IOSDevice | None:
    """Return the first booted simulator, or None if none are booted."""
    simulators = list_simulators()
    for sim in simulators:
        if sim.state == "Booted":
            return sim
    return None
