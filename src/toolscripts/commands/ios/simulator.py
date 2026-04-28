"""``ios-simulator`` - list iOS simulators, boot/open the chosen one."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.platform import require_platform
from toolscripts.core.shell import CommandNotFoundError, capture, require, run
from toolscripts.core.ui_curses import select_one

log = get_logger(__name__)

_DEVICE_ORDER = [
    "iPhone Pro Max",
    "iPhone Pro",
    "iPhone",
    "iPhone Plus",
    "iPhone SE",
    "iPad Pro",
    "iPad Air",
    "iPad mini",
    "iPad",
]


def _device_sort_key(name: str) -> tuple[int, str]:
    for i, prefix in enumerate(_DEVICE_ORDER):
        if name.startswith(prefix):
            return (i, name)
    return (len(_DEVICE_ORDER), name)


def _ios_sort_key(ios: str) -> tuple[int, ...]:
    try:
        parts = (
            ios.replace("iOS-", "")
            .replace("tvOS-", "")
            .replace("watchOS-", "")
            .replace("xrOS-", "")
        )
        return tuple(-int(n) for n in parts.split("-"))
    except (ValueError, TypeError):
        return (0,)


def _list_devices() -> list[tuple[str, str, str, str, str | None]]:
    output = capture(["xcrun", "simctl", "list", "devices", "-j"], check=False)
    data = json.loads(output)
    devices: list[tuple[str, str, str, str, str | None]] = []
    for runtime, dev_list in data.get("devices", {}).items():
        ios_version = runtime.replace("com.apple.CoreSimulator.SimRuntime.", "")
        for dev in dev_list:
            if not dev.get("isAvailable", True):
                continue
            name = dev["name"]
            uuid = dev["udid"]
            status = "Booted" if dev.get("state") == "Booted" else "Shutdown"
            last_boot = dev.get("lastBootedAt")
            devices.append((name, uuid, status, ios_version, last_boot))
    devices.sort(
        key=lambda d: (
            d[2] != "Booted",
            -(datetime.fromisoformat((d[4] or "0001-01-01T00:00:00Z").replace("Z", "+00:00")).timestamp() // 1),
            _ios_sort_key(d[3]),
            _device_sort_key(d[0]),
        )
    )
    return devices


def _format_boot_time(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = now - dt
        if diff.days > 30:
            return dt.strftime("%Y-%m-%d")
        if diff.days >= 1:
            return f"{diff.days}d ago"
        hours = diff.seconds // 3600
        if hours >= 1:
            return f"{hours}h ago"
        minutes = diff.seconds // 60
        if minutes >= 1:
            return f"{minutes}m ago"
        return "just now"
    except (ValueError, TypeError):
        return ""


def _build_display_items(
    devices: list[tuple[str, str, str, str, str | None]],
) -> list[str]:
    items: list[str] = []
    for name, _uuid, status, ios, last_boot in devices:
        status_mark = "*" if status == "Booted" else " "
        parts = [f"{status_mark} {name}", f"({ios})"]
        if last_boot:
            parts.append(_format_boot_time(last_boot))
        else:
            parts.append("never")
        items.append("  ".join(parts))
    return items


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ios-simulator",
        description="List iOS simulators in a curses picker and boot/open the selected one.",
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

    items = _build_display_items(devices)
    items.append("  Shutdown all devices")

    idx = select_one(
        title="iOS Simulators  (j/k move  Enter select  q quit)",
        items=items,
    )

    if idx is None:
        return

    if idx == len(devices):
        run(["xcrun", "simctl", "shutdown", "all"])
        log.success("all simulators have been shut down")
        return

    name, uuid, status, _ios, _ = devices[idx]
    if status == "Booted":
        run(["open", "-a", "Simulator"])
        log.info("opening Simulator for %s", name)
    else:
        run(["xcrun", "simctl", "boot", uuid])
        run(["open", "-a", "Simulator"])
        log.info("booting and opening Simulator for %s", name)


if __name__ == "__main__":
    main()