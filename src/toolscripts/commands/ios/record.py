"""``ios-record`` - record video from the booted iOS simulator."""

from __future__ import annotations

import argparse
import contextlib
import json
import signal
import subprocess
import sys
import time
from pathlib import Path

from toolscripts.commands.android._video import compress_video
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.platform import require_platform
from toolscripts.core.shell import CommandNotFoundError, capture, require

log = get_logger(__name__)


def _get_booted_simulator() -> tuple[str | None, str | None]:
    try:
        out = capture(["xcrun", "simctl", "list", "devices", "booted", "-j"])
    except subprocess.CalledProcessError:
        return None, None
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return None, None
    for devices in data.get("devices", {}).values():
        for dev in devices:
            if dev.get("state") == "Booted":
                return dev["udid"], dev.get("name", "Unknown")
    return None, None


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ios-record",
        description="Record a video of the booted iOS simulator (macOS only).",
    )
    parser.add_argument(
        "--no-compress", action="store_true", help="skip the compression prompt"
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

    udid, sim_name = _get_booted_simulator()
    if not udid:
        log.error("no booted iOS simulator found")
        log.warning("start a simulator first, e.g. `xcrun simctl boot <udid>`")
        sys.exit(1)

    log.success("found booted simulator: %s (%s)", sim_name, udid)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    video_file = Path(f"ios-video-{timestamp}.mp4").resolve()

    proc = subprocess.Popen(
        ["xcrun", "simctl", "io", udid, "recordVideo", "--force", str(video_file)],
        stderr=subprocess.PIPE,
    )
    assert proc.stderr is not None

    try:
        for raw_line in proc.stderr:
            line = raw_line.decode(errors="replace").strip()
            if "Recording started" in line:
                break
            if line:
                log.warning("%s", line)
        else:
            if proc.poll() is not None:
                log.error("simctl exited without starting recording")
                sys.exit(1)
    except KeyboardInterrupt:
        proc.kill()
        proc.wait()
        sys.exit(130)

    log.success("Recording... Press Enter or Ctrl-C to stop.")
    with contextlib.suppress(KeyboardInterrupt, EOFError):
        input()

    proc.send_signal(signal.SIGINT)
    proc.wait()

    log.success("video saved: %s", video_file)
    if video_file.exists():
        size_mb = video_file.stat().st_size / (1024 * 1024)
        log.info("size: %.1f MB", size_mb)

    if args.no_compress or not video_file.exists():
        return

    response = input("Compress video? (Y/n, default Y, quality 1): ").strip().lower()
    if response in ("", "y", "1"):
        compress_video(video_file, quality=1)
    elif response in ("2", "3"):
        compress_video(video_file, quality=int(response))


if __name__ == "__main__":
    main()
