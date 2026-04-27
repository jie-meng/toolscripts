"""``docker-linux-env`` - run a Linux utility container with the cwd mounted at /app."""

from __future__ import annotations

import argparse
import os
import sys

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import CommandNotFoundError, require, run

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="docker-linux-env",
        description="Run an interactive bash inside jmengxy/util with the cwd mounted at /app.",
    )
    parser.add_argument(
        "--image",
        default="jmengxy/util",
        help="Docker image to run (default: jmengxy/util)",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        require("docker")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)

    run(
        [
            "docker",
            "run",
            "--rm",
            "-it",
            "-v",
            f"{os.getcwd()}:/app",
            args.image,
            "bash",
        ]
    )


if __name__ == "__main__":
    main()
