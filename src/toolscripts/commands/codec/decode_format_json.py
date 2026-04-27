"""``decode-and-format-json`` - decode a base64 string and pretty-print the JSON inside."""

from __future__ import annotations

import argparse
import base64
import json
import sys

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)


def decode_base64_to_json(b64: str) -> str:
    missing = len(b64) % 4
    if missing:
        b64 += "=" * (4 - missing)
    decoded = base64.b64decode(b64).decode("utf-8")
    data = json.loads(decoded)
    return json.dumps(data, indent=4, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="decode-and-format-json",
        description="Decode a base64 string and pretty-print the JSON it contains.",
    )
    parser.add_argument("payload", help="base64-encoded JSON string")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        print(decode_base64_to_json(args.payload))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        log.error("could not decode/parse: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
