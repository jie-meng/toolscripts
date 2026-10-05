"""Filesystem size helpers shared across commands (checkspace, agent-clean, ...)."""

from __future__ import annotations

import os
from pathlib import Path


def dir_size(path: Path) -> int:
    """Total bytes of files under *path*, skipping unreadable entries.

    ``path`` may point at a single file; non-directories are measured as a
    plain ``stat()``.
    """

    total = 0
    for root, _dirs, files in os.walk(path):
        base = Path(root)
        for fname in files:
            try:
                total += (base / fname).stat().st_size
            except OSError:
                continue
    return total


def path_size(path: Path) -> int:
    """Bytes used by a file or directory; ``0`` when missing or unreadable."""

    try:
        if path.is_dir():
            return dir_size(path)
        return path.stat().st_size
    except OSError:
        return 0


_SUFFIXES = (
    (1024**3, "G"),
    (1024**2, "M"),
    (1024, "K"),
    (1, "B"),
)


def human_size(size: int) -> str:
    """Format *size* bytes compactly, e.g. ``435M`` / ``1.2G`` / ``512B``."""

    for factor, suffix in _SUFFIXES:
        if size >= factor:
            value = size / factor
            return f"{value:.1f}{suffix}" if value < 10 else f"{value:.0f}{suffix}"
    return "0B"
