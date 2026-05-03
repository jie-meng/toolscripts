"""``trim-audio`` - trim an audio file with interactive start/end prompts."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.prompts import ask
from toolscripts.core.shell import require

log = get_logger(__name__)


def _get_duration(path: Path) -> float:
    """Return duration in seconds via ffprobe."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        log.error("failed to probe audio file: %s", result.stderr.strip())
        sys.exit(1)
    try:
        return float(result.stdout.strip())
    except ValueError:
        log.error("could not parse duration from ffprobe output")
        sys.exit(1)


def _parse_time(value: str) -> float | None:
    """Parse a user-entered time string to seconds. Returns None on failure."""
    try:
        t = float(value)
    except ValueError:
        return None
    return t if t >= 0 else None


def _format_time(seconds: float) -> str:
    """Format seconds to human-readable string."""
    if seconds == int(seconds):
        return str(int(seconds))
    return f"{seconds:.3f}".rstrip("0").rstrip(".")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="audio-trim",
        description="Trim an audio file interactively (supports wav, mp3, ogg, flac, etc.).",
    )
    parser.add_argument("input", help="Path to the input audio file")
    parser.add_argument("-o", "--output", help="Output file path (default: auto-generated)")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    require("ffmpeg")
    require("ffprobe")

    input_path = Path(args.input)
    if not input_path.is_file():
        log.error("file not found: %s", input_path)
        sys.exit(1)

    duration = _get_duration(input_path)
    log.info("source: %s (%s s)", input_path.name, _format_time(duration))

    raw_start = ask("start time", default="0")
    start = _parse_time(raw_start) if raw_start is not None else None
    if start is None or start < 0:
        log.error("invalid start time: %s", raw_start)
        sys.exit(1)

    raw_end = ask("end time", default=_format_time(duration))
    end = _parse_time(raw_end) if raw_end is not None else None
    if end is None or end <= start:
        log.error("invalid end time: %s (must be > start %s)", raw_end, _format_time(start))
        sys.exit(1)
    if end > duration:
        log.warning("end time %.3f exceeds duration %.3f, clamping", end, duration)
        end = duration

    ext = input_path.suffix
    stem = input_path.stem
    default_output = f"{stem}_trimmed{ext}"

    if args.output:
        output_path = Path(args.output)
    else:
        raw_out = ask("output file", default=default_output)
        output_path = Path(raw_out) if raw_out else Path(default_output)

    needs_transcode = output_path.suffix.lower() != ext.lower()
    cmd = ["ffmpeg", "-y", "-i", str(input_path)]
    cmd += ["-ss", str(start), "-to", str(end)]
    if needs_transcode and output_path.suffix.lower() == ".ogg":
        cmd += ["-c:a", "libopus"]
    elif needs_transcode:
        pass
    else:
        cmd += ["-c", "copy"]
    cmd.append(str(output_path))

    log.info(
        "trimming: %s → %s (%s – %s)",
        input_path.name,
        output_path.name,
        _format_time(start),
        _format_time(end),
    )

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log.error("ffmpeg failed:\n%s", result.stderr[-500:])
        sys.exit(1)

    if output_path.is_file():
        size_kb = output_path.stat().st_size / 1024
        log.success("saved: %s (%.0f KB)", output_path, size_kb)
    else:
        log.error("output file was not created")
        sys.exit(1)


if __name__ == "__main__":
    main()
