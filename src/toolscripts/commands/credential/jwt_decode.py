"""``jwt-decode`` - decode a JWT token like jwt.io, in the terminal."""

from __future__ import annotations

import argparse
import base64
import json
import sys
from datetime import datetime, timezone
from typing import Any

from toolscripts.core import colors
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)

KNOWN_TIMESTAMP_CLAIMS = {"exp", "iat", "nbf", "auth_time"}


def _b64_decode(segment: str) -> bytes:
    padding = 4 - len(segment) % 4
    if padding != 4:
        segment += "=" * padding
    return base64.urlsafe_b64decode(segment)


def _decode_json(segment: str, label: str) -> dict[str, Any]:
    try:
        return json.loads(_b64_decode(segment))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        log.error("could not decode %s: %s", label, exc)
        sys.exit(1)


def _format_timestamp(value: object) -> str:
    try:
        dt = datetime.fromtimestamp(int(value), tz=timezone.utc)  # type: ignore[arg-type]
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except (ValueError, TypeError, OSError):
        return ""


def _print_block(data: dict[str, Any], color: str) -> None:
    formatted = json.dumps(data, indent=2, ensure_ascii=False)
    for line in formatted.splitlines():
        print(f"  {colors.colored(line, color)}")


def _print_claim_annotations(data: dict[str, Any]) -> None:
    annotations: list[str] = []
    for key in KNOWN_TIMESTAMP_CLAIMS:
        if key in data:
            human = _format_timestamp(data[key])
            if human:
                line = f"  {key}: {data[key]} -> {human}"
                annotations.append(colors.colored(line, colors.GREY))

    if "exp" in data:
        try:
            exp_dt = datetime.fromtimestamp(int(data["exp"]), tz=timezone.utc)
            now = datetime.now(tz=timezone.utc)
            if exp_dt < now:
                msg = f"  Token EXPIRED ({_format_timestamp(data['exp'])})"
                annotations.append(colors.colored(msg, colors.RED, bold=True))
            else:
                delta = exp_dt - now
                msg = f"  Token valid (expires in {delta})"
                annotations.append(colors.colored(msg, colors.GREEN))
        except (ValueError, TypeError, OSError):
            pass

    if annotations:
        print()
        for line in annotations:
            print(line)


def decode_jwt(token: str) -> None:
    token = token.strip()
    if token.lower().startswith("bearer "):
        token = token[7:]

    parts = token.split(".")
    if len(parts) != 3:
        log.error("invalid JWT - expected 3 parts separated by '.', got %d", len(parts))
        sys.exit(1)

    header = _decode_json(parts[0], "header")
    payload = _decode_json(parts[1], "payload")
    signature = parts[2]

    sep = "-" * 60
    print()
    print(colors.colored(sep, colors.WHITE, bold=True))
    print(colors.colored("  JWT Decoded", colors.WHITE, bold=True))
    print(colors.colored(sep, colors.WHITE, bold=True))

    print()
    print(colors.colored("> HEADER", colors.CYAN, bold=True))
    _print_block(header, colors.CYAN)

    print()
    print(colors.colored("> PAYLOAD", colors.GREEN, bold=True))
    _print_block(payload, colors.GREEN)
    _print_claim_annotations(payload)

    print()
    print(colors.colored("> SIGNATURE", colors.YELLOW, bold=True))
    print(f"  {colors.colored(signature, colors.YELLOW)}")
    alg = header.get("alg", "unknown")
    print(f"  {colors.colored(f'Algorithm: {alg}', colors.GREY)}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="jwt-decode",
        description="Decode a JWT and display header, payload, and signature.",
        epilog="Example: jwt-decode eyJhbGciOiJIUzI1NiIs...",
    )
    parser.add_argument(
        "token",
        nargs="?",
        help="JWT token (also accepts 'Bearer <token>'). Reads stdin if omitted.",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    if args.token:
        token = args.token
    elif not sys.stdin.isatty():
        token = sys.stdin.read().strip()
    else:
        parser.print_help()
        sys.exit(1)

    if not token:
        log.error("no token provided")
        sys.exit(1)

    decode_jwt(token)


if __name__ == "__main__":
    main()
