"""``trans`` - basic English/Chinese translator with clipboard copy."""

from __future__ import annotations

import argparse
import sys

from toolscripts.core.clipboard import copy_to_clipboard
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="trans",
        description="Translate text between English and Chinese using the `translate` library.",
    )
    parser.add_argument(
        "lang", nargs="?", choices=("en", "zh"), help="target language (en or zh)"
    )
    parser.add_argument("text", nargs="*", help="text to translate (or read from stdin)")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    if args.lang is None:
        try:
            choice = input("Target language [en/zh]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
        if choice not in ("en", "zh"):
            log.error("only 'en' or 'zh' are supported")
            sys.exit(1)
        target = choice
    else:
        target = args.lang

    source = "zh" if target == "en" else "en"

    if args.text:
        text = " ".join(args.text)
    else:
        try:
            text = input("Enter text: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
    if not text:
        log.error("no text to translate")
        sys.exit(1)

    try:
        from translate import Translator  # type: ignore[import-not-found]
    except ImportError:
        log.error("missing dependency: install with `pip install translate`")
        sys.exit(1)

    translator = Translator(from_lang=source, to_lang=target)
    try:
        translation = translator.translate(text)
    except Exception as exc:  # noqa: BLE001
        log.error("translation failed: %s", exc)
        sys.exit(1)

    print(translation)
    if copy_to_clipboard(translation):
        log.success("copied to clipboard")
    else:
        log.warning("could not copy to clipboard")


if __name__ == "__main__":
    main()
