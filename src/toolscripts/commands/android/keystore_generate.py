"""``android-keystore-generate`` - wrap keytool to generate Android keystores."""

from __future__ import annotations

import argparse
import sys

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.prompts import ask, yes_no
from toolscripts.core.shell import CommandNotFoundError, require, run

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="android-keystore-generate",
        description="Generate an Android signing keystore via keytool.",
    )
    parser.add_argument("--debug", action="store_true", help="generate the standard debug keystore")
    parser.add_argument("--keystore", help="keystore filename (release only)")
    parser.add_argument("--alias", help="key alias (release only)")
    parser.add_argument("--validity", type=int, help="validity in days (release only)")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        require("keytool")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        log.warning("keytool ships with the JDK; install OpenJDK or set JAVA_HOME")
        sys.exit(1)

    if args.debug or yes_no("Is it a debug keystore?", default=False):
        cmd = [
            "keytool", "-genkey", "-v",
            "-keystore", "debug.keystore",
            "-storepass", "android",
            "-alias", "androiddebugkey",
            "-keypass", "android",
            "-keyalg", "RSA", "-keysize", "2048",
            "-validity", "10000",
        ]
    else:
        keystore = args.keystore or ask("Please input keystore name")
        alias = args.alias or ask("Please input alias name")
        validity_raw = (
            str(args.validity) if args.validity is not None else ask("Please input validity (days)")
        )
        if not keystore or not alias or not validity_raw:
            log.error("keystore, alias, and validity all required")
            sys.exit(1)
        try:
            validity = int(validity_raw)
        except ValueError:
            log.error("validity must be an integer: %r", validity_raw)
            sys.exit(1)
        cmd = [
            "keytool", "-genkey", "-v",
            "-keystore", keystore,
            "-alias", alias,
            "-keyalg", "RSA", "-keysize", "2048",
            "-validity", str(validity),
        ]

    log.info("running: %s", " ".join(cmd))
    run(cmd, check=False)


if __name__ == "__main__":
    main()
