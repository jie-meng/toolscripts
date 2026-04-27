"""``hex2dec`` - convert hexadecimal numbers to decimal."""

from __future__ import annotations

import argparse
import sys

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="hex2dec",
        description="Convert hexadecimal number(s) to decimal.",
    )
    parser.add_argument("numbers", nargs="*", help="hex numbers (with or without 0x prefix)")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    if args.numbers:
        for value in args.numbers:
            try:
                print(int(value, 16))
            except ValueError:
                log.error("not a valid hex: %r", value)
                sys.exit(1)
        return

    try:
        while True:
            try:
                raw = input("Please input hex number: ").strip()
            except EOFError:
                break
            if not raw:
                break
            try:
                print(int(raw, 16))
            except ValueError:
                log.warning("not a valid hex: %r", raw)
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
