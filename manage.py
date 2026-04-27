#!/usr/bin/env python3
"""Manage the local installation of toolscripts (install / uninstall / status).

Tiny, dependency-free helper that wraps `pipx` and `pip` so users don't have to
remember the exact flags. Supports both installation backends, but `pipx` is
strongly recommended for CLI tools.

Examples:
    ./manage.py install                      # pipx + [all] (default)
    ./manage.py install --extras media,git
    ./manage.py install --pip                # pip into the active env
    ./manage.py install --force              # force reinstall

    ./manage.py uninstall                    # try both pipx and pip
    ./manage.py uninstall --pipx
    ./manage.py uninstall --pip

    ./manage.py status                       # show install status on both sides
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

PACKAGE = "toolscripts"
DEFAULT_EXTRAS = "all"
ROOT = Path(__file__).resolve().parent


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

def _pipx_installed() -> bool:
    if not _have("pipx"):
        return False
    code, out = _capture(["pipx", "list", "--short"])
    if code != 0:
        return False
    return any(line.startswith(PACKAGE + " ") for line in out.splitlines())


def _pipx_version() -> str | None:
    if not _have("pipx"):
        return None
    code, out = _capture(["pipx", "list", "--short"])
    if code != 0:
        return None
    for line in out.splitlines():
        parts = line.split()
        if parts and parts[0] == PACKAGE:
            return parts[1] if len(parts) > 1 else "unknown"
    return None


def _pip_version() -> str | None:
    code, out = _capture([sys.executable, "-m", "pip", "show", PACKAGE])
    if code != 0:
        return None
    for line in out.splitlines():
        if line.lower().startswith("version:"):
            return line.split(":", 1)[1].strip()
    return "unknown"


def _hint_install_pipx() -> None:
    warn("pipx is not installed.")
    print("  install via one of:")
    print("    brew install pipx                                         # macOS")
    print("    python3 -m pip install --user pipx && python3 -m pipx ensurepath")
    print("    sudo apt install pipx                                     # Debian/Ubuntu 23.04+")


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------

def cmd_install(args: argparse.Namespace) -> int:
    spec = f"{ROOT}[{args.extras}]" if args.extras else str(ROOT)
    pip_arg = f".[{args.extras}]" if args.extras else "."

    if args.pip:
        warn("installing via pip - this puts the package into the currently active "
             "Python environment and may conflict with other projects.")
        warn("for daily CLI use prefer: ./manage.py install   (pipx)")
        cmd = [sys.executable, "-m", "pip", "install", "-e", pip_arg]
        if args.force:
            cmd.append("--force-reinstall")
        _run(cmd, check=True)
        success(f"{PACKAGE} installed via pip into {sys.executable}")
        return 0

    if not _have("pipx"):
        _hint_install_pipx()
        return 1

    already = _pipx_installed()
    if already and not args.force:
        info(f"{PACKAGE} already installed via pipx - reinstalling to pick up changes")
        cmd = ["pipx", "reinstall", PACKAGE]
        _run(cmd, check=True)
        success(f"{PACKAGE} reinstalled via pipx")
        return 0

    cmd = ["pipx", "install", "-e", spec]
    if args.force or already:
        cmd.append("--force")
    _run(cmd, check=True)
    success(f"{PACKAGE} installed via pipx (extras: {args.extras or 'none'})")
    info("commands are now available on $PATH (~/.local/bin)")
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    target_pipx = args.pipx or not args.pip
    target_pip = args.pip or not args.pipx
    did_anything = False

    if target_pipx:
        if not _have("pipx"):
            info("pipx not present - skipping pipx uninstall")
        elif not _pipx_installed():
            info(f"{PACKAGE} is not installed via pipx - skipping")
        else:
            _run(["pipx", "uninstall", PACKAGE], check=False)
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
        success("uninstall complete")
    else:
        warn(f"{PACKAGE} is not installed (pipx or pip) - nothing to do")
    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    print(_c(f"=== {PACKAGE} install status ===", "1;36"))

    if not _have("pipx"):
        print(f"  pipx :  {_c('not installed', '33')}")
    else:
        v = _pipx_version()
        if v is None:
            print(f"  pipx :  {_c('not installed', '33')}  (pipx itself is available)")
        else:
            print(f"  pipx :  {_c('installed', '32')}  (version {v})")

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
        help="install the package (default: pipx + [all])",
    )
    p_install.add_argument(
        "--extras",
        default=DEFAULT_EXTRAS,
        help="comma-separated extras to install (default: %(default)s; pass '' for none)",
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
        help="uninstall the package (default: try both pipx and pip)",
    )
    p_uninstall.add_argument("--pipx", action="store_true", help="uninstall only via pipx")
    p_uninstall.add_argument("--pip", action="store_true", help="uninstall only via pip")
    p_uninstall.set_defaults(func=cmd_uninstall)

    p_status = sub.add_parser("status", help="show install status on both pipx and pip")
    p_status.set_defaults(func=cmd_status)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
