"""``mp3-to-pcm`` - convert MP3 audio to mono 16kHz s16le PCM."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import CommandNotFoundError, require, run

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mp3-to-pcm",
        description="Convert .mp3 to .pcm (s16le, 16kHz, 1 channel) via ffmpeg.",
    )
    parser.add_argument("input", help=".mp3 input file")
    parser.add_argument("--rate", type=int, default=16000, help="sample rate (default: 16000)")
    parser.add_argument(
        "--channels", type=int, default=1, help="channel count (default: 1, mono)"
    )
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
    output = input_path.with_suffix(".pcm")
    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-f", "s16le", "-ar", str(args.rate),
        "-ac", str(args.channels), str(output),
    ]
    log.info("running: %s", " ".join(cmd))
    run(cmd)
    log.success("output: %s", output)


if __name__ == "__main__":
    main()
