"""``trim-audio`` - trim an audio file (interactive prompts or smart silence detection)."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.prompts import ask
from toolscripts.core.shell import require

log = get_logger(__name__)

_SILENCE_START_RE = re.compile(r"silence_start:\s*(-?[0-9]+(?:\.[0-9]+)?)")
_SILENCE_END_RE = re.compile(r"silence_end:\s*(-?[0-9]+(?:\.[0-9]+)?)")


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


def _detect_silence_bounds(
    path: Path,
    *,
    threshold_db: float,
    min_silence: float,
) -> tuple[list[float], list[float]]:
    """Run ffmpeg's silencedetect filter and return (starts, ends) in seconds.

    ``starts[i]`` is the start of the i-th detected silent region, ``ends[i]``
    is its end. If a silent region runs to EOF, ``starts`` will have one more
    element than ``ends``.
    """
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        str(path),
        "-af",
        f"silencedetect=noise={threshold_db}dB:d={min_silence}",
        "-f",
        "null",
        "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log.error("silencedetect failed:\n%s", result.stderr[-500:])
        sys.exit(1)

    starts: list[float] = []
    ends: list[float] = []
    for line in result.stderr.splitlines():
        if (m := _SILENCE_START_RE.search(line)) is not None:
            starts.append(float(m.group(1)))
        elif (m := _SILENCE_END_RE.search(line)) is not None:
            ends.append(float(m.group(1)))
    return starts, ends


def _smart_bounds(
    path: Path,
    duration: float,
    *,
    threshold_db: float,
    min_silence: float,
    padding: float,
) -> tuple[float, float]:
    """Compute (start, end) that strip leading/trailing silence with padding."""
    starts, ends = _detect_silence_bounds(path, threshold_db=threshold_db, min_silence=min_silence)

    # Leading: if the first silence starts at (~)0, content begins at its end.
    first_content = 0.0
    if starts and ends and starts[0] <= min_silence:
        first_content = ends[0]

    # Trailing: ffmpeg may either leave the final silence open (len(starts) > len(ends))
    # or close it at the file end. Either way, "trailing silence" means the last
    # silent region reaches EOF. Use a small tolerance because ffmpeg sometimes
    # overshoots/undershoots the closing timestamp by a few ms.
    last_content = duration
    eof_tolerance = max(0.05, min_silence / 2)
    final_silence_at_eof = len(starts) > len(ends) or (
        starts and ends and ends[-1] >= duration - eof_tolerance
    )
    if final_silence_at_eof:
        last_content = starts[-1]

    start = max(0.0, first_content - padding)
    end = min(duration, last_content + padding)

    if end <= start:
        log.error(
            "smart-trim found no audible content (threshold=%sdB, min-silence=%ss).\n"
            "  Try a less aggressive threshold (e.g. --threshold -50) or a shorter\n"
            "  --min-silence value.",
            threshold_db,
            min_silence,
        )
        sys.exit(1)

    return start, end


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
        description="Trim an audio file interactively, or use -s for smart silence-trimming "
        "(supports wav, mp3, ogg, flac, etc.).",
    )
    parser.add_argument("input", help="Path to the input audio file")
    parser.add_argument("-o", "--output", help="Output file path (default: auto-generated)")
    parser.add_argument(
        "-s",
        "--smart",
        action="store_true",
        help="Auto-detect and strip leading/trailing silence (no interactive prompts).",
    )
    parser.add_argument(
        "--padding",
        type=float,
        default=0.3,
        metavar="SEC",
        help="With -s: head/tail silence to keep, in seconds (default: 0.3).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=-40.0,
        metavar="DB",
        help="With -s: silence threshold in dB; lower is stricter (default: -40).",
    )
    parser.add_argument(
        "--min-silence",
        type=float,
        default=0.5,
        metavar="SEC",
        help="With -s: minimum silence duration to detect, in seconds (default: 0.5).",
    )
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

    if args.smart:
        if args.padding < 0:
            log.error("--padding must be non-negative")
            sys.exit(1)
        start, end = _smart_bounds(
            input_path,
            duration,
            threshold_db=args.threshold,
            min_silence=args.min_silence,
            padding=args.padding,
        )
        log.info(
            "smart-trim: keeping %s – %s (stripped %.3fs head, %.3fs tail)",
            _format_time(start),
            _format_time(end),
            start,
            duration - end,
        )
    else:
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
    elif args.smart:
        output_path = Path(default_output)
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
