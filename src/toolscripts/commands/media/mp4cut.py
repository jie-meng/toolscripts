"""``mp4cut`` - extract a time range from a video using ffmpeg."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import CommandNotFoundError, require, run

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mp4cut",
        description="Cut a section of a video file (re-encoded copy by default).",
    )
    parser.add_argument("input", help="input video file")
    parser.add_argument("start", help="start time, e.g. 00:00:00")
    parser.add_argument("end", help="end time, e.g. 00:00:10")
    parser.add_argument("output", help="output video file")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        require("ffmpeg")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)

    input_path = Path(args.input).expanduser()
    if not input_path.is_file():
        log.error("file not found: %s", input_path)
        sys.exit(1)

    cmd = [
        "ffmpeg", "-i", str(input_path),
        "-ss", args.start, "-to", args.end, args.output,
    ]
    log.info("running: %s", " ".join(cmd))
    run(cmd)


if __name__ == "__main__":
    main()
