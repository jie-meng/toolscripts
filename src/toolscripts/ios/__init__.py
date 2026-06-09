"""iOS device discovery and selection helpers."""

from toolscripts.ios.devices import (
    IOSDevice,
    get_booted_simulator,
    get_device_name,
    list_devices,
    list_physical_devices,
    list_simulators,
    select_device,
)

__all__ = [
    "IOSDevice",
    "get_booted_simulator",
    "get_device_name",
    "list_devices",
    "list_physical_devices",
    "list_simulators",
    "select_device",
]
