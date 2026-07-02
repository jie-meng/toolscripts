"""``git-alias-setup`` - set up common git aliases (st, co, ci, br, lg)."""

from __future__ import annotations

import argparse

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import require, run

log = get_logger(__name__)

ALIASES: dict[str, str] = {
    "st": "status",
    "co": "checkout",
    "ci": "commit",
    "br": "branch",
    "lg": "log --color --graph --pretty=format:'%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr) %C(bold blue)<%an>%Creset' --abbrev-commit",
}


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="git-alias-setup",
        description="Set up common global git aliases (st, co, ci, br, lg).",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    require("git")

    for alias, command in ALIASES.items():
        run(["git", "config", "--global", f"alias.{alias}", command])
        log.success("alias.%-4s → git %s", alias, command)

    log.success("all git aliases set up successfully")


if __name__ == "__main__":
    main()
