"""``android-log`` - interactive curses-based logcat viewer for Android devices.

Provides a real-time log stream with log level filtering, text filtering,
search highlighting, and one-key copy/clear operations.

Requires ``adb`` on PATH.

Layout::

    ┌──────────────────────────────────────────────────────────────┐
    │  android-log · <model> (<serial>)                            │
    ├──────────────┬───────────────────────────────────────────────┤
    │ LEVEL        │                                               │
    │ > d Debug    │            LOG OUTPUT                         │
    │   i Info     │  06-08 12:00:01 D MyApp: Starting...         │
    │   w Warn     │  06-08 12:00:01 I Activity: Created           │
    │   e Error    │  ...                                           │
    │   f Fatal    │                                               │
    │              │                                               │
    │ FILTER       │                                               │
    │ > [MyApp]    │                                               │
    │ SEARCH       │                                               │
    │ > [keyword]  │                                               │
    ├──────────────┴───────────────────────────────────────────────┤
    │ level:d  filter:MyApp  search:keyword  |  f filter | / search│
    └──────────────────────────────────────────────────────────────┘

Keybindings:

- ``f`` Enter filter mode · ``Enter`` Confirm · ``Esc`` Cancel
- ``/`` Enter search mode (vim-like) · ``n``/``N`` next/prev match
- ``-``/``=`` Cycle log level (previous/next)
- ``e`` Freeze/unfreeze log stream
- ``v`` Enter visual select mode (frozen only)
- ``k``/``j`` or arrows scroll · ``u``/``d`` half page · ``g``/``G`` top/bottom
- ``y`` Copy selected (visual) or all visible (normal)
- ``c`` Clear all collected logs
- ``q`` Quit
"""

from __future__ import annotations

import argparse
import contextlib
import curses
import queue
import re
import threading
from collections import deque
from dataclasses import dataclass, field
from subprocess import PIPE, Popen

from toolscripts.adb.devices import get_device_model, select_device
from toolscripts.core.clipboard import copy_to_clipboard
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import require

log = get_logger(__name__)

LEVELS = ["Verbose", "Debug", "Info", "Warn", "Error", "Fatal"]

_COLORS = {
    "Verbose": 6,
    "Debug": 4,
    "Info": 2,
    "Warn": 3,
    "Error": 1,
    "Fatal": 5,
}

_THREADTIME_RE = re.compile(
    r"(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+(\d+)\s+(\d+)\s+([VDIWEF])\s+(\S+?)\s*:\s(.*)"
)
_BRIEF_RE = re.compile(r"([VDIWEF])/(.+?)\(\s*(\d+)\):\s(.*)")
_PRIORITY_TO_LEVEL = {
    "V": "Verbose",
    "D": "Debug",
    "I": "Info",
    "W": "Warn",
    "E": "Error",
    "F": "Fatal",
}
_PRIORITY_COLORS = {"V": 6, "D": 4, "I": 2, "W": 3, "E": 1, "F": 5}
_PRIORITY_SELECTED = {"V": 15, "D": 13, "I": 11, "W": 12, "E": 10, "F": 14}


@dataclass
class LogEntry:
    timestamp: str
    pid: int
    tid: int
    priority: str
    tag: str
    message: str
    raw: str = field(repr=False, default="")


def _parse_logcat_line(line: str) -> LogEntry | None:
    m = _THREADTIME_RE.match(line)
    if m:
        return LogEntry(
            timestamp=m.group(1),
            pid=int(m.group(2)),
            tid=int(m.group(3)),
            priority=m.group(4),
            tag=m.group(5).strip(),
            message=m.group(6),
            raw=line,
        )
    m = _BRIEF_RE.match(line)
    if m:
        return LogEntry(
            timestamp="",
            pid=int(m.group(3)),
            tid=0,
            priority=m.group(1),
            tag=m.group(2).strip(),
            message=m.group(4),
            raw=line,
        )
    return None


class LogViewer:
    """Curses-based logcat viewer with level, text filtering, and search."""

    def __init__(self, device: str, max_logs: int = 50_000) -> None:
        self.device = device
        self.model = get_device_model(device)

        self.logs: deque[LogEntry] = deque(maxlen=max_logs)
        self.current_level = "Debug"
        self.log_top = 0
        self.auto_scroll = True

        self.filter_text = ""
        self.filter_mode = False

        self.search_text = ""
        self.search_mode = False
        self.search_match_idx = -1

        self.frozen = False
        self._snapshot: list[LogEntry] | None = None
        self.cursor = 0

        self.visual_mode = False
        self.selected: set[int] = set()
        self.visual_anchor = 0

        self.status_msg = ""

        self._log_lock = threading.Lock()
        self._entry_queue: queue.Queue[LogEntry | None] = queue.Queue()
        self._stop_event = threading.Event()
        self._process: Popen[str] | None = None
        self._visible_log_h = 21

    def _init_colors(self) -> None:
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_RED, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.init_pair(4, curses.COLOR_BLUE, -1)
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)
        curses.init_pair(6, curses.COLOR_CYAN, -1)
        if curses.COLORS >= 256:
            sel_bg = 237
        else:
            sel_bg = curses.COLOR_WHITE
        curses.init_pair(10, curses.COLOR_RED, sel_bg)
        curses.init_pair(11, curses.COLOR_GREEN, sel_bg)
        curses.init_pair(12, curses.COLOR_YELLOW, sel_bg)
        curses.init_pair(13, curses.COLOR_BLUE, sel_bg)
        curses.init_pair(14, curses.COLOR_MAGENTA, sel_bg)
        curses.init_pair(15, curses.COLOR_CYAN, sel_bg)
        curses.init_pair(20, 94, -1)  # brown (color 94) on default
        curses.init_pair(21, 94, 228)  # brown on light yellow (current match)
        curses.init_pair(22, -1, 237)  # default fg on dark gray (other matches)
        self._SEARCH_CUR = curses.color_pair(21) | curses.A_BOLD
        self._SEARCH_OTH = curses.color_pair(22)

    def _cp(self, n: int) -> int:
        return curses.color_pair(n)

    def _get_display_list(self) -> list[LogEntry]:
        if self._snapshot is not None:
            return self._snapshot
        return [e for e in self.logs if self._passes_filter(e)]

    def _find_search_matches(self, entry: LogEntry) -> list[re.Match[str]]:
        """Return all match objects for search_text in entry's raw line."""
        if not self.search_text:
            return []
        try:
            return list(re.finditer(re.escape(self.search_text), entry.raw, re.IGNORECASE))
        except re.error:
            return []

    def _draw_header(self, stdscr: curses.window) -> None:
        _, w = stdscr.getmaxyx()
        title = f"android-log · {self.model} ({self.device})"
        with contextlib.suppress(curses.error):
            stdscr.addnstr(0, 0, title, w - 1, curses.A_BOLD | self._cp(6))

    def _draw_level_panel(self, stdscr: curses.window, pw: int) -> None:
        level_short = {
            "Verbose": "v",
            "Debug": "d",
            "Info": "i",
            "Warn": "w",
            "Error": "e",
            "Fatal": "f",
        }
        with contextlib.suppress(curses.error):
            stdscr.addnstr(2, 0, "LEVEL", pw - 1, curses.A_BOLD)
        for i, level in enumerate(LEVELS):
            marker = "> " if level == self.current_level else "  "
            text = f"{marker}  {level_short[level]} {level}"
            color = self._cp(_COLORS[level]) if level == self.current_level else 0
            with contextlib.suppress(curses.error):
                stdscr.addnstr(3 + i, 0, text, pw - 1, color)

    def _draw_filter_panel(self, stdscr: curses.window, pw: int) -> None:
        with contextlib.suppress(curses.error):
            stdscr.addnstr(10, 0, "FILTER", pw - 1, curses.A_BOLD)
        if self.filter_mode:
            display = f"> [{self.filter_text}\u2588]"
            color = self._cp(6)
        elif self.filter_text:
            display = f"> [{self.filter_text}]"
            color = self._cp(2)
        else:
            display = "> [_]"
            color = self._cp(4)
        with contextlib.suppress(curses.error):
            stdscr.addnstr(11, 0, display, pw - 1, color | curses.A_UNDERLINE)

    def _draw_search_panel(self, stdscr: curses.window, pw: int) -> None:
        with contextlib.suppress(curses.error):
            stdscr.addnstr(13, 0, "SEARCH", pw - 1, curses.A_BOLD)
        if self.search_mode:
            display = f"> [{self.search_text}\u2588]"
            color = self._cp(20)
        elif self.search_text:
            display = f"> [{self.search_text}]"
            color = self._cp(3)
        else:
            display = "> [_]"
            color = self._cp(4)
        with contextlib.suppress(curses.error):
            stdscr.addnstr(14, 0, display, pw - 1, color | curses.A_UNDERLINE)

    def _draw_log_area(self, stdscr: curses.window, panel_w: int) -> None:
        h, w = stdscr.getmaxyx()
        log_w = w - panel_w - 2
        if log_w <= 0:
            return
        log_h = h - 3
        self._visible_log_h = log_h
        log_x = panel_w + 1

        with contextlib.suppress(curses.error):
            stdscr.vline(2, panel_w, curses.ACS_VLINE, log_h)

        display = self._get_display_list()

        if self.auto_scroll and display and not self.frozen:
            self.log_top = max(0, len(display) - log_h)
        self.log_top = max(0, self.log_top)
        if display and self.log_top > len(display) - log_h:
            self.log_top = max(0, len(display) - log_h)

        visible = display[self.log_top : self.log_top + log_h]
        for i, entry in enumerate(visible):
            line_idx = self.log_top + i
            color = self._cp(_PRIORITY_COLORS.get(entry.priority, 4))
            prefix = " "

            if self.frozen and not self.visual_mode:
                is_cursor = line_idx == self.cursor
                if is_cursor:
                    prefix = ">"
                    color = curses.A_REVERSE | color | curses.A_BOLD
                else:
                    prefix = " "
            elif self.visual_mode:
                is_cursor = line_idx == self.cursor
                is_selected = line_idx in self.selected
                if is_cursor and is_selected:
                    prefix = ">"
                    color = curses.A_BOLD | self._cp(_PRIORITY_SELECTED.get(entry.priority, 13))
                elif is_cursor:
                    prefix = ">"
                    color = curses.A_REVERSE | color | curses.A_BOLD
                elif is_selected:
                    prefix = "*"
                    color = self._cp(_PRIORITY_SELECTED.get(entry.priority, 13))
                else:
                    prefix = " "
            elif line_idx in self.selected:
                prefix = "*"
                color = curses.A_BOLD | self._cp(2)

            text = f"{prefix} {entry.raw.rstrip()}"
            text_len = len(text)
            with contextlib.suppress(curses.error):
                stdscr.addnstr(2 + i, log_x, text, log_w, color)
            if self.search_text and not self.search_mode:
                self._apply_search_highlight(stdscr, 2 + i, log_x, log_w, entry, text_len)

        remaining = len(display) - self.log_top - log_h
        if remaining > 0:
            with contextlib.suppress(curses.error):
                stdscr.addnstr(h - 1, log_x, f"  ...{remaining} more", log_w, self._cp(3))
        elif not display and self.logs:
            with contextlib.suppress(curses.error):
                stdscr.addnstr(2, log_x, " (no logs match current filter)", log_w, self._cp(4))
        elif not self.logs:
            with contextlib.suppress(curses.error):
                stdscr.addnstr(2, log_x, " Waiting for logcat output...", log_w, self._cp(4))

    def _draw_status_bar(self, stdscr: curses.window) -> None:
        h, w = stdscr.getmaxyx()
        parts: list[str] = []
        parts.append(f"level:{self.current_level[0].lower()}")
        if self.filter_text:
            parts.append(f"filter:{self.filter_text}")
        if self.search_text:
            parts.append(f"search:{self.search_text}")
        if self.selected:
            parts.append(f"selected:{len(self.selected)}")

        if self.filter_mode:
            hints = "type to filter | Enter confirm | Esc cancel"
        elif self.search_mode:
            hints = "type to search | Enter confirm | Esc cancel"
        elif self.visual_mode:
            hints = "k/j/u/d select | g/G top/bottom | y copy | Esc exit visual"
        elif self.frozen:
            hints = "e unfreeze | v select | / search | k/j/u/d scroll | g/G top/bottom | y copy | q quit"
        else:
            hints = "k/j/u/d scroll | g/G top/bottom | f filter | / search | - = level | e freeze | c clear | y copy | q quit"
        status = "  ".join(parts) + "  |  " + hints

        if self.status_msg:
            bar = self.status_msg
            self.status_msg = ""
        else:
            bar = status
        with contextlib.suppress(curses.error):
            stdscr.addnstr(h - 1, 0, bar, w - 1, self._cp(3))

    def _draw(self, stdscr: curses.window) -> None:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        if h < 10 or w < 40:
            with contextlib.suppress(curses.error):
                stdscr.addstr(0, 0, "Terminal too small (need 40x10)")
            stdscr.refresh()
            return

        panel_w = min(18, w // 5)
        self._draw_header(stdscr)
        self._draw_level_panel(stdscr, panel_w)
        self._draw_filter_panel(stdscr, panel_w)
        self._draw_search_panel(stdscr, panel_w)
        self._draw_log_area(stdscr, panel_w)
        self._draw_status_bar(stdscr)
        stdscr.refresh()

    def _handle_key(self, key: int) -> bool:
        if self.filter_mode:
            return self._handle_filter_key(key)
        if self.search_mode:
            return self._handle_search_key(key)
        if self.visual_mode:
            return self._handle_visual_key(key)
        return self._handle_normal_key(key)

    def _handle_normal_key(self, key: int) -> bool:
        if key == ord("q"):
            return False

        if self.frozen:
            return self._handle_frozen_key(key)

        if key == ord("f"):
            self.filter_mode = True
            curses.curs_set(1)
        elif key == ord("/"):
            self.search_mode = True
            curses.curs_set(1)
        elif key == ord("n") and self.search_text:
            self._search_next()
        elif key == ord("N") and self.search_text:
            self._search_prev()
        elif key == ord("-"):
            idx = LEVELS.index(self.current_level)
            self.current_level = LEVELS[(idx - 1) % len(LEVELS)]
            self.status_msg = f"  Level: {self.current_level}"
        elif key == ord("="):
            idx = LEVELS.index(self.current_level)
            self.current_level = LEVELS[(idx + 1) % len(LEVELS)]
            self.status_msg = f"  Level: {self.current_level}"
        elif key == ord("e"):
            self._freeze()
        elif key == ord("c"):
            self.logs.clear()
            self.log_top = 0
            self.selected.clear()
            self.status_msg = "  Logs cleared"
        elif key == ord("y"):
            self._copy_visible_logs()
        elif key in (curses.KEY_UP, ord("k")):
            self.log_top = max(0, self.log_top - 1)
            self.auto_scroll = False
        elif key in (curses.KEY_DOWN, ord("j")):
            self.auto_scroll = True
        elif key == curses.KEY_PPAGE:
            self.log_top = max(0, self.log_top - 10)
            self.auto_scroll = False
        elif key == curses.KEY_NPAGE:
            self.auto_scroll = True
        elif key == ord("u"):
            half = self._visible_log_h // 2
            self.log_top = max(0, self.log_top - half)
            self.auto_scroll = False
        elif key == ord("d"):
            display = self._get_display_list()
            half = self._visible_log_h // 2
            self.log_top = min(self.log_top + half, max(0, len(display) - self._visible_log_h))
            if self.log_top >= max(0, len(display) - self._visible_log_h):
                self.auto_scroll = True
        elif key == ord("g"):
            self.log_top = 0
            self.auto_scroll = False
        elif key == ord("G"):
            self.auto_scroll = True

        return True

    def _handle_frozen_key(self, key: int) -> bool:
        if key == ord("q"):
            return False

        if key == ord("e"):
            self._unfreeze()
        elif key == ord("v"):
            self._enter_visual_mode()
        elif key == ord("f"):
            self.filter_mode = True
            curses.curs_set(1)
        elif key == ord("/"):
            self.search_mode = True
            curses.curs_set(1)
        elif key == ord("n") and self.search_text:
            self._search_next()
        elif key == ord("N") and self.search_text:
            self._search_prev()
        elif key == ord("-"):
            idx = LEVELS.index(self.current_level)
            self.current_level = LEVELS[(idx - 1) % len(LEVELS)]
            self.status_msg = f"  Level: {self.current_level}"
        elif key == ord("="):
            idx = LEVELS.index(self.current_level)
            self.current_level = LEVELS[(idx + 1) % len(LEVELS)]
            self.status_msg = f"  Level: {self.current_level}"
        elif key == ord("y"):
            self._copy_frozen_at_cursor()
        elif key == ord("c"):
            self.logs.clear()
            self.log_top = 0
            self.selected.clear()
            self._unfreeze()
            self.status_msg = "  Logs cleared"
        elif key in (curses.KEY_UP, ord("k")):
            display = self._get_display_list()
            self.cursor = max(0, self.cursor - 1)
            self._ensure_cursor_visible()
        elif key in (curses.KEY_DOWN, ord("j")):
            display = self._get_display_list()
            self.cursor = min(self.cursor + 1, max(0, len(display) - 1))
            self._ensure_cursor_visible()
        elif key == ord("g"):
            self.cursor = 0
            self.log_top = 0
        elif key == ord("G"):
            display = self._get_display_list()
            self.cursor = max(0, len(display) - 1)
            self._ensure_cursor_visible()
        elif key == ord("u"):
            half = self._visible_log_h // 2
            self.cursor = max(0, self.cursor - half)
            self._ensure_cursor_visible()
        elif key == ord("d"):
            display = self._get_display_list()
            half = self._visible_log_h // 2
            self.cursor = min(self.cursor + half, max(0, len(display) - 1))
            self._ensure_cursor_visible()

        return True

    def _handle_visual_key(self, key: int) -> bool:
        display = self._get_display_list()
        max_idx = len(display) - 1

        if key == 27 or key == ord("v"):  # Esc - exit visual, stay frozen
            self._exit_visual_mode()
        elif key == ord("e"):  # e - exit visual AND unfreeze
            self._exit_visual_mode()
            self._unfreeze()
        elif key == ord("f"):  # f - enter filter from visual
            self._exit_visual_mode()
            self.filter_mode = True
            curses.curs_set(1)
        elif (
            key == ord("/") and self.search_text or key == ord("n") and self.search_text
        ):  # / then n/N in visual
            self._search_next()
        elif key == ord("N") and self.search_text:
            self._search_prev()
        elif key == ord("j") or key == curses.KEY_DOWN:
            self.cursor = min(self.cursor + 1, max_idx)
            self._rebuild_selection()
        elif key == ord("k") or key == curses.KEY_UP:
            self.cursor = max(self.cursor - 1, 0)
            self._rebuild_selection()
        elif key == ord("g"):
            self.cursor = 0
            self._rebuild_selection()
        elif key == ord("G"):
            self.cursor = max_idx
            self._rebuild_selection()
        elif key == ord("u"):
            half = self._visible_log_h // 2
            self.cursor = max(0, self.cursor - half)
            self._rebuild_selection()
        elif key == ord("d"):
            half = self._visible_log_h // 2
            self.cursor = min(self.cursor + half, max_idx)
            self._rebuild_selection()
        elif key == ord("y"):
            self._copy_selected()
            self._exit_visual_mode()

        self._ensure_cursor_visible()
        return True

    def _handle_filter_key(self, key: int) -> bool:
        if key == 27:
            self.filter_mode = False
            curses.curs_set(0)
        elif key in (curses.KEY_ENTER, 10, 13):
            self.filter_mode = False
            curses.curs_set(0)
            if self.frozen and self.filter_text:
                self._refresh_snapshot()
            self.status_msg = (
                f"  Filter: {self.filter_text}" if self.filter_text else "  Filter cleared"
            )
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            if self.filter_text:
                self.filter_text = self.filter_text[:-1]
                if self.frozen:
                    self._refresh_snapshot()
                if not self.filter_text:
                    self.status_msg = "  Filter cleared"
        elif 32 <= key < 127:
            self.filter_text += chr(key)
            if self.frozen:
                self._refresh_snapshot()

        return True

    def _handle_search_key(self, key: int) -> bool:
        if key == 27:
            self.search_mode = False
            curses.curs_set(0)
        elif key in (curses.KEY_ENTER, 10, 13):
            self.search_mode = False
            curses.curs_set(0)
            if self.search_text:
                self.search_match_idx = -1
                self._search_next()
            else:
                self.search_match_idx = -1
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            if self.search_text:
                self.search_text = self.search_text[:-1]
                self.search_match_idx = -1
                if not self.search_text:
                    self.status_msg = "  Search cleared"
        elif 32 <= key < 127:
            self.search_text += chr(key)
            self.search_match_idx = -1

        return True

    def _search_next(self) -> None:
        """Move to the next search match."""
        display = self._get_display_list()
        if not display or not self.search_text:
            return
        start = self.search_match_idx + 1
        for i in range(len(display)):
            idx = (start + i) % len(display)
            matches = self._find_search_matches(display[idx])
            if matches:
                self.search_match_idx = idx
                if idx < self.log_top or idx >= self.log_top + self._visible_log_h:
                    self.log_top = max(
                        0, min(idx - self._visible_log_h // 2, len(display) - self._visible_log_h)
                    )
                self.auto_scroll = False
                self.status_msg = f"  Match {idx + 1}/{len(display)}"
                return
        self.status_msg = "  No matches found"

    def _search_prev(self) -> None:
        """Move to the previous search match."""
        display = self._get_display_list()
        if not display or not self.search_text:
            return
        start = self.search_match_idx - 1
        for i in range(len(display)):
            idx = (start - i) % len(display)
            matches = self._find_search_matches(display[idx])
            if matches:
                self.search_match_idx = idx
                if idx < self.log_top or idx >= self.log_top + self._visible_log_h:
                    self.log_top = max(
                        0, min(idx - self._visible_log_h // 2, len(display) - self._visible_log_h)
                    )
                self.auto_scroll = False
                self.status_msg = f"  Match {idx + 1}/{len(display)}"
                return
        self.status_msg = "  No matches found"

    def _apply_search_highlight(
        self,
        stdscr: curses.window,
        row: int,
        col: int,
        width: int,
        entry: LogEntry,
        text_len: int,
    ) -> None:
        """Apply search highlighting via chgat() after text is drawn."""
        if not self.search_text or self.search_mode:
            return

        matches = self._find_search_matches(entry)
        if not matches:
            return

        raw = entry.raw.rstrip()
        prefix_len = text_len - len(raw) if text_len > len(raw) else 0

        try:
            for m in matches:
                start = col + prefix_len + m.start()
                end = col + prefix_len + m.end()
                if start >= col + width:
                    break
                end = min(end, col + width)
                n = end - start
                if n > 0:
                    stdscr.chgat(row, start, n, self._SEARCH_CUR)
        except curses.error:
            pass

    def _freeze(self) -> None:
        self.frozen = True
        self._snapshot = self._get_display_list()
        display = self._snapshot
        vh = self._visible_log_h
        if display:
            self.cursor = min(self.log_top + vh // 2, len(display) - 1)
            self.log_top = max(0, self.cursor - vh // 2)
        else:
            self.cursor = 0
            self.log_top = 0
        curses.curs_set(1)
        self.status_msg = "  [FROZEN]"

    def _unfreeze(self) -> None:
        self.frozen = False
        self._snapshot = None
        self.visual_mode = False
        self.selected.clear()
        curses.curs_set(0)
        self.status_msg = "  Resumed live"

    def _enter_visual_mode(self) -> None:
        display = self._get_display_list()
        if not display:
            return
        self.visual_mode = True
        self.selected.clear()
        self.visual_anchor = self.cursor
        self.selected.add(self.cursor)
        self.status_msg = "  [VISUAL] i/j select lines"

    def _exit_visual_mode(self) -> None:
        self.visual_mode = False
        self.selected.clear()
        self.status_msg = "  Exited visual"

    def _rebuild_selection(self) -> None:
        lo, hi = min(self.visual_anchor, self.cursor), max(self.visual_anchor, self.cursor)
        display = self._get_display_list()
        self.selected = {i for i in range(lo, hi + 1) if i < len(display)}

    def _ensure_cursor_visible(self) -> None:
        vh = self._visible_log_h
        if self.cursor < self.log_top:
            self.log_top = self.cursor
        elif self.cursor >= self.log_top + vh:
            self.log_top = self.cursor - vh + 1

    def _refresh_snapshot(self) -> None:
        if self.frozen:
            self._snapshot = self._get_display_list()
            if self.cursor >= len(self._snapshot):
                self.cursor = max(0, len(self._snapshot) - 1)

    def _copy_selected(self) -> None:
        display = self._get_display_list()
        if not self.selected or not display:
            self.status_msg = "  No lines selected"
            return
        lines = []
        for idx in sorted(self.selected):
            if idx < len(display):
                lines.append(display[idx].raw.rstrip())
        if not lines:
            self.status_msg = "  No lines selected"
            return
        text = "\n".join(lines)
        if copy_to_clipboard(text):
            self.status_msg = f"  Copied {len(lines)} lines to clipboard"
        else:
            self.status_msg = "  Copy failed"

    def _copy_frozen_at_cursor(self) -> None:
        display = self._get_display_list()
        if not display:
            return
        if self.cursor < len(display):
            text = display[self.cursor].raw.rstrip()
            if copy_to_clipboard(text):
                self.status_msg = f"  Copied line {self.cursor + 1}"
            else:
                self.status_msg = "  Copy failed"

    def _passes_filter(self, entry: LogEntry) -> bool:
        level_idx = LEVELS.index(self.current_level)
        full_level = _PRIORITY_TO_LEVEL.get(entry.priority, "Debug")
        entry_idx = LEVELS.index(full_level)
        if entry_idx < level_idx:
            return False
        if self.filter_text:
            f = self.filter_text.lower()
            if f not in entry.tag.lower() and f not in entry.message.lower():
                return False
        return True

    def _copy_visible_logs(self) -> None:
        filtered = self._get_display_list()
        if not filtered:
            self.status_msg = "  No logs to copy"
            return
        text = "\n".join(e.raw.rstrip() for e in filtered)
        if copy_to_clipboard(text):
            self.status_msg = f"  Copied {len(filtered)} lines to clipboard"
        else:
            self.status_msg = "  Copy failed"

    def _start_logcat(self) -> None:
        cmd = ["adb", "-s", self.device, "logcat", "-v", "threadtime", "-T", "1"]
        self._process = Popen(cmd, stdout=PIPE, stderr=PIPE, bufsize=0)
        threading.Thread(target=self._read_logcat, daemon=True).start()

    def _read_logcat(self) -> None:
        assert self._process is not None
        assert self._process.stdout is not None
        try:
            buf = b""
            while not self._stop_event.is_set():
                chunk = self._process.stdout.read(4096)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line_bytes, buf = buf.split(b"\n", 1)
                    line = line_bytes.decode("utf-8", errors="replace")
                    entry = _parse_logcat_line(line)
                    if entry is not None:
                        self._entry_queue.put(entry)
        except Exception:
            pass
        finally:
            self._entry_queue.put(None)

    def _process_entries(self) -> None:
        while True:
            try:
                entry = self._entry_queue.get_nowait()
            except queue.Empty:
                break
            if entry is None:
                break
            with self._log_lock:
                self.logs.append(entry)

    def run(self) -> None:
        self._start_logcat()
        try:
            curses.wrapper(self._main_loop)
        finally:
            self._stop_event.set()
            if self._process and self._process.poll() is None:
                self._process.terminate()

    def _main_loop(self, stdscr: curses.window) -> None:
        curses.curs_set(0)
        self._init_colors()
        curses.set_escdelay(50)
        stdscr.timeout(100)

        while True:
            self._process_entries()
            self._draw(stdscr)
            try:
                key = stdscr.get_wch()
            except curses.error:
                continue
            if isinstance(key, str):
                key = ord(key)
            if not self._handle_key(key):
                break


def main() -> None:
    require("adb")

    parser = argparse.ArgumentParser(
        prog="android-log",
        description="Interactive curses-based logcat viewer with level and text filtering.",
    )
    parser.add_argument(
        "-m",
        "--max-logs",
        type=int,
        default=5,
        help="max log entries in units of 10,000 (default: 5, i.e. 50,000)",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    device = select_device()
    max_logs = args.max_logs * 10_000
    log.info("device %s selected, max logs %d", device, max_logs)

    viewer = LogViewer(device, max_logs=max_logs)
    viewer.run()


if __name__ == "__main__":
    main()
