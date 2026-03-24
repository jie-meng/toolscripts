#!/usr/bin/env python3
"""Shared curses UI helpers for interactive selection.

Provides multi-select UI with:
- Arrow keys / k,j to move
- Space to toggle selection
- 'a' to select/deselect all
- Enter to confirm, q to cancel
"""

from __future__ import annotations

import platform
import subprocess
import sys
from typing import Callable, Optional

IS_WINDOWS = platform.system() == "Windows"


def _enable_windows_ansi() -> None:
    if not IS_WINDOWS:
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        kernel32.SetConsoleMode(handle, mode.value | 4)
    except Exception:
        pass


def _ensure_curses() -> None:
    try:
        import curses as _  # noqa: F401
    except ImportError:
        if IS_WINDOWS:
            print("Installing windows-curses ...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "windows-curses"],
                stdout=subprocess.DEVNULL,
            )
        else:
            print("Error: curses module not available.")
            sys.exit(1)


_enable_windows_ansi()
_ensure_curses()

import curses


def curses_multi_select(
    stdscr: curses.window,
    title: str,
    items: list[str],
    preselected: list[bool] | None = None,
    disabled: set[int] | None = None,
    selected_color: int = 5,
) -> list[int] | None:
    """Interactive multi-select UI.

    Args:
        stdscr: Curses window
        title: Title displayed at top
        items: List of item labels
        preselected: Initial selection state (True=all selected)
        disabled: Set of indices that cannot be selected

    Returns:
        List of selected indices, or None if cancelled
    """
    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_RED, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_WHITE, -1)
    curses.init_pair(5, curses.COLOR_GREEN, -1)

    disabled = disabled or set()
    if preselected:
        selected = list(preselected)
    else:
        selected = [i not in disabled for i in range(len(items))]
    for i in disabled:
        selected[i] = False

    cursor = 0
    all_item = "Select All / Deselect All"
    total_items = 1 + len(items)
    enabled_count = len(items) - len(disabled)

    def _next_enabled(pos: int, direction: int) -> int:
        candidate = (pos + direction) % total_items
        attempts = 0
        while attempts < total_items:
            if candidate == 0 or candidate - 1 not in disabled:
                return candidate
            candidate = (candidate + direction) % total_items
            attempts += 1
        return 0

    def draw() -> None:
        stdscr.clear()
        stdscr.addstr(0, 0, title, curses.A_BOLD)
        hint = "Up/Down move | Space toggle | a all/none | Enter confirm | q quit"
        stdscr.addstr(1, 0, hint, curses.color_pair(3))

        row = 3
        enabled_sel = [s for i, s in enumerate(selected) if i not in disabled]
        all_selected = bool(enabled_sel) and all(enabled_sel)
        marker = "[x]" if all_selected else "[ ]"
        attr = curses.A_REVERSE if cursor == 0 else 0
        try:
            stdscr.addstr(
                row, 0, f"  {marker}  {all_item}", attr | curses.color_pair(1)
            )
        except curses.error:
            pass

        row += 1
        try:
            stdscr.addstr(row, 0, "  " + "-" * 40, curses.color_pair(1))
        except curses.error:
            pass

        row += 1
        for i, item in enumerate(items):
            is_disabled = i in disabled
            if is_disabled:
                marker = "[-]"
                attr = curses.A_DIM
                color = 0
            else:
                marker = "[x]" if selected[i] else "[ ]"
                attr = curses.A_REVERSE if cursor == i + 1 else 0
                color = (
                    curses.color_pair(selected_color)
                    if selected[i]
                    else curses.color_pair(4)
                )
            try:
                stdscr.addstr(row + i, 0, f"  {marker}  {item}", attr | color)
            except curses.error:
                pass

        count = sum(1 for i, s in enumerate(selected) if s and i not in disabled)
        try:
            stdscr.addstr(
                row + len(items) + 1,
                0,
                f"  {count}/{enabled_count} selected",
                curses.color_pair(3),
            )
        except curses.error:
            pass

        stdscr.refresh()

    while True:
        draw()
        key = stdscr.getch()

        if key == curses.KEY_UP or key == ord("k"):
            cursor = _next_enabled(cursor, -1)
        elif key == curses.KEY_DOWN or key == ord("j"):
            cursor = _next_enabled(cursor, 1)
        elif key == ord(" "):
            if cursor == 0:
                enabled_sel = [s for i, s in enumerate(selected) if i not in disabled]
                new_val = not (bool(enabled_sel) and all(enabled_sel))
                selected = [
                    new_val if i not in disabled else False for i in range(len(items))
                ]
            elif cursor - 1 not in disabled:
                selected[cursor - 1] = not selected[cursor - 1]
        elif key == ord("a"):
            enabled_sel = [s for i, s in enumerate(selected) if i not in disabled]
            new_val = not (bool(enabled_sel) and all(enabled_sel))
            selected = [
                new_val if i not in disabled else False for i in range(len(items))
            ]
        elif key in (curses.KEY_ENTER, 10, 13):
            return [i for i, s in enumerate(selected) if s and i not in disabled]
        elif key in (ord("q"), 27):
            return None


def run_curses_select(
    title: str,
    items: list[str],
    preselected: list[bool] | None = None,
    disabled: set[int] | None = None,
    selected_color: int = 5,
) -> list[int] | None:
    """Run the curses multi-select UI.

    Args:
        title: Title displayed at top
        items: List of item labels
        preselected: Initial selection state (True=all selected)
        disabled: Set of indices that cannot be selected
        selected_color: Color pair for selected items (5=green, 2=red)

    Returns:
        List of selected indices, or None if cancelled
    """
    return curses.wrapper(
        curses_multi_select, title, items, preselected, disabled, selected_color
    )
