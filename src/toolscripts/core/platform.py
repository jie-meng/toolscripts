"""Platform detection and gating.

Use ``require_platform("macos")`` at the top of a command's ``main()`` to
print a friendly warning and exit cleanly (status 0) when the current OS is
unsupported.
"""

from __future__ import annotations

import sys

_ALIASES = {
    "darwin": "macos",
    "macos": "macos",
    "mac": "macos",
    "osx": "macos",
    "linux": "linux",
    "windows": "windows",
    "win32": "windows",
    "win": "windows",
}


def current_platform() -> str:
    """Return one of: ``macos``, ``linux``, ``windows``, or the raw ``sys.platform`` value."""
    p = sys.platform
    if p == "darwin":
        return "macos"
    if p.startswith("linux"):
        return "linux"
    if p in ("win32", "cygwin"):
        return "windows"
    return p


def is_macos() -> bool:
    return current_platform() == "macos"


def is_linux() -> bool:
    return current_platform() == "linux"


def is_windows() -> bool:
    return current_platform() == "windows"


def require_platform(*platforms: str) -> None:
    """Exit with a friendly warning if the current platform is not supported.

    Accepts any of: ``macos``, ``linux``, ``windows`` (and common aliases).
    Exits with status 0 - the command is intentionally a no-op on this OS,
    not a failure.
    """
    normalized = {_ALIASES.get(p.lower(), p.lower()) for p in platforms}
    cur = current_platform()
    if cur in normalized:
        return

    from toolscripts.core.log import get_logger

    log = get_logger("platform")
    pretty = ", ".join(sorted(normalized))
    log.warning(
        "this command is only supported on %s, current platform: %s",
        pretty,
        cur,
    )
    sys.exit(0)
