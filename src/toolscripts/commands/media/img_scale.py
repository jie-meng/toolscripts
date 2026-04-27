"""``img-scale`` - scale a single image by a factor (0 < scale < 1) via ImageMagick."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import CommandNotFoundError, require, run

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="img-scale",
        description="Scale an image by a factor (0 < scale < 1) using ImageMagick.",
    )
    parser.add_argument("file", help="path to the image")
    parser.add_argument("scale", type=float, help="scale factor, e.g. 0.5")
    parser.add_argument("-o", "--output", help="output path (default: <name>-output.<ext>)")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        require("magick")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)

    input_path = Path(args.file).expanduser()
    if not input_path.is_file():
        log.error("file not found: %s", input_path)
        sys.exit(1)

    if not 0 < args.scale < 1:
        log.error("scale must be in (0, 1) - got %s", args.scale)
        sys.exit(1)

    output = Path(args.output) if args.output else input_path.with_name(
        f"{input_path.stem}-output{input_path.suffix}"
    )
    percentage = f"{args.scale * 100:g}%"
    cmd = ["magick", str(input_path), "-resize", percentage, str(output)]
    log.info("running: %s", " ".join(cmd))
    run(cmd)
    log.success("output: %s", output)


if __name__ == "__main__":
    main()
