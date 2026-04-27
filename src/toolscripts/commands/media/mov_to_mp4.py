"""``mov-to-mp4`` - convert a MOV file to MP4 with selectable quality."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

from ._ffmpeg_quality import encode, prompt_quality

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mov-to-mp4",
        description="Convert a .mov file to .mp4 (libx264) with selectable quality.",
    )
    parser.add_argument("input", help="path to the .mov file")
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
    if input_path.suffix.lower() != ".mov":
        log.error("input must be a .mov file")
        sys.exit(1)

    quality = args.quality or prompt_quality()
    output = input_path.with_suffix(".mp4")
    if not encode(input_path, output, quality=quality):
        sys.exit(1)
    log.success("output: %s", output)


if __name__ == "__main__":
    main()
