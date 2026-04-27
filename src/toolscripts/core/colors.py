"""ANSI color helpers with tty / NO_COLOR awareness.

The constants below evaluate to empty strings when colors are disabled, so
callers can safely f-string them without checking. Use ``colored(text, color)``
when you want a one-shot wrap with automatic reset.

Colors are disabled when:
    - stderr is not a TTY (e.g. piped to a file), AND
    - the caller hasn't explicitly forced colors via ``FORCE_COLOR=1``.
The standard ``NO_COLOR=1`` env var also disables colors unconditionally
(see https://no-color.org/).
"""

from __future__ import annotations

import os
import sys

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

BLACK = "\033[30m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"
GREY = "\033[90m"


def colors_enabled(stream=None) -> bool:
    """Return True if ANSI colors should be emitted on the given stream."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    s = stream if stream is not None else sys.stderr
    try:
        return bool(s.isatty())
    except (AttributeError, ValueError):
        return False


def enable_windows_ansi() -> None:
    """Enable ANSI escape processing on the Windows console (no-op elsewhere)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        for handle_id in (-11, -12):  # stdout, stderr
            handle = kernel32.GetStdHandle(handle_id)
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


def colored(text: str, color: str, *, bold: bool = False, stream=None) -> str:
    """Wrap ``text`` with ``color`` (and optional bold) if colors are enabled."""
    if not colors_enabled(stream):
        return text
    prefix = (BOLD if bold else "") + color
    return f"{prefix}{text}{RESET}"


enable_windows_ansi()
