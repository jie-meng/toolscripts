"""``dotnet-switch`` - switch the active .NET SDK version managed by Homebrew."""

from __future__ import annotations

import argparse
import contextlib
import json
import sys

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.platform import require_platform
from toolscripts.core.shell import CommandNotFoundError, capture, require, run
from toolscripts.core.ui_curses import select_one

log = get_logger(__name__)

_INSTALL_EXAMPLES = """\
Install other versions:
  brew install dotnet           # latest SDK
  brew install dotnet@9         # .NET 9 SDK
  brew install dotnet@8         # .NET 8 SDK"""


def _get_formulas() -> list[dict]:
    """Return installed dotnet Homebrew formula info dicts."""
    try:
        out = capture(["brew", "list", "--formula", "--full-name"])
    except Exception as exc:
        log.error("failed to list brew formulae: %s", exc)
        sys.exit(1)

    names = [line for line in out.splitlines() if line.startswith("dotnet")]
    if not names:
        return []

    info_json = capture(["brew", "info", "--json=v2", "--formula"] + names)
    try:
        data = json.loads(info_json)
    except json.JSONDecodeError as exc:
        log.error("failed to parse brew info output: %s", exc)
        sys.exit(1)

    return data.get("formulae", [])


def _get_version(formula: dict) -> str:
    ver = formula.get("versions", {}).get("stable")
    return str(ver) if ver else "?"


def _get_linked_name(formulas: list[dict]) -> str | None:
    for f in formulas:
        if f.get("linked_keg"):
            return f["name"]
    return None


def _show_status(formulas: list[dict], linked: str | None) -> None:
    print("dotnet-switch  —  Homebrew .NET SDK status")
    print()
    if not formulas:
        print("  No dotnet formulae installed.")
    else:
        for f in formulas:
            ver = _get_version(f)
            name = f["name"]
            mark = "  ← active" if name == linked else ""
            print(f"  {name:14s}  {ver:10s}{mark}")

    print()
    try:
        ver = capture(["dotnet", "--version"])
        print(f"  dotnet CLI: {ver}")
    except Exception:
        print("  dotnet CLI: not on PATH")

    try:
        sdks = capture(["dotnet", "--list-sdks"])
        for line in sdks.splitlines():
            print(f"    {line}")
    except Exception:
        pass

    print()
    print(_INSTALL_EXAMPLES)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="dotnet-switch",
        description="Switch the active .NET SDK version installed via Homebrew.",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="show current status and exit",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    if args.status:
        require_platform("macos")
        try:
            require("brew")
        except CommandNotFoundError as exc:
            log.error("brew is required: %s", exc)
            sys.exit(1)

        formulas = _get_formulas()
        linked = _get_linked_name(formulas)
        _show_status(formulas, linked)
        return

    require_platform("macos")

    try:
        require("brew")
    except CommandNotFoundError as exc:
        log.error("brew is required: %s", exc)
        sys.exit(1)

    formulas = _get_formulas()

    if not formulas:
        log.info("No dotnet formulae installed via Homebrew.")
        print()
        print(_INSTALL_EXAMPLES)
        return

    linked = _get_linked_name(formulas)

    display = []
    for f in formulas:
        ver = _get_version(f)
        name = f["name"]
        label = f"{name}  ({ver})"
        if name == linked:
            label += "  ← active"
        display.append(label)

    default = None
    for i, f in enumerate(formulas):
        if f["name"] == linked:
            default = i
            break

    idx = select_one("Select .NET SDK version:", display, default_index=default)
    if idx is None:
        log.warning("cancelled")
        return

    chosen = formulas[idx]
    if chosen["name"] == linked:
        log.info("already using %s", chosen["name"])
        return

    for f in formulas:
        with contextlib.suppress(Exception):
            run(["brew", "unlink", "--force", f["name"]])

    try:
        run(["brew", "link", "--force", "--overwrite", chosen["name"]])
    except Exception as exc:
        log.error("failed to link %s: %s", chosen["name"], exc)
        sys.exit(1)

    print(f"\nSwitched to {chosen['name']} ({_get_version(chosen)})")
    try:
        ver = capture(["dotnet", "--version"])
        print(f"  dotnet --version: {ver}")
    except Exception:
        pass
    print()
    print(_INSTALL_EXAMPLES)
