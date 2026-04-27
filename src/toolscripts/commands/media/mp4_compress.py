"""``mp4-compress`` - compress an MP4 file with selectable quality."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

from ._ffmpeg_quality import encode, prompt_quality

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mp4-compress",
        description="Compress an MP4 with libx264 (quality 1=low, 2=medium, 3=high).",
    )
    parser.add_argument("input", help="path to the .mp4 file")
    parser.add_argument(
        "quality",
        nargs="?",
        choices=("1", "2", "3"),
        help="quality preset (will prompt if omitted)",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    input_path = Path(args.input).expanduser()
    if not input_path.is_file():
        log.error("file not found: %s", input_path)
        sys.exit(1)
    if input_path.suffix.lower() != ".mp4":
        log.error("input must be a .mp4 file")
        sys.exit(1)

    quality = args.quality or prompt_quality()
    output = input_path.with_name(f"{input_path.stem}_compressed.mp4")
    if not encode(input_path, output, quality=quality):
        sys.exit(1)

    try:
        orig = input_path.stat().st_size / (1024 * 1024)
        comp = output.stat().st_size / (1024 * 1024)
        log.success("compressed: %.1fMB -> %.1fMB", orig, comp)
        log.info("output: %s", output)
    except OSError:
        pass


if __name__ == "__main__":
    main()
