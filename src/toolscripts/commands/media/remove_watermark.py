"""``remove-watermark`` - crop a fixed-size watermark from one or more images."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import CommandNotFoundError, capture, require, run

log = get_logger(__name__)

_POSITIONS = ("top-left", "top-right", "bottom-left", "bottom-right")


def _identify(path: Path) -> tuple[int, int]:
    out = capture(["magick", "identify", "-format", "%w %h", str(path)])
    w, h = out.split()
    return int(w), int(h)


def _crop(input_path: Path, output_path: Path, position: str, width: int, height: int) -> bool:
    img_w, img_h = _identify(input_path)
    if position in ("bottom-right", "bottom-left"):
        new_w = img_w
        new_h = max(1, img_h - height)
        geom = f"{new_w}x{new_h}+0+0"
        gravity = "North"
    elif position in ("top-left", "top-right"):
        new_w = img_w
        new_h = max(1, img_h - height)
        geom = f"{new_w}x{new_h}+0+{height}"
        gravity = "South"
    else:
        log.error("invalid position %r", position)
        return False

    cmd = [
        "magick", str(input_path),
        "-gravity", gravity, "-crop", geom, "+repage",
        str(output_path),
    ]
    try:
        run(cmd)
    except Exception as exc:  # noqa: BLE001
        log.error("magick failed: %s", exc)
        return False
    log.success("created: %s (%dx%d)", output_path, new_w, new_h)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="remove-watermark",
        description="Remove a fixed-size watermark band by cropping the affected edge.",
    )
    parser.add_argument("images", nargs="+", help="image files to process")
    parser.add_argument(
        "-p",
        "--position",
        choices=_POSITIONS,
        default="bottom-right",
        help="watermark corner (default: bottom-right)",
    )
    parser.add_argument(
        "-s",
        "--size",
        default="250,100",
        help="watermark width,height in pixels (default: 250,100)",
    )
    parser.add_argument(
        "-o", "--output", help="output file (only valid when processing a single image)"
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        require("magick")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)

    try:
        w_str, h_str = args.size.split(",", 1)
        width, height = int(w_str), int(h_str)
    except ValueError:
        log.error("invalid --size format %r (expected W,H)", args.size)
        sys.exit(1)

    if args.output and len(args.images) > 1:
        log.warning("--output ignored when processing multiple images")
        args.output = None

    successes = 0
    for raw in args.images:
        path = Path(raw).expanduser()
        if not path.is_file():
            log.warning("skipping missing file: %s", raw)
            continue
        out = (
            Path(args.output)
            if args.output
            else path.with_name(f"{path.stem}_no_watermark{path.suffix}")
        )
        if _crop(path, out, args.position, width, height):
            successes += 1

    log.success("processed %d/%d image(s)", successes, len(args.images))


if __name__ == "__main__":
    main()
