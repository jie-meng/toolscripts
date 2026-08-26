"""``pido`` - run a prompt via ``pi -p`` against the freellmapi provider with the ``auto`` model."""

from __future__ import annotations

import argparse
import sys

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import CommandNotFoundError, require, run

log = get_logger(__name__)

PROVIDER = "freellmapi"
MODEL = "auto"


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pido",
        description=f"Run a prompt via `pi -p` using the {PROVIDER} provider and the {MODEL} model.",
        add_help=False,
    )
    parser.add_argument("prompt", nargs=argparse.REMAINDER, help="prompt to send")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    if not args.prompt:
        log.error("usage: pido <prompt> [...]")
        sys.exit(1)

    try:
        require("pi")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        log.error("install from https://pi.dev and ensure `pi` is on PATH.")
        sys.exit(1)

    cmd = ["pi", "-p", "--provider", PROVIDER, "--model", MODEL, "--", *args.prompt]

    log.debug("running: %s", " ".join(cmd))
    run(cmd)


if __name__ == "__main__":
    main()
