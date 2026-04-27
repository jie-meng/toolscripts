"""``oauth-code`` - generate a TOTP code via ``oathtool`` and copy to clipboard.

Migrated from ``shell/oauth-code``. The user must provide the secret either via
environment variable ``OATH_SECRET`` or via the ``--secret`` flag - the original
shell script's hard-coded placeholder ``******`` was a configuration leftover.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

from toolscripts.core.clipboard import copy_to_clipboard
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import CommandNotFoundError, require

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="oauth-code",
        description=(
            "Generate a TOTP code via `oathtool` and copy it to the clipboard. "
            "The base32 secret comes from --secret or $OATH_SECRET."
        ),
    )
    parser.add_argument(
        "-s",
        "--secret",
        help="base32-encoded TOTP secret (defaults to $OATH_SECRET)",
    )
    parser.add_argument(
        "--no-copy", action="store_true", help="do not copy the code to clipboard"
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    secret = args.secret or os.environ.get("OATH_SECRET")
    if not secret:
        log.error("provide a secret via --secret or $OATH_SECRET")
        sys.exit(1)

    try:
        require("oathtool")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        log.warning("install via Homebrew: 'brew install oath-toolkit'")
        sys.exit(1)

    try:
        out = subprocess.check_output(
            ["oathtool", "--totp", "-b", secret], text=True
        ).strip()
    except subprocess.CalledProcessError as exc:
        log.error("oathtool failed: %s", exc)
        sys.exit(1)

    print(out)
    if not args.no_copy and copy_to_clipboard(out):
        log.success("code copied to clipboard")


if __name__ == "__main__":
    main()
