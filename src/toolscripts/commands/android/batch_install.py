"""``android-batch-install`` - install APKs on connected devices using a JSON mapping."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from toolscripts.adb.devices import list_devices
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import run

log = get_logger(__name__)


def _load_mapping(path: Path) -> dict[str, str]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("mapping must be a JSON array of objects")
    out: dict[str, str] = {}
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        name = entry.get("deviceName")
        regex = entry.get("apkRegex")
        if name and regex:
            out[name] = regex
    return out


def _find_apk(regex: str, search_dir: Path) -> Path | None:
    pattern = re.compile(regex)
    for path in search_dir.iterdir():
        if path.suffix == ".apk" and pattern.fullmatch(path.name):
            return path
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="android-batch-install",
        description="Install APKs across multiple devices using a JSON device->regex mapping.",
    )
    parser.add_argument("mapping", help="JSON mapping file")
    parser.add_argument(
        "-d", "--directory", default=".", help="directory containing the .apk files (default: .)"
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    mapping_path = Path(args.mapping)
    if not mapping_path.is_file():
        log.error("mapping file not found: %s", mapping_path)
        sys.exit(1)
    try:
        mapping = _load_mapping(mapping_path)
    except (json.JSONDecodeError, ValueError) as exc:
        log.error("invalid mapping file: %s", exc)
        sys.exit(1)

    devices = list_devices()
    if not devices:
        log.error("no Android devices connected")
        sys.exit(1)

    search_dir = Path(args.directory).expanduser()
    if not search_dir.is_dir():
        log.error("directory not found: %s", search_dir)
        sys.exit(1)

    for device in devices:
        log.info("processing device: %s", device)
        regex = mapping.get(device)
        if not regex:
            log.warning("no mapping for device %r, skipping", device)
            continue
        apk = _find_apk(regex, search_dir)
        if not apk:
            log.warning("no APK matching %r for %s", regex, device)
            continue
        log.info("installing %s on %s", apk.name, device)
        result = run(["adb", "-s", device, "install", str(apk)], check=False)
        if result.returncode == 0:
            log.success("installed on %s", device)
        else:
            log.error("install failed on %s", device)
    log.info("done")


if __name__ == "__main__":
    main()
