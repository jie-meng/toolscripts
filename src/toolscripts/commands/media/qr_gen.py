"""``qr-gen`` - generate a PNG QR code from a string."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.prompts import ask

log = get_logger(__name__)


def _output_path(raw: str | None) -> Path:
    if raw is None:
        raw = ask("Output file", default="out.png") if sys.stdin.isatty() else "out.png"
    return Path(raw or "out.png").expanduser()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="qr-gen",
        description="Generate a PNG QR code from a string.",
    )
    parser.add_argument("content", help="text to encode")
    parser.add_argument(
        "-o",
        "--output",
        help="output PNG path (prompted when omitted; empty input falls back to out.png)",
    )
    parser.add_argument(
        "-s", "--scale", type=int, default=10, help="pixels per QR module (default: 10)"
    )
    parser.add_argument(
        "-b", "--border", type=int, default=4, help="quiet zone width in modules (default: 4)"
    )
    parser.add_argument(
        "-e",
        "--error-level",
        type=str.upper,
        choices=("L", "M", "Q", "H"),
        default="M",
        help="error correction level (default: M)",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        import segno
    except ImportError:
        log.error("missing dependency: install with `./manage.py install --extras qrcode`")
        sys.exit(1)

    if args.scale < 1:
        log.error("scale must be >= 1 - got %s", args.scale)
        sys.exit(1)
    if args.border < 0:
        log.error("border must be >= 0 - got %s", args.border)
        sys.exit(1)

    output = _output_path(args.output)
    if output.is_dir():
        log.error("output is a directory: %s", output)
        sys.exit(1)
    if output.suffix.lower() != ".png":
        if output.suffix:
            log.error("output must be a .png file - got %s", output.name)
            sys.exit(1)
        output = output.with_suffix(".png")

    try:
        qr = segno.make_qr(args.content, error=args.error_level)
    except (ValueError, segno.DataOverflowError) as exc:
        log.error("could not encode content: %s", exc)
        sys.exit(1)

    output.parent.mkdir(parents=True, exist_ok=True)
    qr.save(output, kind="png", scale=args.scale, border=args.border)
    log.success("wrote %s", output)


if __name__ == "__main__":
    main()
