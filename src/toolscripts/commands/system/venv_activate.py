"""``venv-activate`` - find and activate a Python virtual environment.

A child process can't modify its parent shell's environment, so this command
operates in two complementary modes:

* default - spawn a new interactive subshell with the venv pre-activated.
  Type ``exit`` (or Ctrl-D) to return to the original shell.
* ``--print``  - print the absolute path to the venv's ``activate`` script.
  Use it as ``source "$(venv-activate --print)"`` from your shell, optionally
  wrapped in a function in your rc file.

Detection is conservative: a directory only counts as a venv when it has all
the canonical markers (``pyvenv.cfg`` + ``bin/python`` (or ``Scripts/python.exe``
on Windows) + the matching ``activate`` script).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from toolscripts.core import colors
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.platform import is_windows
from toolscripts.core.prompts import choice

log = get_logger(__name__)

_PREFERRED_NAMES = (".venv", "venv", ".env", "env")


def _activate_relpath(venv: Path) -> Path:
    """Return the path inside ``venv`` to the activate script for this OS."""
    if is_windows():
        return venv / "Scripts" / "activate.bat"
    return venv / "bin" / "activate"


def _python_relpath(venv: Path) -> Path:
    if is_windows():
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def _is_venv(path: Path) -> bool:
    """Conservative venv check: needs ``pyvenv.cfg`` + python + activate script."""
    if not path.is_dir():
        return False
    if not (path / "pyvenv.cfg").is_file():
        return False
    if not _python_relpath(path).exists():
        return False
    return _activate_relpath(path).is_file()


def _scan_for_venvs(root: Path) -> list[Path]:
    """Find venvs in ``root``, preferred names first, then any other immediate child."""
    found: list[Path] = []
    seen: set[Path] = set()

    for name in _PREFERRED_NAMES:
        candidate = root / name
        if _is_venv(candidate):
            found.append(candidate)
            seen.add(candidate.resolve())

    try:
        children = sorted(root.iterdir(), key=lambda p: p.name.lower())
    except OSError as exc:
        log.debug("cannot list %s: %s", root, exc)
        return found

    for child in children:
        if child.name.startswith("."):
            continue
        resolved = child.resolve()
        if resolved in seen:
            continue
        if _is_venv(child):
            found.append(child)
            seen.add(resolved)

    return found


def _pick_venv(venvs: list[Path]) -> Path | None:
    if len(venvs) == 1:
        return venvs[0]
    labels = [
        str(v.relative_to(Path.cwd())) if v.is_relative_to(Path.cwd()) else str(v) for v in venvs
    ]
    idx = choice("Multiple virtual environments found:", labels, default=0)
    if idx is None:
        return None
    return venvs[idx]


def _spawn_subshell(venv: Path) -> None:
    activate = _activate_relpath(venv).resolve()
    venv_resolved = venv.resolve()

    if is_windows():
        log.error(
            "subshell activation is not supported on Windows yet; "
            'use --print and `call "%s"` instead',
            activate,
        )
        sys.exit(1)

    shell = os.environ.get("SHELL", "/bin/bash")
    shell_name = Path(shell).name

    env = os.environ.copy()
    env["VIRTUAL_ENV"] = str(venv_resolved)
    env["VIRTUAL_ENV_PROMPT"] = f"({venv_resolved.name}) "
    bin_dir = str((venv_resolved / "bin").resolve())
    env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")
    env.pop("PYTHONHOME", None)
    env["TOOLSCRIPTS_VENV_ACTIVATED"] = str(venv_resolved)

    log.success(
        "activated %s (subshell: %s) - type `exit` to leave",
        colors.colored(str(venv_resolved), colors.GREEN, bold=True),
        shell_name,
    )

    args: list[str]
    if shell_name in ("zsh", "bash"):
        args = [shell, "-i"]
    elif shell_name == "fish":
        args = [shell, "-i", "-C", f"source '{activate}.fish'"]
    else:
        args = [shell, "-i"]

    try:
        os.execvpe(args[0], args, env)
    except OSError as exc:
        log.error("failed to spawn %s: %s", shell, exc)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="venv-activate",
        description=(
            "Find a Python virtual environment under the current directory and "
            "activate it. Defaults to spawning a subshell with the venv enabled; "
            "pass --print to emit the activate-script path for use with "
            '`source "$(venv-activate --print)"`.'
        ),
    )
    parser.add_argument(
        "--name",
        help="explicit venv directory name to use (skips auto-detection)",
    )
    parser.add_argument(
        "--print",
        dest="print_only",
        action="store_true",
        help="print the absolute path to the activate script and exit",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    cwd = Path.cwd()

    if args.name:
        candidate = cwd / args.name
        if not _is_venv(candidate):
            log.error("not a virtual environment: %s", candidate)
            sys.exit(1)
        venv = candidate
    else:
        venvs = _scan_for_venvs(cwd)
        if not venvs:
            log.error(
                "no virtual environment found in %s "
                "(looked for %s, plus any directory with pyvenv.cfg + bin/python + activate)",
                cwd,
                ", ".join(_PREFERRED_NAMES),
            )
            log.warning("create one with: venv-create  (or: uv-venv-create)")
            sys.exit(1)
        picked = _pick_venv(venvs)
        if picked is None:
            log.warning("cancelled")
            sys.exit(130)
        venv = picked

    activate = _activate_relpath(venv).resolve()

    if args.print_only:
        print(activate)
        return

    log.info("found venv: %s", venv.relative_to(cwd) if venv.is_relative_to(cwd) else venv)
    _spawn_subshell(venv)


if __name__ == "__main__":
    main()
