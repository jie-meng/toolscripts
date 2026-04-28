"""Curses-based interactive selection UIs.

Provides a multi-select picker with arrow-key navigation, ``space`` to toggle,
``a`` to select/deselect all, ``Enter`` to confirm, ``q`` / Esc to cancel.

Also provides ``browse_commands(...)`` — a two-pane drill-down browser for
hierarchies of commands (used by ``toolscripts-list -i``).

On Windows the standard library does not ship the ``curses`` module; install
``windows-curses`` (e.g. ``pip install windows-curses``) to enable this UI.
"""

from __future__ import annotations

import contextlib
import sys
from collections.abc import Callable
from typing import NamedTuple

from toolscripts.core import colors

colors.enable_windows_ansi()


class BrowseEntry(NamedTuple):
    """A single command exposed to ``browse_commands``."""

    name: str
    group: str
    summary: str


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


def single_select(
    title: str,
    items: list[str],
    *,
    default_index: int | None = None,
) -> int | None:
    """Show a single-select UI and return the chosen index, or None on cancel.

    Use arrow keys (or j/k) to move, Enter to confirm, q or Esc to cancel.
    """
    _ensure_curses_available()
    import curses

    def _run(stdscr: curses.window) -> int | None:
        return _single_select_impl(stdscr, title, items, default_index)

    return curses.wrapper(_run)


def _single_select_impl(
    stdscr,
    title: str,
    items: list[str],
    default_index: int | None,
) -> int | None:
    import curses

    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_WHITE, -1)

    cursor = default_index if default_index is not None else 0
    cursor = max(0, min(cursor, len(items) - 1))

    def draw() -> None:
        stdscr.clear()
        stdscr.addstr(0, 0, title, curses.A_BOLD)
        hint = "Up/Down move | Enter confirm | q quit"
        stdscr.addstr(1, 0, hint, curses.color_pair(3))

        row = 3
        for i, item in enumerate(items):
            marker = ">" if i == cursor else " "
            attr = curses.A_BOLD | curses.A_REVERSE if i == cursor else 0
            color = curses.color_pair(2) if i == cursor else curses.color_pair(4)
            with contextlib.suppress(curses.error):
                stdscr.addstr(row + i, 0, f"  {marker}  {item}", attr | color)

        stdscr.refresh()

    while True:
        draw()
        key = stdscr.getch()

        if key == curses.KEY_UP or key == ord("k"):
            cursor = max(0, cursor - 1)
        elif key == curses.KEY_DOWN or key == ord("j"):
            cursor = min(len(items) - 1, cursor + 1)
        elif key in (curses.KEY_ENTER, 10, 13):
            return cursor
        elif key in (ord("q"), 27):
            return None


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
    selected = list(preselected) if preselected else [i not in disabled for i in range(len(items))]
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
            stdscr.addstr(row, 0, f"  {marker}  {all_label}", attr | curses.color_pair(1))

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
                color = curses.color_pair(selected_color) if selected[i] else curses.color_pair(4)
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
                selected = [new_val if i not in disabled else False for i in range(len(items))]
            elif cursor - 1 not in disabled:
                selected[cursor - 1] = not selected[cursor - 1]
        elif key == ord("a"):
            enabled_sel = [s for i, s in enumerate(selected) if i not in disabled]
            new_val = not (bool(enabled_sel) and all(enabled_sel))
            selected = [new_val if i not in disabled else False for i in range(len(items))]
        elif key in (curses.KEY_ENTER, 10, 13):
            return [i for i, s in enumerate(selected) if s and i not in disabled]
        elif key in (ord("q"), 27):
            return None


# ---------------------------------------------------------------------------
# Two-pane drill-down browser
# ---------------------------------------------------------------------------


def browse_commands(
    title: str,
    entries: list[BrowseEntry],
    *,
    detail_provider: Callable[[BrowseEntry], str],
) -> BrowseEntry | None:
    """Show a two-pane drill-down browser; return the picked entry or ``None``.

    Layout
    ------
    Left pane shows the currently active list (groups at the top level, then
    commands within a chosen group). Right pane shows the on-demand detail
    text for the highlighted command — typically its ``--help`` output.

    Keys
    ----
    ``j`` / ``Down``     move selection down
    ``k`` / ``Up``       move selection up
    ``g``                jump to first
    ``G``                jump to last
    ``Enter`` / ``l``    drill into group / pick command
    ``h`` / ``Backspace`` / ``Esc``   back to parent (top level: quit)
    ``/``                start a search filter (Enter to apply, Esc to clear)
    ``q``                quit
    """
    _ensure_curses_available()
    import curses

    if not entries:
        return None

    def _run(stdscr: curses.window) -> BrowseEntry | None:
        return _browse_commands_impl(stdscr, title, entries, detail_provider)

    return curses.wrapper(_run)


def _wrap_text(text: str, width: int) -> list[str]:
    """Word-wrap ``text`` to ``width``, preserving blank lines."""
    if width <= 0:
        return []
    out: list[str] = []
    for raw_line in text.splitlines():
        if not raw_line.strip():
            out.append("")
            continue
        line = raw_line.rstrip()
        while len(line) > width:
            cut = line.rfind(" ", 0, width)
            if cut <= 0:
                cut = width
            out.append(line[:cut])
            line = line[cut:].lstrip()
        out.append(line)
    return out


def _browse_commands_impl(
    stdscr,
    title: str,
    entries: list[BrowseEntry],
    detail_provider: Callable[[BrowseEntry], str],
) -> BrowseEntry | None:
    import curses

    with contextlib.suppress(curses.error):
        curses.curs_set(0)
    has_color = False
    with contextlib.suppress(curses.error):
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.init_pair(4, -1, -1)
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)
        has_color = True

    def cp(n: int) -> int:
        return curses.color_pair(n) if has_color else 0

    groups: dict[str, list[BrowseEntry]] = {}
    for entry in entries:
        groups.setdefault(entry.group, []).append(entry)
    for items in groups.values():
        items.sort(key=lambda e: e.name)
    group_names = sorted(groups)

    detail_cache: dict[str, list[str]] = {}
    last_detail_width = -1

    def get_detail_lines(entry: BrowseEntry, width: int) -> list[str]:
        nonlocal last_detail_width, detail_cache
        if width != last_detail_width:
            detail_cache = {}
            last_detail_width = width
        cached = detail_cache.get(entry.name)
        if cached is not None:
            return cached
        try:
            raw = detail_provider(entry)
        except Exception as exc:  # noqa: BLE001
            raw = f"(failed to load details: {exc})"
        lines = _wrap_text(raw or "(no details available)", width)
        detail_cache[entry.name] = lines
        return lines

    level = 0  # 0 = groups, 1 = commands within selected group
    cursor = [0, 0]
    top = [0, 0]
    selected_group: str | None = None
    search = ""
    search_active = False

    def current_items() -> list[str]:
        if level == 0:
            base = group_names
        else:
            base = [e.name for e in groups[selected_group]]  # type: ignore[index]
        if search:
            needle = search.lower()
            return [item for item in base if needle in item.lower()]
        return base

    def current_entry() -> BrowseEntry | None:
        if level != 1:
            return None
        items = current_items()
        if not items or cursor[1] >= len(items):
            return None
        name = items[cursor[1]]
        for e in groups[selected_group]:  # type: ignore[index]
            if e.name == name:
                return e
        return None

    def clamp_cursor() -> None:
        items = current_items()
        if not items:
            cursor[level] = 0
            top[level] = 0
            return
        cursor[level] = max(0, min(cursor[level], len(items) - 1))

    def draw() -> None:
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        if height < 6 or width < 40:
            with contextlib.suppress(curses.error):
                stdscr.addstr(0, 0, "terminal too small")
            stdscr.refresh()
            return

        left_w = max(24, min(40, width // 3))
        right_x = left_w + 2
        right_w = width - right_x - 1

        crumbs = title
        if level == 1 and selected_group:
            crumbs = f"{title}  >  {selected_group}"
        with contextlib.suppress(curses.error):
            stdscr.addstr(0, 0, crumbs[: width - 1], curses.A_BOLD | cp(1))

        if search_active:
            hint = f"/search: {search}_  (Enter apply, Esc clear)"
        elif level == 0:
            hint = "j/k move  Enter open  / search  q quit"
        else:
            hint = "j/k move  Enter help  h back  / search  q quit"
        with contextlib.suppress(curses.error):
            stdscr.addstr(1, 0, hint[: width - 1], cp(3))

        with contextlib.suppress(curses.error):
            stdscr.hline(2, 0, curses.ACS_HLINE, width)

        list_top = 3
        list_h = height - list_top - 1
        items = current_items()

        if cursor[level] < top[level]:
            top[level] = cursor[level]
        elif cursor[level] >= top[level] + list_h:
            top[level] = cursor[level] - list_h + 1

        for i in range(list_h):
            idx = top[level] + i
            if idx >= len(items):
                break
            label = items[idx]
            attr = curses.A_REVERSE if idx == cursor[level] else 0
            if level == 0:
                count = len(groups[label])
                text = f"  {label}  ({count})"
                color = cp(5)
            else:
                text = f"  {label}"
                color = cp(2)
            with contextlib.suppress(curses.error):
                stdscr.addstr(list_top + i, 0, text[:left_w].ljust(left_w), attr | color)

        with contextlib.suppress(curses.error):
            stdscr.vline(list_top, left_w + 1, curses.ACS_VLINE, list_h)

        if level == 1:
            entry = current_entry()
            if entry is not None:
                with contextlib.suppress(curses.error):
                    stdscr.addstr(
                        list_top,
                        right_x,
                        entry.name[:right_w],
                        curses.A_BOLD | cp(2),
                    )
                if entry.summary:
                    summary_lines = _wrap_text(entry.summary, right_w)
                    for i, line in enumerate(summary_lines[: max(0, list_h - 3)]):
                        with contextlib.suppress(curses.error):
                            stdscr.addstr(list_top + 1 + i, right_x, line, cp(4))
                    detail_offset = 1 + len(summary_lines[: max(0, list_h - 3)]) + 1
                else:
                    detail_offset = 2
                detail_lines = get_detail_lines(entry, right_w)
                for i, line in enumerate(detail_lines[: list_h - detail_offset]):
                    with contextlib.suppress(curses.error):
                        stdscr.addstr(
                            list_top + detail_offset + i,
                            right_x,
                            line,
                            cp(4),
                        )
        else:
            msg = "Pick a domain on the left, press Enter to drill in."
            with contextlib.suppress(curses.error):
                stdscr.addstr(list_top, right_x, msg[:right_w], cp(3))

        status = f"  {len(items)} item(s)"
        if search:
            status += f"  filter: {search!r}"
        with contextlib.suppress(curses.error):
            stdscr.addstr(height - 1, 0, status[: width - 1], cp(3))

        stdscr.refresh()

    while True:
        clamp_cursor()
        draw()
        key = stdscr.getch()

        if search_active:
            if key in (curses.KEY_ENTER, 10, 13):
                search_active = False
            elif key == 27:  # Esc
                search = ""
                search_active = False
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                search = search[:-1]
            elif 32 <= key < 127:
                search += chr(key)
                cursor[level] = 0
                top[level] = 0
            continue

        if key in (ord("q"),):
            return None
        if key == 27:  # Esc at top level quits, otherwise go up a level
            if level == 0:
                return None
            level = 0
            search = ""
            continue
        if key in (curses.KEY_UP, ord("k")):
            cursor[level] = max(0, cursor[level] - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            items = current_items()
            cursor[level] = min(max(0, len(items) - 1), cursor[level] + 1)
        elif key in (curses.KEY_PPAGE,):
            cursor[level] = max(0, cursor[level] - 10)
        elif key in (curses.KEY_NPAGE,):
            items = current_items()
            cursor[level] = min(max(0, len(items) - 1), cursor[level] + 10)
        elif key == ord("g"):
            cursor[level] = 0
        elif key == ord("G"):
            items = current_items()
            cursor[level] = max(0, len(items) - 1)
        elif key in (curses.KEY_ENTER, 10, 13, ord("l"), curses.KEY_RIGHT):
            items = current_items()
            if not items:
                continue
            if level == 0:
                selected_group = items[cursor[0]]
                level = 1
                cursor[1] = 0
                top[1] = 0
                search = ""
            else:
                entry = current_entry()
                if entry is not None:
                    return entry
        elif key in (curses.KEY_BACKSPACE, 127, 8, ord("h"), curses.KEY_LEFT):
            if level == 1:
                level = 0
                search = ""
        elif key == ord("/"):
            search_active = True
            search = ""
            cursor[level] = 0
            top[level] = 0
