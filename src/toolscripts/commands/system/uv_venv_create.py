"""``uv-venv-create`` - create a virtual environment via ``uv venv``."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import CommandNotFoundError, require, run

log = get_logger(__name__)

_PYENV_DIR = Path.home() / ".pyenv" / "versions"


def _pyenv_versions() -> list[str]:
    if not _PYENV_DIR.is_dir():
        return []
    return sorted(
        (p.name for p in _PYENV_DIR.iterdir() if p.is_dir()),
        key=lambda v: tuple(int(x) if x.isdigit() else x for x in v.split(".")),
        reverse=True,
    )


def _system_versions() -> list[str]:
    seen: list[str] = []
    for binary in (
        "python3.12",
        "python3.11",
        "python3.10",
        "python3.9",
        "python3.8",
        "python3",
        "python",
    ):
        if shutil.which(binary):
            try:
                out = subprocess.check_output([binary, "--version"], text=True).strip()
            except (subprocess.CalledProcessError, OSError):
                continue
            parts = out.split()
            if len(parts) >= 2 and parts[1] not in seen:
                seen.append(parts[1])
    return seen


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
        prog="uv-venv-create",
        description="Pick a Python version and create a virtual environment via `uv venv`.",
    )
    parser.add_argument(
        "--name", default=".venv", help="virtual environment directory (default: .venv)"
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        require("uv")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        log.warning("install uv: https://docs.astral.sh/uv/getting-started/installation/")
        sys.exit(1)

    versions = _pyenv_versions() or _system_versions()
    if not versions:
        log.error("no Python versions found")
        sys.exit(1)

    selected = _select(versions)
    if selected is None:
        log.warning("cancelled")
        return

    Path(".python-version").write_text(selected + "\n", encoding="utf-8")
    run(["uv", "venv", args.name, "--python", selected])
    log.success("created %s with python %s", args.name, selected)
    log.info("activate with: source %s/bin/activate", args.name)


if __name__ == "__main__":
    main()
