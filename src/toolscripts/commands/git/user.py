"""``git-user`` - interactively view or update local git user.name / user.email."""

from __future__ import annotations

import argparse
import subprocess

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.prompts import ask

log = get_logger(__name__)


def _config_get(key: str) -> str:
    try:
        out = subprocess.run(
            ["git", "config", key], capture_output=True, text=True, check=False
        )
        return out.stdout.strip() or "(not set)"
    except FileNotFoundError:
        return "(git not found)"


def _show() -> None:
    print()
    print(f"Git Username: {_config_get('user.name')}")
    print(f"Git Email:    {_config_get('user.email')}")
    print()


def _set() -> None:
    name = ask("Enter Git Username")
    if not name:
        log.warning("no name entered, skipping")
        return
    email = ask("Enter Git Email")
    if not email:
        log.warning("no email entered, skipping")
        return
    subprocess.run(["git", "config", "user.name", name], check=True)
    subprocess.run(["git", "config", "user.email", email], check=True)
    log.success("git config updated")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="git-user",
        description="Display or update local git user.name and user.email.",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    while True:
        print("\nPlease select an option:")
        print("1) Display Git Username and Email")
        print("2) Set Git Username and Email")
        print("0) Exit")
        try:
            choice = input("Enter your choice (1/2/0): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if choice == "1":
            _show()
        elif choice == "2":
            _set()
        elif choice == "0":
            return
        else:
            log.warning("invalid choice")


if __name__ == "__main__":
    main()
