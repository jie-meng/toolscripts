"""Shared helper for compressing video files via ffmpeg.

Used by ``android-record`` and ``ios-record``.
"""

from __future__ import annotations

from pathlib import Path

from toolscripts.core.log import get_logger
from toolscripts.core.shell import run, which

log = get_logger(__name__)


def compress_video(input_file: Path, *, quality: int = 1) -> Path | None:
    """Compress ``input_file`` with ffmpeg. Returns the output path on success."""
    if which("ffmpeg") is None:
        log.warning("ffmpeg not found on PATH; skipping compression")
        return None

    presets = {1: ("28", "fast"), 2: ("23", "medium"), 3: ("18", "slow")}
    crf, preset = presets.get(quality, presets[1])
    output = input_file.with_name(f"{input_file.stem}_compressed.mp4")

    log.info("compressing video (quality=%d)...", quality)
    cmd = [
        "ffmpeg", "-i", str(input_file),
        "-c:v", "libx264", "-crf", crf, "-preset", preset,
        "-c:a", "aac", "-movflags", "+faststart",
        str(output),
    ]
    try:
        run(cmd)
    except Exception as exc:  # noqa: BLE001
        log.error("compression failed: %s", exc)
        return None

    try:
        orig_mb = input_file.stat().st_size / (1024 * 1024)
        comp_mb = output.stat().st_size / (1024 * 1024)
        log.success("compressed: %.1fMB -> %.1fMB", orig_mb, comp_mb)
        log.info("output: %s", output)
    except OSError:
        pass
    return output
