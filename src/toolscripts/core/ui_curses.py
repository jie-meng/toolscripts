"""Curses-based interactive selection UIs.

Provides a multi-select picker with arrow-key navigation, ``space`` to toggle,
``a`` to select/deselect all, ``Enter`` to confirm, ``q`` / Esc to cancel.

On Windows the standard library does not ship the ``curses`` module; install
``windows-curses`` (e.g. ``pip install windows-curses``) to enable this UI.
"""

from __future__ import annotations

import contextlib
import sys

from toolscripts.core import colors

colors.enable_windows_ansi()


def _ensure_curses_available() -> None:
    try:
        import curses  # noqa: F401
        return
    except ImportError:
        from toolscripts.core.log import get_logger

        log = get_logger(__name__)
        if sys.platform == "win32":
            log.error(
                "curses is not available on Windows by default. "
                "Install it with: pip install windows-curses"
            )
        else:
            log.error("curses module is not available on this Python build")
        sys.exit(1)


def multi_select(
    title: str,
    items: list[str],
    *,
    preselected: list[bool] | None = None,
    disabled: set[int] | None = None,
    selected_color: int = 5,
) -> list[int] | None:
    """Show a multi-select UI and return the chosen indices, or None on cancel."""
    _ensure_curses_available()
    import curses

    def _run(stdscr: curses.window) -> list[int] | None:
        return _multi_select_impl(
            stdscr,
            title,
            items,
            preselected,
            disabled,
            selected_color,
        )

    return curses.wrapper(_run)


def _multi_select_impl(
    stdscr,
    title: str,
    items: list[str],
    preselected: list[bool] | None,
    disabled: set[int] | None,
    selected_color: int,
) -> list[int] | None:
    import curses

    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_RED, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_WHITE, -1)
    curses.init_pair(5, curses.COLOR_GREEN, -1)

    disabled = disabled or set()
    selected = (
        list(preselected)
        if preselected
        else [i not in disabled for i in range(len(items))]
    )
    for i in disabled:
        selected[i] = False

    cursor = 0
    all_label = "Select All / Deselect All"
    total = 1 + len(items)
    enabled_count = len(items) - len(disabled)

    def next_enabled(pos: int, direction: int) -> int:
        candidate = (pos + direction) % total
        for _ in range(total):
            if candidate == 0 or candidate - 1 not in disabled:
                return candidate
            candidate = (candidate + direction) % total
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
        with contextlib.suppress(curses.error):
            stdscr.addstr(
                row, 0, f"  {marker}  {all_label}", attr | curses.color_pair(1)
            )

        row += 1
        with contextlib.suppress(curses.error):
            stdscr.addstr(row, 0, "  " + "-" * 40, curses.color_pair(1))

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
            with contextlib.suppress(curses.error):
                stdscr.addstr(row + i, 0, f"  {marker}  {item}", attr | color)

        count = sum(1 for i, s in enumerate(selected) if s and i not in disabled)
        with contextlib.suppress(curses.error):
            stdscr.addstr(
                row + len(items) + 1,
                0,
                f"  {count}/{enabled_count} selected",
                curses.color_pair(3),
            )

        stdscr.refresh()

    while True:
        draw()
        key = stdscr.getch()

        if key == curses.KEY_UP or key == ord("k"):
            cursor = next_enabled(cursor, -1)
        elif key == curses.KEY_DOWN or key == ord("j"):
            cursor = next_enabled(cursor, 1)
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
