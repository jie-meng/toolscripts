"""``uvcmd`` - interactive front-end for common ``uv`` commands."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import CommandNotFoundError, require, run

log = get_logger(__name__)


def _ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    try:
        raw = input(f"{prompt}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(130)
    return raw or (default or "")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="uvcmd",
        description="Interactive front-end for common `uv` commands.",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        require("uv")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)

    while True:
        print("\nSelect a uv action:")
        print("  1) Create a virtual environment (uv-venv-create)")
        print("  2) Sync dependencies (uv sync / uv pip sync)")
        print("  3) Generate lock file (uv lock)")
        print("  4) Install a package (uv pip install)")
        print("  5) Uninstall a package (uv pip uninstall)")
        print("  6) List installed packages (uv pip list)")
        print("  7) Freeze packages (uv pip freeze)")
        print("  8) Clean cache (uv cache clean)")
        print("  9) Show cache directory (uv cache dir)")
        print("  0) Quit")
        try:
            choice = input("Your choice: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if choice == "0":
            return
        if choice == "1":
            try:
                run([sys.executable, "-m", "toolscripts.commands.system.uv_venv_create"])
            except Exception as exc:  # noqa: BLE001
                log.error("uv-venv-create failed: %s", exc)
        elif choice == "2":
            if Path("pyproject.toml").is_file():
                run(["uv", "sync"])
            else:
                req = _ask("requirements file", "requirements.txt")
                run(["uv", "pip", "sync", req])
        elif choice == "3":
            run(["uv", "lock"])
        elif choice == "4":
            pkg = _ask("package to install")
            if pkg:
                run(["uv", "pip", "install", pkg])
        elif choice == "5":
            pkg = _ask("package to uninstall")
            if pkg:
                run(["uv", "pip", "uninstall", pkg])
        elif choice == "6":
            run(["uv", "pip", "list"])
        elif choice == "7":
            run(["uv", "pip", "freeze"])
        elif choice == "8":
            run(["uv", "cache", "clean"])
        elif choice == "9":
            run(["uv", "cache", "dir"])
        else:
            log.warning("invalid choice")
        print("-" * 28)


if __name__ == "__main__":
    main()
