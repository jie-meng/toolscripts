"""``basic-auth`` - generate a Base64-encoded HTTP Basic Auth string."""

from __future__ import annotations

import argparse
import base64
import sys

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.prompts import ask

log = get_logger(__name__)


def basic_auth(key: str, secret: str) -> str:
    raw = f"{key}:{secret}".encode()
    return base64.b64encode(raw).decode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="basic-auth",
        description="Build an HTTP Basic Auth header value from key + secret.",
    )
    parser.add_argument("--key", help="key / username (prompted if omitted)")
    parser.add_argument("--secret", help="secret / password (prompted if omitted)")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    key = args.key or ask("Enter key")
    if not key:
        log.error("key required")
        sys.exit(1)
    secret = args.secret or ask("Enter secret")
    if not secret:
        log.error("secret required")
        sys.exit(1)

    encoded = basic_auth(key, secret)
    print()
    print("Encoded Basic Auth string:")
    print(f"key={key}, secret={secret}: {encoded}")


if __name__ == "__main__":
    main()
