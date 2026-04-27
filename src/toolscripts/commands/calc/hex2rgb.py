"""``hex2rgb`` - convert a hex color code to RGB."""

from __future__ import annotations

import argparse
import sys

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    raw = value.lstrip("#").strip()
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    if len(raw) != 6:
        raise ValueError(f"hex color must be 3 or 6 chars, got {value!r}")
    r = int(raw[0:2], 16)
    g = int(raw[2:4], 16)
    b = int(raw[4:6], 16)
    return r, g, b


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="hex2rgb",
        description="Convert a hex color code (e.g. #ff8800) to RGB.",
    )
    parser.add_argument("color", help="hex color, with or without leading '#'")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        r, g, b = hex_to_rgb(args.color)
    except ValueError as exc:
        log.error("%s", exc)
        sys.exit(1)

    print(f"RGB({r}, {g}, {b})")


if __name__ == "__main__":
    main()
