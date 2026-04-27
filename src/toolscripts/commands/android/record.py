"""``android-record`` - record the screen on an Android device, pull the file, optionally compress."""

from __future__ import annotations

import argparse
import contextlib
import subprocess
import sys
import time
from pathlib import Path

from toolscripts.adb.devices import select_device
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import run

from ._video import compress_video

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="android-record",
        description="Record the screen on a connected Android device.",
    )
    parser.add_argument(
        "--no-compress", action="store_true", help="skip the compression prompt"
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    device = select_device()
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    remote = f"/sdcard/android-video-{timestamp}.mp4"
    local = Path(f"android-video-{timestamp}.mp4")

    log.info("starting screen recording on device %s...", device)
    proc = subprocess.Popen(["adb", "-s", device, "shell", "screenrecord", remote])

    try:
        input("Press Enter to stop recording.")
    except (EOFError, KeyboardInterrupt):
        print()

    proc.terminate()
    with contextlib.suppress(subprocess.TimeoutExpired):
        proc.wait(timeout=5)
    if proc.poll() is None:
        proc.kill()

    log.info("stopping recording...")
    time.sleep(2)

    log.info("pulling %s -> %s", remote, local)
    try:
        run(["adb", "-s", device, "pull", remote, str(local)])
        log.success("video downloaded: %s", local)
    except subprocess.CalledProcessError as exc:
        log.error("failed to download video: %s", exc)
        sys.exit(1)

    log.info("removing %s from device", remote)
    run(["adb", "-s", device, "shell", "rm", remote], check=False)

    if args.no_compress or not local.exists():
        return

    response = input("Compress video? (Y/n, default Y, quality 1): ").strip().lower()
    if response in ("", "y"):
        compress_video(local, quality=1)
    elif response in ("2", "3"):
        compress_video(local, quality=int(response))


if __name__ == "__main__":
    main()
