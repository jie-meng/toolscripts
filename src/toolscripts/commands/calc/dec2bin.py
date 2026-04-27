"""``dec2bin`` - convert decimal numbers to binary (interactive or one-shot)."""

from __future__ import annotations

import argparse
import sys

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="dec2bin",
        description="Convert decimal number(s) to binary. Reads from args or stdin.",
    )
    parser.add_argument("numbers", nargs="*", help="decimal numbers to convert")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    if args.numbers:
        for value in args.numbers:
            try:
                print(f"{int(value):b}")
            except ValueError:
                log.error("not a valid decimal: %r", value)
                sys.exit(1)
        return

    try:
        while True:
            try:
                raw = input("Please input decimal number: ").strip()
            except EOFError:
                break
            if not raw:
                break
            try:
                print(f"{int(raw):b}")
            except ValueError:
                log.warning("not a valid decimal: %r", raw)
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
