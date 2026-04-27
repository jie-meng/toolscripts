"""``android-retrieve-media`` - pull recent images/videos/screenshots from a device."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from toolscripts.adb.devices import select_device
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.prompts import ask, choice
from toolscripts.core.shell import capture, run

log = get_logger(__name__)


_PRESETS = [
    ("Image (jpg/png from DCIM/Camera)",          "/sdcard/DCIM/Camera",        ("IMG_",), (".jpg", ".png")),
    ("Screenshot (jpg/png from DCIM/Screenshots)", "/sdcard/DCIM/Screenshots",   ("Screenshot_",), (".jpg", ".png")),
    ("Video (mp4 from DCIM/Camera)",              "/sdcard/DCIM/Camera",        ("VID_",), (".mp4",)),
    ("Screen recording (mp4 from DCIM/ScreenRecorder)", "/sdcard/DCIM/ScreenRecorder", (), (".mp4",)),
]


def _matches(name: str, prefixes: tuple[str, ...], suffixes: tuple[str, ...]) -> bool:
    if prefixes and not any(name.startswith(p) for p in prefixes):
        return False
    if suffixes and not any(name.endswith(s) for s in suffixes):
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="android-retrieve-media",
        description="Retrieve recent media files from an Android device's DCIM tree.",
    )
    parser.add_argument(
        "-n", "--count", type=int, default=None, help="number of latest files to pull"
    )
    parser.add_argument(
        "-o", "--output", default=".", help="local output directory (default: .)"
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    device = select_device()
    output_dir = Path(args.output).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    idx = choice("Select media type", [p[0] for p in _PRESETS], default=0)
    if idx is None:
        return
    _, remote_dir, prefixes, suffixes = _PRESETS[idx]

    listing = capture(["adb", "-s", device, "shell", "ls", remote_dir], check=False)
    items = [line.strip() for line in listing.splitlines() if line.strip()]
    items = [name for name in items if _matches(name, prefixes, suffixes)]
    items.sort(reverse=True)

    if not items:
        log.warning("no matching files in %s", remote_dir)
        return

    log.info("found %d matching files", len(items))
    if args.count is not None:
        count = max(1, args.count)
    else:
        raw = ask("How many files to retrieve (latest)?", default="1") or "1"
        try:
            count = max(1, int(raw))
        except ValueError:
            log.error("not a valid integer: %r", raw)
            sys.exit(1)

    for name in items[:count]:
        src = f"{remote_dir}/{name}"
        dst = output_dir / name
        log.info("pulling %s", name)
        run(["adb", "-s", device, "pull", src, str(dst)], check=False)


if __name__ == "__main__":
    main()
