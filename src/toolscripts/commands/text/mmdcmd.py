"""``mmdcmd`` - interactive Mermaid CLI wrapper (no flags needed).

Launch it in any directory that holds ``.mmd`` files. A curses wizard walks
you through: pick the input file, edit the output name, choose a theme and
background, pick an output format, and set the scale (sharpness) for raster
outputs, then runs ``mmdc`` and prints the exact command it used so you can
learn the flags.

Requires the Mermaid CLI (``mmdc``) on PATH — install with ``npm i -g @mermaid-js/mermaid-cli``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.mermaid_options import (
    BACKGROUNDS,
    FORMATS,
    SCALES,
    THEMES,
    background_labels,
    build_mmdc_command,
    cmd_string,
    first_key,
    format_labels,
    label_for,
    scale_labels,
    theme_labels,
)
from toolscripts.core.shell import CommandNotFoundError, require, run
from toolscripts.core.ui_curses import select_one

log = get_logger(__name__)


def _text_input(stdscr, prompt: str, default: str) -> str:
    """Read a line of text inside the curses UI, pre-filled with ``default``."""
    import curses

    height, width = stdscr.getmaxyx()
    stdscr.clear()
    stdscr.hline(0, 0, curses.ACS_HLINE, width)
    stdscr.addstr(0, 0, " Step 2 of 4 — output filename ", curses.A_BOLD)
    stdscr.addstr(2, 0, prompt, curses.A_BOLD)
    stdscr.addstr(3, 0, f"(leave empty for: {default})", curses.A_DIM)

    stdscr.move(5, 0)
    curses.echo()
    stdscr.refresh()
    try:
        raw = stdscr.getstr(5, 0).decode("utf-8", "replace").strip()
    except KeyboardInterrupt:
        raw = ""
    finally:
        curses.noecho()
    return raw or default


def _pick(stdscr, title: str, labels: list[str], table, default_value: str) -> str:
    """Show a single-select picker and return the chosen table value."""
    default_index = list(table).index(default_value)
    chosen = select_one(title, labels, default_index=default_index)
    if chosen is None:
        return ""
    return list(table.values())[chosen][0]


def _run_curses(stdscr) -> None:
    import curses

    mmd_files = sorted(p.name for p in Path.cwd().glob("*.mmd"))
    if not mmd_files:
        stdscr.addstr(0, 0, "No .mmd files found in the current directory.", curses.A_BOLD)
        stdscr.addstr(2, 0, "Press any key to exit.")
        stdscr.getch()
        return

    # Step 1: input file
    idx = select_one("Step 1 of 5 — select input .mmd file:", mmd_files)
    if idx is None:
        return
    input_file = mmd_files[idx]
    stem = Path(input_file).stem

    # Step 2: output name (editable)
    output_name = _text_input(stdscr, "Output filename (without extension):", stem)
    if not output_name:
        output_name = stem

    # Step 3: theme + background
    theme = _pick(
        stdscr,
        "Step 3 of 5 — select theme:",
        theme_labels(),
        THEMES,
        first_key(THEMES),
    )
    if not theme:
        return
    background = _pick(
        stdscr,
        "Step 3 of 5 — select background:",
        background_labels(),
        BACKGROUNDS,
        first_key(BACKGROUNDS),
    )
    if not background:
        return

    # Step 4: format
    fmt = _pick(
        stdscr,
        "Step 4 of 5 — select output format:",
        format_labels(),
        FORMATS,
        first_key(FORMATS),
    )
    if not fmt:
        return

    # Step 5: scale (sharpness) — only meaningful for raster outputs
    scale = _pick(
        stdscr,
        "Step 5 of 5 — select scale (sharpness):",
        scale_labels(),
        SCALES,
        "2",
    )
    if not scale:
        return

    output_file = f"{output_name}.{fmt}"
    cmd = build_mmdc_command(input_file, output_file, theme, background, scale)

    # Echo the command so the user learns the flags.
    print(cmd_string(cmd))
    print()

    try:
        run(cmd)
    except Exception as exc:  # noqa: BLE001
        log.error("mmdc failed: %s", exc)
        return
    log.success("saved: %s", output_file)
    log.info(
        "theme=%s  background=%s  format=%s  scale=%sx",
        label_for(THEMES, theme),
        label_for(BACKGROUNDS, background),
        label_for(FORMATS, fmt),
        scale,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mmdcmd",
        description="Interactive wizard around the Mermaid CLI (mmdc).",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        require("mmdc")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        log.error("install with: npm i -g @mermaid-js/mermaid-cli")
        raise SystemExit(1) from None

    import curses

    curses.wrapper(_run_curses)


if __name__ == "__main__":
    main()
