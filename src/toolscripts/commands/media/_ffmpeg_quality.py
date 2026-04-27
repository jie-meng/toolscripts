"""Helpers for video transcoding with ffmpeg."""

from __future__ import annotations

import sys
from pathlib import Path

from toolscripts.core.log import get_logger
from toolscripts.core.shell import CommandNotFoundError, require, run

log = get_logger(__name__)


_PRESETS: dict[str, tuple[str, str]] = {
    "1": ("28", "fast"),
    "2": ("23", "medium"),
    "3": ("18", "slow"),
}


def encode(
    input_file: Path,
    output_file: Path,
    *,
    quality: str | int,
) -> bool:
    """Run ffmpeg libx264/aac encode. Returns True on success."""
    try:
        require("ffmpeg")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        return False

    crf, preset = _PRESETS.get(str(quality), _PRESETS["1"])
    cmd = [
        "ffmpeg", "-i", str(input_file),
        "-c:v", "libx264", "-crf", crf, "-preset", preset,
        "-c:a", "aac", "-movflags", "+faststart",
        str(output_file),
    ]
    log.info("running: %s", " ".join(cmd))
    try:
        run(cmd)
    except Exception as exc:  # noqa: BLE001
        log.error("ffmpeg failed: %s", exc)
        return False
    return True


def prompt_quality() -> str:
    print("Select compression quality:")
    print("  1) Low (smallest size, lower quality) [Default]")
    print("  2) Medium (balanced)")
    print("  3) High (larger size, best quality)")
    try:
        raw = input("Enter choice [1-3] (default: 1): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    return raw or "1"
