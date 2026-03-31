#!/usr/bin/env python3
"""Interactive model selector for aido.

Lists all 'free' models from opencode and lets the user pick one
using a curses single-select UI. The selection is saved to
~/.config/toolscripts/config.json for use by the aido command.
"""

from __future__ import annotations

import curses
import json
import subprocess
import sys
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "toolscripts"
CONFIG_FILE = CONFIG_DIR / "config.json"
CONFIG_KEY = "aido_model"

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
NC = "\033[0m"


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def save_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def fetch_free_models() -> list[str]:
    try:
        result = subprocess.run(
            ["opencode", "models"],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        print(f"{RED}Error: 'opencode' not found in PATH.{NC}", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"{RED}Error running 'opencode models': {e}{NC}", file=sys.stderr)
        sys.exit(1)

    return [line for line in result.stdout.splitlines() if "free" in line.lower()]


def curses_single_select(
    stdscr: curses.window,
    title: str,
    items: list[str],
    current: int,
) -> int | None:
    """Single-select curses UI. Returns selected index or None if cancelled."""
    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)

    cursor = current
    scroll_offset = 0

    def draw() -> None:
        nonlocal scroll_offset
        stdscr.clear()
        max_y, max_x = stdscr.getmaxyx()

        stdscr.addstr(0, 0, title, curses.A_BOLD)
        hint = "↑/↓ or i/j move  |  Enter select  |  q quit"
        stdscr.addstr(1, 0, hint, curses.color_pair(3))

        list_start_row = 3
        visible_rows = max_y - list_start_row - 2

        # Keep cursor visible
        nonlocal scroll_offset
        if cursor < scroll_offset:
            scroll_offset = cursor
        elif cursor >= scroll_offset + visible_rows:
            scroll_offset = cursor - visible_rows + 1

        for idx in range(visible_rows):
            item_idx = idx + scroll_offset
            if item_idx >= len(items):
                break
            item = items[item_idx]
            is_cursor = item_idx == cursor
            prefix = "▶ " if is_cursor else "  "
            attr = curses.A_REVERSE if is_cursor else 0
            color = curses.color_pair(2) if is_cursor else 0
            display = f"{prefix}{item}"
            try:
                stdscr.addstr(list_start_row + idx, 0, display[:max_x - 1], attr | color)
            except curses.error:
                pass

        stdscr.refresh()

    while True:
        draw()
        key = stdscr.getch()

        if key in (curses.KEY_UP, ord("i"), ord("k")):
            cursor = (cursor - 1) % len(items)
        elif key in (curses.KEY_DOWN, ord("j")):
            cursor = (cursor + 1) % len(items)
        elif key in (curses.KEY_ENTER, 10, 13):
            return cursor
        elif key in (ord("q"), 27):
            return None


def main() -> None:
    models = fetch_free_models()
    if not models:
        print(f"{YELLOW}No free models found.{NC}", file=sys.stderr)
        sys.exit(1)

    config = load_config()
    saved_model = config.get(CONFIG_KEY, "")

    # Pre-position cursor on the currently saved model
    current_idx = 0
    if saved_model in models:
        current_idx = models.index(saved_model)

    selected_idx = curses.wrapper(
        curses_single_select,
        f"Select a free model for aido  ({len(models)} available)",
        models,
        current_idx,
    )

    if selected_idx is None:
        print("Cancelled. No changes made.")
        return

    chosen = models[selected_idx]
    config[CONFIG_KEY] = chosen
    save_config(config)
    print(f"{GREEN}Model saved:{NC} {chosen}")


if __name__ == "__main__":
    main()
