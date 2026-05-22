"""``android-screenshot`` - capture a screenshot from a connected Android device."""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

from toolscripts.adb.devices import select_device
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="android-screenshot",
        description="Capture a screenshot from a connected Android device.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output file path (default: android-screenshot-<timestamp>.png)",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    device = select_device()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = args.output or Path(f"android-screenshot-{timestamp}.png")

    log.info("capturing screenshot from %s...", device)
    try:
        result = subprocess.run(
            ["adb", "-s", device, "exec-out", "screencap", "-p"],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        log.error("screencap failed: %s", exc)
        sys.exit(1)

    output.write_bytes(result.stdout)
    log.success("screenshot saved: %s", output)


if __name__ == "__main__":
    main()
