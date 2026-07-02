"""``android-emulator`` - list available AVDs and start the chosen one."""

from __future__ import annotations

import argparse
import contextlib
import subprocess
import sys

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import CommandNotFoundError, capture, require
from toolscripts.core.ui_curses import _ensure_curses_available

log = get_logger(__name__)


def _pick_avd(avds: list[str], *, writable: bool, detach: bool) -> tuple[int, bool, bool] | None:
    """Show a curses picker with toggle options. Returns (index, writable, detach) or None on cancel."""
    _ensure_curses_available()
    import curses

    def _run(stdscr: curses.window) -> tuple[int, bool, bool] | None:
        return _avd_picker_impl(stdscr, avds, writable, detach)

    return curses.wrapper(_run)


def _avd_picker_impl(
    stdscr: object,
    avds: list[str],
    writable: bool,
    detach: bool,
) -> tuple[int, bool, bool] | None:
    import curses

    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_WHITE, -1)

    cursor = 0
    top = 0
    ws = writable
    dt = detach

    def draw() -> None:
        nonlocal top
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        title = "Please select emulator"
        stdscr.addstr(0, 0, title, curses.A_BOLD)
        hint = "j/k move | Enter start | w writable | d detach | q quit"
        stdscr.addstr(1, 0, hint, curses.color_pair(3))

        body_row = 3
        list_h = height - body_row - 3

        if cursor < top:
            top = cursor
        elif cursor >= top + list_h:
            top = cursor - list_h + 1

        for i in range(min(list_h, len(avds) - top)):
            idx = top + i
            marker = ">" if idx == cursor else " "
            attr = curses.A_BOLD | curses.A_REVERSE if idx == cursor else 0
            color = curses.color_pair(2) if idx == cursor else curses.color_pair(4)
            with contextlib.suppress(curses.error):
                text = f"  {marker}  {avds[idx]}"[: width - 1]
                stdscr.addstr(body_row + i, 0, text, attr | color)

        sep_row = body_row + min(list_h, len(avds))
        with contextlib.suppress(curses.error):
            stdscr.addstr(sep_row, 0, "  " + "-" * min(40, width - 4), curses.color_pair(1))

        ws_mark = "[x]" if ws else "[ ]"
        dt_mark = "[x]" if dt else "[ ]"
        with contextlib.suppress(curses.error):
            stdscr.addstr(sep_row + 1, 0, f"  {ws_mark} w  writable-system", curses.color_pair(3))
            stdscr.addstr(
                sep_row + 2, 0, f"  {dt_mark} d  detach (background)", curses.color_pair(3)
            )

        stdscr.refresh()

    while True:
        draw()
        key = stdscr.getch()

        if key == curses.KEY_UP or key == ord("k"):
            cursor = max(0, cursor - 1)
        elif key == curses.KEY_DOWN or key == ord("j"):
            cursor = min(len(avds) - 1, cursor + 1)
        elif key == ord("g"):
            key2 = stdscr.getch()
            if key2 == ord("g"):
                cursor = 0
        elif key == ord("G"):
            cursor = len(avds) - 1
        elif key == ord("w"):
            ws = not ws
        elif key == ord("d"):
            dt = not dt
        elif key in (curses.KEY_ENTER, 10, 13) or key == ord("o"):
            return (cursor, ws, dt)
        elif key in (ord("q"), 27):
            return None


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="android-emulator",
        description="List Android emulator AVDs and launch the chosen one.",
    )
    parser.add_argument(
        "--writable-system",
        action="store_true",
        help="start with -writable-system (skip prompt)",
    )
    parser.add_argument(
        "--foreground",
        action="store_true",
        help="block terminal until emulator exits (default: detach)",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        require("emulator")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        log.warning("install Android SDK platform-tools / emulator")
        sys.exit(1)

    output = capture(["emulator", "-list-avds"], check=False)
    avds = [line.strip() for line in output.splitlines() if line.strip() and "INFO" not in line]
    if not avds:
        log.warning("no emulator AVDs configured")
        return

    result = _pick_avd(avds, writable=args.writable_system, detach=not args.foreground)
    if result is None:
        return
    idx, ws, dt = result
    avd = avds[idx]
    log.info("%s selected", avd)

    cmd = ["emulator", "-avd", avd]
    if ws:
        cmd.append("-writable-system")

    if dt:
        log.info("starting emulator in background")
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log.success("emulator launched (detached)")
    else:
        log.info("starting emulator in foreground")
        subprocess.run(cmd, check=False)


if __name__ == "__main__":
    main()
