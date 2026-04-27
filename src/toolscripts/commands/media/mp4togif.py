"""``mp4togif`` - convert a video to a GIF via a palette filter chain."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import CommandNotFoundError, require, run

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mp4togif",
        description="Convert a video to GIF using ffmpeg with a high-quality palette.",
    )
    parser.add_argument("input", help="input video file")
    parser.add_argument("width", type=int, help="output width in pixels (height auto)")
    parser.add_argument("output", help="output .gif file")
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

    vf = (
        f"scale={args.width}:-1:flags=lanczos,split[s0][s1];"
        "[s0]palettegen[p];[s1][p]paletteuse"
    )
    cmd = ["ffmpeg", "-i", str(input_path), "-vf", vf, args.output]
    log.info("running: %s", " ".join(cmd))
    run(cmd)


if __name__ == "__main__":
    main()
