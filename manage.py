#!/usr/bin/env python3
"""Manage the local installation of toolscripts (install / uninstall / status).

Tiny, dependency-free helper that wraps `uv` and `pip` so users don't have to
remember the exact flags. Supports both installation backends; `uv` is the
default.

Examples:
    ./manage.py install                      # uv, core only (fast, no extras)
    ./manage.py install --extras all         # uv + every optional dep
    ./manage.py install --extras media,clipboard
    ./manage.py install --pip                # pip into the active env
    ./manage.py install --force              # force reinstall even if up to date

    ./manage.py uninstall                    # try both uv and pip
    ./manage.py uninstall --uv
    ./manage.py uninstall --pip

    ./manage.py status                       # show install status on both sides

Fast-skip behavior:
    Once installed via uv, `./manage.py install` re-runs as a no-op as long
    as `pyproject.toml` hasn't changed - source edits under `src/` are picked
    up live by the editable install with no reinstall needed.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

PACKAGE = "toolscripts"
DEFAULT_EXTRAS = ""
ROOT = Path(__file__).resolve().parent
_STAMP = ROOT / ".manage-py-install-stamp"
_PYPROJECT = ROOT / "pyproject.toml"


# ---------------------------------------------------------------------------
# tiny color helpers (no dependency on the package itself - it might not be
# installed yet when this script runs)
# ---------------------------------------------------------------------------

def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return sys.stderr.isatty()


_COLOR = _supports_color()


def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR else text


def info(msg: str) -> None:
    print(_c("INFO  ", "36") + msg)


def success(msg: str) -> None:
    print(_c("OK    ", "32") + msg)


def warn(msg: str) -> None:
    print(_c("WARN  ", "33") + msg, file=sys.stderr)


def error(msg: str) -> None:
    print(_c("ERROR ", "31") + msg, file=sys.stderr)


# ---------------------------------------------------------------------------
# subprocess helpers
# ---------------------------------------------------------------------------

def _have(tool: str) -> bool:
    return shutil.which(tool) is not None


def _run(cmd: list[str], *, check: bool = True) -> int:
    info("$ " + " ".join(cmd))
    res = subprocess.run(cmd, check=False)
    if check and res.returncode != 0:
        error(f"command failed (exit {res.returncode})")
        sys.exit(res.returncode)
    return res.returncode


def _capture(cmd: list[str]) -> tuple[int, str]:
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return res.returncode, (res.stdout + res.stderr).strip()


# ---------------------------------------------------------------------------
# detection
# ---------------------------------------------------------------------------

def _uv_installed() -> bool:
    if not _have("uv"):
        return False
    code, out = _capture(["uv", "tool", "list"])
    if code != 0:
        return False
    return any(line.startswith(PACKAGE + " ") for line in out.splitlines())


def _uv_version() -> str | None:
    if not _have("uv"):
        return None
    code, out = _capture(["uv", "tool", "list"])
    if code != 0:
        return None
    for line in out.splitlines():
        if line.startswith(PACKAGE + " "):
            version = line.split()[-1]
            return version.lstrip("v") if len(line.split()) > 1 else "unknown"
    return None


def _pip_version() -> str | None:
    code, out = _capture([sys.executable, "-m", "pip", "show", PACKAGE])
    if code != 0:
        return None
    for line in out.splitlines():
        if line.lower().startswith("version:"):
            return line.split(":", 1)[1].strip()
    return "unknown"


def _hint_install_uv() -> None:
    warn("uv is not installed.")
    print("  install via one of:")
    print("    brew install uv                                             # macOS")
    print("    curl -LsSf https://astral.sh/uv/install.sh | sh            # macOS/Linux")
    print("    powershell -ExecutionPolicy ByPass -c \"irm https://astral.sh/uv/install.ps1 | iex\"  # Windows")


def _pyproject_mtime() -> float:
    try:
        return _PYPROJECT.stat().st_mtime
    except OSError:
        return 0.0


def _stamp_mtime() -> float:
    try:
        return _STAMP.stat().st_mtime
    except OSError:
        return 0.0


def _write_stamp() -> None:
    try:
        _STAMP.write_text(f"{_pyproject_mtime()}\n", encoding="utf-8")
    except OSError as exc:
        warn(f"could not write install stamp: {exc}")


def _pyproject_changed_since_install() -> bool:
    return _pyproject_mtime() > _stamp_mtime()


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------

def cmd_install(args: argparse.Namespace) -> int:
    pip_arg = f".[{args.extras}]" if args.extras else "."

    if args.pip:
        warn("installing via pip - this puts the package into the currently active "
             "Python environment and may conflict with other projects.")
        warn("for daily CLI use prefer: ./manage.py install   (uv)")
        cmd = [sys.executable, "-m", "pip", "install", "-e", pip_arg]
        if args.force:
            cmd.append("--force-reinstall")
        _run(cmd, check=True)
        _write_stamp()
        success(f"{PACKAGE} installed via pip into {sys.executable}")
        return 0

    if not _have("uv"):
        _hint_install_uv()
        return 1

    already = _uv_installed()

    if already and not args.force and not _pyproject_changed_since_install():
        success(f"{PACKAGE} is up to date - editable install picks up src/ changes automatically")
        info("pass --force to reinstall anyway, or edit pyproject.toml to trigger a reinstall")
        return 0

    spec = f".[{args.extras}]" if args.extras else "."
    cmd = ["uv", "tool", "install", "-e", spec]
    if args.force or already:
        cmd.append("--force")
    _run(cmd, check=True)
    _write_stamp()
    success(f"{PACKAGE} installed via uv (extras: {args.extras or 'none'})")
    info("commands are now available on $PATH (~/.local/bin)")
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    target_uv = args.uv or not args.pip
    target_pip = args.pip or not args.uv
    did_anything = False

    if target_uv:
        if not _have("uv"):
            info("uv not present - skipping uv uninstall")
        elif not _uv_installed():
            info(f"{PACKAGE} is not installed via uv - skipping")
        else:
            _run(["uv", "tool", "uninstall", PACKAGE], check=False)
            did_anything = True

    if target_pip:
        if _pip_version() is None:
            info(f"{PACKAGE} is not installed via pip ({sys.executable}) - skipping")
        else:
            _run([sys.executable, "-m", "pip", "uninstall", "-y", PACKAGE], check=False)
            did_anything = True
            warn("pip leaves dependencies behind. To list candidates run:")
            print("    pip show pyperclip pillow matplotlib openpyxl markdownify "
                  "translate binaryornot")

    if did_anything:
        with contextlib.suppress(OSError):
            _STAMP.unlink(missing_ok=True)
        success("uninstall complete")
    else:
        warn(f"{PACKAGE} is not installed (uv or pip) - nothing to do")
    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    print(_c(f"=== {PACKAGE} install status ===", "1;36"))

    if not _have("uv"):
        print(f"  uv    :  {_c('not installed', '33')}")
    else:
        v = _uv_version()
        if v is None:
            print(f"  uv    :  {_c('not installed', '33')}  (uv itself is available)")
        else:
            print(f"  uv    :  {_c('installed', '32')}  (version {v})")

    pv = _pip_version()
    label = f"pip ({sys.executable})"
    if pv is None:
        print(f"  {label} :  {_c('not installed', '33')}")
    else:
        print(f"  {label} :  {_c('installed', '32')}  (version {pv})")

    if _have(PACKAGE) is False and not (
        _have("timestamp-now") or _have("hex2rgb")
    ):
        warn("no toolscripts commands found on $PATH")
    return 0


# ---------------------------------------------------------------------------
# argparse
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="manage.py",
        description="Install / uninstall / inspect the local toolscripts package.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="action", required=True)

    p_install = sub.add_parser(
        "install",
        help="install the package (default: uv, core only - fast)",
    )
    p_install.add_argument(
        "--extras",
        default=DEFAULT_EXTRAS,
        help=(
            "comma-separated extras to install (default: none - core only). "
            "Use 'all' for everything, or pick from clipboard,media,office,text,windows. "
            "Example: --extras media,clipboard"
        ),
    )
    p_install.add_argument(
        "--pip",
        action="store_true",
        help="install via pip into the active Python env (not recommended)",
    )
    p_install.add_argument(
        "--force",
        action="store_true",
        help="force reinstall if already present",
    )
    p_install.set_defaults(func=cmd_install)

    p_uninstall = sub.add_parser(
        "uninstall",
        help="uninstall the package (default: try both uv and pip)",
    )
    p_uninstall.add_argument("--uv", action="store_true", help="uninstall only via uv")
    p_uninstall.add_argument("--pip", action="store_true", help="uninstall only via pip")
    p_uninstall.set_defaults(func=cmd_uninstall)

    p_status = sub.add_parser("status", help="show install status on both uv and pip")
    p_status.set_defaults(func=cmd_status)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
