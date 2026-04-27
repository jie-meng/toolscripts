"""``venv-create`` - select a pyenv-managed Python version and create a venv."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import CommandNotFoundError, require, run

log = get_logger(__name__)

_PYENV_DIR = Path.home() / ".pyenv" / "versions"


def _list_versions() -> list[str]:
    if not _PYENV_DIR.is_dir():
        return []
    return sorted(
        (p.name for p in _PYENV_DIR.iterdir() if p.is_dir()),
        key=lambda v: tuple(int(x) if x.isdigit() else x for x in v.split(".")),
        reverse=True,
    )


def _select(versions: list[str]) -> str | None:
    print("Select a Python version to create the virtual environment:")
    for i, v in enumerate(versions, 1):
        print(f"  {i}. {v}")
    try:
        raw = input(f"Enter choice (1-{len(versions)}): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    if not raw.isdigit():
        return None
    idx = int(raw) - 1
    if not 0 <= idx < len(versions):
        return None
    return versions[idx]


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="venv-create",
        description=(
            "Pick a pyenv-managed Python version and create a venv via `python -m venv`."
        ),
    )
    parser.add_argument(
        "--name", default=".venv", help="virtual environment directory (default: .venv)"
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    versions = _list_versions()
    if not versions:
        log.error("no pyenv versions found in %s", _PYENV_DIR)
        sys.exit(1)

    selected = _select(versions)
    if selected is None:
        log.warning("cancelled")
        return

    Path(".python-version").write_text(selected + "\n", encoding="utf-8")
    log.info("wrote .python-version = %s", selected)

    try:
        require("python")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)

    run(["python", "-m", "venv", args.name])
    log.success("created %s with python %s", args.name, selected)


if __name__ == "__main__":
    main()
