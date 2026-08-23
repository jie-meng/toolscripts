"""``pi-update-all`` - update pi core and all pi extensions."""

from __future__ import annotations

import argparse

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import run

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pi-update-all",
        description="Update pi core and all pi extensions in one step.",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    log.info("Updating pi core...")
    run(["pi", "update"])

    log.info("Updating pi extensions...")
    run(["pi", "update", "--extensions"])

    log.success("Done.")


if __name__ == "__main__":
    main()