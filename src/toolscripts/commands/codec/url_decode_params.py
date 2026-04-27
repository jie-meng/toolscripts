"""``url-decode-params`` - decode URL-encoded query parameters with JSON detection."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse

from toolscripts.core import colors
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)


def _try_parse_json(value: str) -> object | None:
    s = value.strip()
    looks_object = s.startswith("{") and s.endswith("}")
    looks_array = s.startswith("[") and s.endswith("]")
    if not (looks_object or looks_array):
        return None
    try:
        return json.loads(s)
    except (json.JSONDecodeError, ValueError):
        return None


def _format_value(key: str, value: str) -> str:
    parsed = _try_parse_json(value)
    if parsed is not None:
        body = json.dumps(parsed, indent=2, ensure_ascii=False)
        return f"{colors.colored(key, colors.GREEN)}={colors.colored(body, colors.CYAN)}"
    return f"{colors.colored(key, colors.GREEN)}={colors.colored(value, colors.CYAN)}"


def decode(query_string: str) -> dict[str, list[str]]:
    qs = query_string.lstrip("?")
    return urllib.parse.parse_qs(qs, keep_blank_values=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="url-decode-params",
        description=(
            "Decode URL-encoded query parameters. Accepts a full URL or a query string. "
            "Wrap the input in quotes to avoid shell parsing of '&'."
        ),
    )
    parser.add_argument("input", help="URL or query string")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    raw = args.input
    base_url: str | None = None
    if "?" in raw:
        base_url, query_string = raw.split("?", 1)
    else:
        query_string = raw

    if "&" not in query_string and "=" in query_string and len(query_string) < 100:
        log.warning("input may be truncated by the shell; quote it to keep '&' safe")

    if base_url:
        print(f"{colors.colored('Base URL:', colors.YELLOW)} {base_url}")
        print(f"{colors.colored('Query String:', colors.YELLOW)} {query_string}")
        print()

    try:
        params = decode(query_string)
    except (ValueError, UnicodeDecodeError) as exc:
        log.error("error decoding parameters: %s", exc)
        sys.exit(1)

    if not params:
        log.warning("no parameters found")
        return

    print(colors.colored("Decoded Parameters:", colors.BLUE))
    for key, values in sorted(params.items()):
        for value in values:
            print(_format_value(key, value))


if __name__ == "__main__":
    main()
