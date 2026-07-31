"""``cbdo`` - run a prompt via CodeBuddy (`cbc`) in print mode with the free hy3 model."""

from __future__ import annotations

import argparse
import shutil
import sys

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import run

log = get_logger(__name__)

DEFAULT_MODEL = "hy3"


def _codebuddy_bin() -> str:
    for name in ("cbc", "codebuddy"):
        if shutil.which(name):
            return name
    log.error("codebuddy not found on PATH (looked for `cbc` / `codebuddy`).")
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="cbdo",
        description="Run a prompt via CodeBuddy in print mode using the free hy3 model.",
        add_help=False,
    )
    parser.add_argument("prompt", nargs=argparse.REMAINDER, help="prompt to send")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--safe",
        action="store_true",
        help="without --dangerously-skip-permissions (may prompt for permission)",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    if not args.prompt:
        log.error("usage: cbdo <prompt> [...]")
        sys.exit(1)

    bin_name = _codebuddy_bin()
    prompt = " ".join(args.prompt)
    cmd = [bin_name, "--print", "--model", args.model, prompt]
    if not args.safe:
        cmd.append("--dangerously-skip-permissions")
    log.debug("running: %s", " ".join(cmd))
    run(cmd)


if __name__ == "__main__":
    main()
