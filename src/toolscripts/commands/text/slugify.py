"""``slugify`` - convert a phrase to a slug, optionally interactively."""

from __future__ import annotations

import argparse
import re
import sys

from toolscripts.core.clipboard import copy_to_clipboard
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)

_PUNCT_RE = re.compile(r"""[!,:.?;'"()\[\]{}/\\|*<>@#$%^&+=~`]""")


def _normalize(phrase: str) -> str:
    cleaned = _PUNCT_RE.sub("", phrase)
    return " ".join(cleaned.split())


def _apply_case(text: str, mode: str) -> str:
    if mode == "upper":
        return text.upper()
    if mode == "lower":
        return text.lower()
    return text


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="slugify",
        description="Convert a phrase to a slug (e.g. 'App Store Connect' -> 'App-Store-Connect').",
    )
    parser.add_argument("phrase", nargs="+", help="phrase to convert")
    parser.add_argument(
        "-s", "--separator", default="-", choices=("-", "_"), help="separator (default: -)"
    )
    parser.add_argument(
        "-c",
        "--case",
        choices=("unchanged", "upper", "lower"),
        default="unchanged",
        help="output case (default: unchanged)",
    )
    parser.add_argument(
        "--no-copy", action="store_true", help="do not copy the result to clipboard"
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    phrase = _normalize(" ".join(args.phrase))
    if not phrase:
        log.error("empty phrase after normalization")
        sys.exit(1)

    slug = _apply_case(args.separator.join(phrase.split()), args.case)
    print(slug)

    if not args.no_copy:
        if copy_to_clipboard(slug):
            log.success("copied to clipboard")
        else:
            log.warning("could not copy to clipboard")


if __name__ == "__main__":
    main()
