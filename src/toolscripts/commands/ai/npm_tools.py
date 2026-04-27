"""``npm-tools`` - manage globally installed npm packages with a curses TUI."""

from __future__ import annotations

import argparse
import contextlib
import json
import subprocess
import sys
import threading

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import CommandNotFoundError, require

log = get_logger(__name__)

_BUILTINS = {"npm", "corepack"}
_PENDING = object()


def _run(cmd: list[str], *, timeout: int | None = None) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, check=False, timeout=timeout
        )
        return proc.returncode, proc.stdout.strip()
    except subprocess.TimeoutExpired:
        return 1, ""


def _list_installed() -> dict[str, str]:
    code, out = _run(["npm", "list", "-g", "--depth=0", "--json"], timeout=30)
    if code != 0 or not out:
        return {}
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return {}
    deps = data.get("dependencies", {})
    return {
        name: info.get("version", "unknown")
        for name, info in deps.items()
        if name not in _BUILTINS
    }


def _latest_version(name: str) -> str:
    _, out = _run(["npm", "view", name, "version"], timeout=15)
    return out


class _VersionFetcher:
    def __init__(self, names: list[str]) -> None:
        self._versions: dict[str, object] = {n: _PENDING for n in names}
        self._lock = threading.Lock()
        for name in names:
            t = threading.Thread(target=self._fetch, args=(name,), daemon=True)
            t.start()

    def _fetch(self, name: str) -> None:
        version = _latest_version(name) or ""
        with self._lock:
            self._versions[name] = version

    def get(self, name: str) -> object:
        with self._lock:
            return self._versions.get(name, _PENDING)

    def all_done(self) -> bool:
        with self._lock:
            return all(v is not _PENDING for v in self._versions.values())


def _run_ops_outside_curses(stdscr, ops: list[tuple[str, str]]) -> None:  # type: ignore[no-untyped-def]
    import curses
    curses.def_prog_mode()
    curses.endwin()
    print()
    for action, pkg in ops:
        if action == "uninstall":
            log.info("uninstalling %s ...", pkg)
            subprocess.run(["npm", "uninstall", "-g", pkg], check=False)
        elif action == "update":
            log.info("updating %s ...", pkg)
            subprocess.run(["npm", "install", "-g", f"{pkg}@latest"], check=False)
    print()
    with contextlib.suppress(EOFError, KeyboardInterrupt):
        input("Press Enter to return to the menu...")
    curses.reset_prog_mode()
    stdscr.keypad(True)
    stdscr.refresh()


def _draw(stdscr, *, installed, pkg_names, fetcher, nav_pos, scroll_top, selected, current_name):  # type: ignore[no-untyped-def]
    import curses

    h, w = stdscr.getmaxyx()
    HEADER_ROWS = 7
    FOOTER_ROWS = 1
    list_height = max(1, h - HEADER_ROWS - FOOTER_ROWS)

    if pkg_names:
        if nav_pos < scroll_top:
            scroll_top = nav_pos
        elif nav_pos >= scroll_top + list_height:
            scroll_top = nav_pos - list_height + 1

    stdscr.clear()
    title = " NPM Global Packages "
    try:
        stdscr.addstr(0, max(0, (w - len(title)) // 2), title, curses.A_BOLD)
        stdscr.addstr(2, 2, "[i/k/Up] Up  [j/Down] Down  [Space] Select  [s] Select All/None", curses.A_DIM)
        stdscr.addstr(3, 2, "[d] Uninstall  [u] Update Selected  [a] Update All  [r] Refresh  [q] Quit", curses.A_DIM)
        col_hdr = f"{'':8}{'Package':<39}{'Installed':<13}Latest"
        stdscr.addstr(5, 2, col_hdr[: w - 4], curses.A_BOLD)
        stdscr.addstr(6, 2, "-" * min(len(col_hdr), w - 4), curses.A_DIM)
    except curses.error:
        pass

    row = HEADER_ROWS
    for idx in range(scroll_top, len(pkg_names)):
        if row >= h - FOOTER_ROWS:
            break
        name = pkg_names[idx]
        is_current = idx == nav_pos
        is_selected = name in selected
        installed_ver = installed.get(name, "")
        latest = fetcher.get(name)

        checkbox = "[*]" if is_selected else "[ ]"
        ver_col = f"{installed_ver:<13}"
        line = f"  {checkbox} {name:<38} {ver_col}"

        attr = curses.A_REVERSE if is_current else 0
        if is_selected and not is_current:
            attr |= curses.A_BOLD

        try:
            stdscr.addstr(row, 2, line[: w - 4], attr)
            x = 2 + len(line) + 1
            if latest is _PENDING:
                stdscr.addstr(row, x, "?", curses.A_DIM | attr)
            elif not latest:
                stdscr.addstr(row, x, "-", curses.A_DIM | attr)
            elif installed_ver == latest:
                stdscr.addstr(row, x, "OK", attr)
            else:
                stdscr.addstr(row, x, f"-> {latest}", attr | curses.A_BOLD)
        except curses.error:
            pass
        row += 1

    fetching = "" if fetcher.all_done() else "  fetching latest..."
    status = f" {len(selected)} selected | {len(pkg_names)} packages{fetching} "
    with contextlib.suppress(curses.error):
        stdscr.addstr(h - 1, max(0, (w - len(status)) // 2), status[:w], curses.A_REVERSE)
    stdscr.refresh()
    return scroll_top


def _curses_loop(stdscr) -> None:  # type: ignore[no-untyped-def]
    import curses

    curses.curs_set(0)
    stdscr.timeout(200)

    installed = _list_installed()
    pkg_names = sorted(installed.keys())
    fetcher = _VersionFetcher(pkg_names)
    nav_pos = 0
    scroll_top = 0
    selected: set[str] = set()

    while True:
        if pkg_names:
            nav_pos = max(0, min(nav_pos, len(pkg_names) - 1))
            current_name = pkg_names[nav_pos]
        else:
            nav_pos = 0
            current_name = ""

        scroll_top = _draw(
            stdscr,
            installed=installed,
            pkg_names=pkg_names,
            fetcher=fetcher,
            nav_pos=nav_pos,
            scroll_top=scroll_top,
            selected=selected,
            current_name=current_name,
        )

        key = stdscr.getch()
        if key == -1:
            continue
        if key in (ord("q"), ord("Q")):
            break
        if key in (ord("r"), ord("R")):
            installed = _list_installed()
            pkg_names = sorted(installed.keys())
            fetcher = _VersionFetcher(pkg_names)
            selected.clear()
            nav_pos = min(nav_pos, max(0, len(pkg_names) - 1))
        elif key in (curses.KEY_UP, ord("i"), ord("k")):
            nav_pos = max(0, nav_pos - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            if pkg_names:
                nav_pos = min(len(pkg_names) - 1, nav_pos + 1)
        elif key in (ord("s"), ord("S")):
            if len(selected) == len(pkg_names):
                selected.clear()
            else:
                selected = set(pkg_names)
        elif key == ord(" ") and pkg_names:
            if current_name in selected:
                selected.remove(current_name)
            else:
                selected.add(current_name)
        elif key in (ord("d"), ord("D")) and selected:
            ops = [("uninstall", t) for t in selected]
            _run_ops_outside_curses(stdscr, ops)
            installed = _list_installed()
            pkg_names = sorted(installed.keys())
            fetcher = _VersionFetcher(pkg_names)
            selected.clear()
        elif key == ord("u") and selected:
            ops = []
            for t in selected:
                latest = fetcher.get(t)
                if latest is not _PENDING and latest and latest == installed.get(t):
                    continue
                ops.append(("update", t))
            if ops:
                _run_ops_outside_curses(stdscr, ops)
                installed = _list_installed()
                pkg_names = sorted(installed.keys())
                fetcher = _VersionFetcher(pkg_names)
                selected.clear()
        elif key == ord("a"):
            if not fetcher.all_done():
                continue
            ops = []
            for t in pkg_names:
                latest = fetcher.get(t)
                if latest is not _PENDING and latest and latest == installed.get(t):
                    continue
                ops.append(("update", t))
            if ops:
                _run_ops_outside_curses(stdscr, ops)
                installed = _list_installed()
                pkg_names = sorted(installed.keys())
                fetcher = _VersionFetcher(pkg_names)
                selected.clear()


def _text_status() -> None:
    log.info("Globally installed npm packages:")
    installed = _list_installed()
    if not installed:
        log.warning("no globally installed packages found.")
        return
    for name, version in sorted(installed.items()):
        print(f"  {name}@{version}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="npm-tools",
        description="Manage globally installed npm packages via curses TUI.",
    )
    parser.add_argument(
        "--text", action="store_true", help="print plain text status without TUI"
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        require("npm")
        require("node")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)

    if args.text:
        _text_status()
        return

    try:
        import curses
    except ImportError:
        log.warning("curses unavailable - install windows-curses on Windows")
        _text_status()
        return

    try:
        curses.wrapper(_curses_loop)
    except Exception as exc:  # noqa: BLE001
        log.error("interactive UI failed: %s. Falling back to text mode.", exc)
        _text_status()


if __name__ == "__main__":
    main()
