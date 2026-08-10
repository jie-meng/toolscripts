"""Shared option tables and command builder for the Mermaid CLI (``mmdc``).

Both the ``mermaid`` and ``mmdcmd`` commands shell out to ``mmdc``. This module
is the single source of truth for the selectable themes, backgrounds, and
output formats, plus the flag layout, so the two commands can't drift apart.
"""

from __future__ import annotations

from collections.abc import Sequence

# value -> (mmdc token, human label)
THEMES: dict[str, tuple[str, str]] = {
    "default": ("default", "Default Theme"),
    "dark": ("dark", "Dark Theme"),
    "forest": ("forest", "Forest Theme"),
    "neutral": ("neutral", "Neutral Theme"),
}

BACKGROUNDS: dict[str, tuple[str, str]] = {
    "white": ("white", "White (default)"),
    "transparent": ("transparent", "Transparent"),
    "black": ("black", "Black"),
    "#F0F0F0": ("#F0F0F0", "Light Gray"),
    "red": ("red", "Red"),
}

FORMATS: dict[str, tuple[str, str]] = {
    "png": ("png", "PNG image"),
    "svg": ("svg", "SVG vector"),
    "pdf": ("pdf", "PDF document"),
}

# Puppeteer scale factor — higher means a sharper raster (PNG/PDF). SVG ignores it.
SCALES: dict[str, tuple[str, str]] = {
    "1": ("1", "1x (default, may look blurry)"),
    "2": ("2", "2x (sharp, recommended)"),
    "3": ("3", "3x (very sharp, larger file)"),
    "4": ("4", "4x (maximum)"),
}


def build_mmdc_command(
    input_file: str,
    output_file: str,
    theme: str | None = None,
    background: str | None = None,
    scale: str | None = None,
) -> list[str]:
    """Build the ``mmdc`` argument list for the given options."""
    cmd: list[str] = ["mmdc", "-i", input_file, "-o", output_file]
    if theme:
        cmd.extend(["-t", theme])
    if background:
        cmd.extend(["-b", background])
    if scale and scale != "1":
        cmd.extend(["-s", scale])
    return cmd


def theme_labels() -> list[str]:
    return [f"{v} — {label}" for v, (_, label) in THEMES.items()]


def background_labels() -> list[str]:
    return [f"{v} — {label}" for v, (_, label) in BACKGROUNDS.items()]


def format_labels() -> list[str]:
    return [f"{v} — {label}" for v, (_, label) in FORMATS.items()]


def scale_labels() -> list[str]:
    return [f"{v} — {label}" for v, (_, label) in SCALES.items()]


def numbered(table: dict[str, tuple[str, str]]) -> dict[str, tuple[str, str]]:
    """Return a copy keyed by "1".."N" for the legacy numbered-choice UI."""
    return {str(i): v for i, v in enumerate(table.values(), 1)}


def first_key(table: dict[str, tuple[str, str]]) -> str:
    """Return the first key of a table (used as the default selection)."""
    return next(iter(table))


def label_for(table: dict[str, tuple[str, str]], value: str) -> str:
    """Return the human label for a stored value, or the value itself."""
    entry = table.get(value)
    return entry[1] if entry else value


def cmd_string(cmd: Sequence[str]) -> str:
    """Render a command list as a copy-pasteable shell string."""
    return " ".join(cmd)
