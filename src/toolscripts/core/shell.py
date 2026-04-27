"""Subprocess wrappers with consistent error handling and logging.

Higher-level than ``subprocess.run`` but still very thin. The goal is to keep
all of the toolscripts commands using the same idioms:

    from toolscripts.core.shell import run, capture, which, CommandNotFoundError

    if not which("adb"):
        raise CommandNotFoundError("adb")

    run(["adb", "devices"])
    output = capture(["git", "rev-parse", "HEAD"])
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Sequence

from toolscripts.core.log import get_logger

log = get_logger(__name__)


class CommandNotFoundError(RuntimeError):
    """Raised when an external binary cannot be located on PATH."""

    def __init__(self, name: str) -> None:
        super().__init__(f"required command not found on PATH: {name}")
        self.name = name


def which(name: str) -> str | None:
    """Return the absolute path of ``name`` on PATH, or ``None``."""
    return shutil.which(name)


def require(name: str) -> str:
    """Like ``which()`` but raises ``CommandNotFoundError`` if missing."""
    path = shutil.which(name)
    if not path:
        raise CommandNotFoundError(name)
    return path


def run(
    cmd: Sequence[str],
    *,
    check: bool = True,
    env: dict[str, str] | None = None,
    cwd: str | None = None,
    input: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run ``cmd`` and stream output to the parent terminal.

    Use this when you want the user to see the command's output live.
    """
    log.debug("run: %s", " ".join(cmd))
    return subprocess.run(
        list(cmd),
        check=check,
        env=env,
        cwd=cwd,
        input=input,
        text=True,
    )


def capture(
    cmd: Sequence[str],
    *,
    check: bool = True,
    env: dict[str, str] | None = None,
    cwd: str | None = None,
    input: str | None = None,
    strip: bool = True,
) -> str:
    """Run ``cmd`` and return its stdout as a string."""
    log.debug("capture: %s", " ".join(cmd))
    result = subprocess.run(
        list(cmd),
        check=check,
        env=env,
        cwd=cwd,
        input=input,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip() if strip else result.stdout


def try_run(cmd: Sequence[str], **kwargs: object) -> bool:
    """Run ``cmd`` and return True on success, False on any error.

    Useful when the failure case is part of normal flow (e.g. probing).
    """
    try:
        run(cmd, check=True, **kwargs)  # type: ignore[arg-type]
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
