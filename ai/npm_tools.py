#!/usr/bin/env python3
import curses
import json
import os
import subprocess
import sys
import shutil
import threading
from pathlib import Path


TOOLS = {
    "AI CLI": [
        {"name": "@github/copilot", "desc": "GitHub Copilot - AI pair programmer"},
        {
            "name": "@google/gemini-cli",
            "desc": "Google Gemini CLI - AI coding assistant",
        },
        {"name": "@openai/codex", "desc": "OpenAI Codex - AI code generation"},
        {
            "name": "@qwen-code/qwen-code",
            "desc": "Qwen Code - Alibaba's AI coding tool",
        },
        {"name": "@fly-ai/flyai-cli", "desc": "FlyAI - Travel booking CLI"},
    ],
    "Dev Tools": [
        {"name": "pnpm", "desc": "Fast, disk space efficient package manager"},
        {"name": "appium", "desc": "Mobile app automation testing framework"},
    ],
}


class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    NC = "\033[0m"


# Curses color pair IDs
CP_GREEN = 1
CP_RED = 2
CP_YELLOW = 3
CP_CYAN = 4
CP_SEL = 5   # black text on green background — selected row highlight

# Sentinel for "not yet fetched" — distinct from "" (fetch failed) or a version string
_PENDING = object()


def log_info(msg):
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {msg}")


def log_error(msg):
    print(f"{Colors.RED}[ERROR]{Colors.NC} {msg}", file=sys.stderr)


def run_command(command, shell=False, check=False, stream=False, timeout=None):
    if stream:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=shell,
        )
        output = []
        for line in iter(process.stdout.readline, ""):
            if not line:
                break
            sys.stdout.write(line)
            output.append(line)
        process.wait()
        return process.returncode, "".join(output)

    try:
        process = subprocess.run(
            command, capture_output=True, text=True, shell=shell, check=check,
            timeout=timeout,
        )
        return process.returncode, process.stdout.strip()
    except subprocess.TimeoutExpired:
        return 1, ""
    except subprocess.CalledProcessError as e:
        return e.returncode, e.stdout.strip()


_npm_root = None


def get_npm_root(reset=False):
    global _npm_root
    if _npm_root is None or reset:
        _, stdout = run_command(["npm", "root", "-g"])
        _npm_root = stdout
    return _npm_root


def get_all_tool_names():
    return [tool["name"] for tools in TOOLS.values() for tool in tools]


def get_installed_tools(reset_cache=False):
    installed = {}
    npm_root = get_npm_root(reset=reset_cache)
    if not npm_root:
        log_error("Could not determine npm root directory.")
        return {}
    for tool_name in get_all_tool_names():
        pkg_path = Path(npm_root) / tool_name / "package.json"
        if pkg_path.is_file():
            try:
                with pkg_path.open("r") as f:
                    data = json.load(f)
                    installed[tool_name] = data.get("version", "unknown")
            except (json.JSONDecodeError, IOError):
                installed[tool_name] = "error"
    return installed


def get_latest_version(package_name):
    _, stdout = run_command(["npm", "view", package_name, "version"], timeout=15)
    return stdout


class VersionFetcher:
    """Fetches latest npm versions in background daemon threads.

    get(name) returns:
      _PENDING  — still fetching
      ""        — fetch completed but returned nothing (network error, unknown pkg)
      "x.y.z"   — fetched successfully
    """

    def __init__(self, tool_names):
        self._versions = {name: _PENDING for name in tool_names}
        self._lock = threading.Lock()
        for name in tool_names:
            t = threading.Thread(target=self._fetch, args=(name,), daemon=True)
            t.start()

    def _fetch(self, name):
        version = get_latest_version(name) or ""
        with self._lock:
            self._versions[name] = version

    def get(self, name):
        with self._lock:
            return self._versions.get(name, _PENDING)

    def all_done(self):
        with self._lock:
            return all(v is not _PENDING for v in self._versions.values())


def build_display_list():
    """Flat list of ("header", category) or ("tool", category, name, desc) entries."""
    items = []
    for category, tools in TOOLS.items():
        items.append(("header", category))
        for tool in tools:
            items.append(("tool", category, tool["name"], tool["desc"]))
    return items


def get_tool_indices(display_list):
    """Indices of tool entries in display_list (the navigable items)."""
    return [i for i, item in enumerate(display_list) if item[0] == "tool"]


def init_curses_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(CP_GREEN,  curses.COLOR_GREEN,  -1)
    curses.init_pair(CP_RED,    curses.COLOR_RED,    -1)
    curses.init_pair(CP_YELLOW, curses.COLOR_YELLOW, -1)
    curses.init_pair(CP_CYAN,   curses.COLOR_CYAN,   -1)
    curses.init_pair(CP_SEL,    curses.COLOR_BLACK,  curses.COLOR_GREEN)


def _addstr(stdscr, y, x, text, attr=0):
    try:
        stdscr.addstr(y, x, text, attr)
    except curses.error:
        pass


def _run_ops_outside_curses(stdscr, ops):
    """Temporarily exit curses, run npm ops, re-enter. ops: list of (action, tool_name)."""
    curses.def_prog_mode()
    curses.endwin()
    print()
    for action, tool in ops:
        if action == "install":
            log_info(f"Installing {tool}...")
            run_command(["npm", "install", "-g", f"{tool}@latest"], stream=True)
        elif action == "uninstall":
            log_info(f"Uninstalling {tool}...")
            run_command(["npm", "uninstall", "-g", tool], stream=True)
        elif action == "update":
            log_info(f"Updating {tool}...")
            run_command(["npm", "install", "-g", f"{tool}@latest"], stream=True)
    print()
    input("Press Enter to return to the menu...")
    curses.reset_prog_mode()
    stdscr.keypad(True)   # re-enable keypad after returning from shell
    stdscr.refresh()


def _render_tool_row(stdscr, row, w, tool_name, is_current, is_selected, installed_ver, latest):
    """Render one tool row.

    installed_ver: version string if installed, "" if not.
    latest: _PENDING | "" | "x.y.z"  (from VersionFetcher)

    Priority: cursor (A_REVERSE) > selected (green bg) > normal
    Sub-elements (✓/✗, ↑ version) keep their natural accent color only on
    normal rows; on highlighted rows they inherit the row's base attribute so
    they don't clash with the background.
    """
    checkbox = "[*]" if is_selected else "[ ]"
    is_installed = bool(installed_ver)
    ver_col = f"{installed_ver:<13}" if installed_ver else f"{'—':<13}"

    if is_current:
        base = curses.A_REVERSE
    elif is_selected:
        base = curses.color_pair(CP_SEL)
    else:
        base = curses.A_NORMAL

    # accent(): natural color on normal rows, base attribute on highlighted rows
    def accent(cp, extra=0):
        if is_current or is_selected:
            return base | extra
        return curses.color_pair(cp) | extra

    status_char = "✓" if is_installed else "✗"
    status_attr = accent(CP_GREEN if is_installed else CP_RED)

    if latest is _PENDING:
        latest_text = "⟳"
        latest_attr = accent(CP_YELLOW, curses.A_DIM)
    elif not latest:
        latest_text = "?"
        latest_attr = base | curses.A_DIM
    elif not is_installed:
        latest_text = latest
        latest_attr = base
    elif installed_ver == latest:
        latest_text = "✓"
        latest_attr = accent(CP_GREEN)
    else:
        latest_text = f"↑ {latest}"
        latest_attr = accent(CP_YELLOW, curses.A_BOLD)

    try:
        x = 2
        stdscr.addstr(row, x, f"  {checkbox} ", base)
        x += 6
        stdscr.addstr(row, x, status_char, status_attr)
        x += 1
        stdscr.addstr(row, x, f" {tool_name:<32} {ver_col}", base)
        x += 1 + 32 + 1 + 13
        stdscr.addstr(row, x, latest_text[:max(0, w - x - 1)], latest_attr)
    except curses.error:
        pass


def run_curses(stdscr):
    init_curses_colors()
    curses.curs_set(0)
    stdscr.timeout(200)  # unblock getch() every 200ms for async version updates

    display_list = build_display_list()
    tool_indices = get_tool_indices(display_list)
    all_names = get_all_tool_names()

    nav_pos = 0
    selected = set()
    scroll_top = 0
    installed = get_installed_tools()
    fetcher = VersionFetcher(all_names)

    # Fixed chrome rows
    HEADER_ROWS = 7   # title, blank, help×2, blank, col-hdr, separator
    FOOTER_ROWS = 3   # separator, description, status-bar

    col_hdr = f"{'':8}{'Package':<33}{'Installed':<13}Latest"

    while True:
        h, w = stdscr.getmaxyx()
        list_height = max(1, h - HEADER_ROWS - FOOTER_ROWS)
        current_disp_idx = tool_indices[nav_pos] if tool_indices else -1
        current_item = display_list[current_disp_idx] if current_disp_idx >= 0 else None
        current_name = current_item[2] if current_item else ""
        current_desc = current_item[3] if current_item else ""

        # Keep the focused item inside the visible scroll window
        if current_disp_idx < scroll_top:
            scroll_top = current_disp_idx
        elif current_disp_idx >= scroll_top + list_height:
            scroll_top = current_disp_idx - list_height + 1

        stdscr.clear()

        # ── Header ────────────────────────────────────────────────────────────
        title = " NPM Tools Manager "
        _addstr(stdscr, 0, max(0, (w - len(title)) // 2), title, curses.A_BOLD | curses.A_UNDERLINE)
        _addstr(stdscr, 2, 2, "[i/k/↑] Up  [j/↓] Down  [Space] Select  [s] Select All/None", curses.A_DIM)
        _addstr(stdscr, 3, 2, "[a] Install  [d] Delete  [u] Update  [r] Refresh  [q] Quit", curses.A_DIM)
        _addstr(stdscr, 5, 2, col_hdr[:w - 4], curses.A_BOLD)
        _addstr(stdscr, 6, 2, "─" * min(len(col_hdr), w - 4), curses.A_DIM)

        # ── List ──────────────────────────────────────────────────────────────
        row = HEADER_ROWS
        for disp_idx in range(scroll_top, len(display_list)):
            if row >= h - FOOTER_ROWS:
                break
            item = display_list[disp_idx]
            if item[0] == "header":
                _, category = item
                _addstr(stdscr, row, 2, f"── {category} ", curses.A_BOLD | curses.color_pair(CP_CYAN))
            else:
                _, _, tool_name, _ = item
                _render_tool_row(
                    stdscr, row, w, tool_name,
                    is_current=(disp_idx == current_disp_idx),
                    is_selected=(tool_name in selected),
                    installed_ver=installed.get(tool_name, ""),
                    latest=fetcher.get(tool_name),
                )
            row += 1

        # ── Footer ────────────────────────────────────────────────────────────
        sep_row = h - FOOTER_ROWS
        _addstr(stdscr, sep_row, 2, "─" * min(len(col_hdr), w - 4), curses.A_DIM)
        _addstr(stdscr, sep_row + 1, 2, f"→ {current_desc}"[:w - 4] if current_desc else "", curses.A_DIM)

        fetching = "" if fetcher.all_done() else "  ⟳ fetching latest…"
        status = f" {len(selected)} selected · {len(installed)}/{len(all_names)} installed{fetching} "
        _addstr(stdscr, h - 1, max(0, (w - len(status)) // 2), status[:w], curses.A_REVERSE)

        stdscr.refresh()
        key = stdscr.getch()

        if key == -1:
            continue  # timeout — redraw to pick up fresh version data
        elif key in (ord("q"), ord("Q")):
            break
        elif key in (ord("r"), ord("R")):
            installed = get_installed_tools(reset_cache=True)
            fetcher = VersionFetcher(all_names)  # restart background fetches
        elif key in (curses.KEY_UP, ord("i"), ord("k")):
            nav_pos = max(0, nav_pos - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            nav_pos = min(len(tool_indices) - 1, nav_pos + 1)
        elif key in (ord("s"), ord("S")):
            if len(selected) == len(all_names):
                selected.clear()
            else:
                selected = set(all_names)
        elif key == ord(" ") and tool_indices:
            if current_name in selected:
                selected.remove(current_name)
            else:
                selected.add(current_name)
        elif key in (ord("a"), ord("A")) and selected:
            ops = [("install", t) for t in selected if t not in installed]
            if ops:
                _run_ops_outside_curses(stdscr, ops)
                installed = get_installed_tools(reset_cache=True)
                fetcher = VersionFetcher(all_names)
                selected.clear()
        elif key in (ord("d"), ord("D")) and selected:
            ops = [("uninstall", t) for t in selected if t in installed]
            if ops:
                _run_ops_outside_curses(stdscr, ops)
                installed = get_installed_tools(reset_cache=True)
                selected.clear()
        elif key in (ord("u"), ord("U")) and selected:
            ops = []
            for t in selected:
                if t not in installed:
                    continue  # not installed, nothing to update
                latest = fetcher.get(t)
                if latest is not _PENDING and latest and latest == installed.get(t):
                    continue  # already at latest version, skip
                ops.append(("update", t))
            if ops:
                _run_ops_outside_curses(stdscr, ops)
                installed = get_installed_tools(reset_cache=True)
                fetcher = VersionFetcher(all_names)
                selected.clear()


def show_status_text_mode():
    log_info("Checking tool status...")
    print()
    installed_tools = get_installed_tools()
    for category, tools in TOOLS.items():
        print(f"\n{Colors.CYAN}{category}:{Colors.NC}")
        for tool in tools:
            tool_name = tool["name"]
            tool_desc = tool["desc"]
            if tool_name in installed_tools:
                version = installed_tools[tool_name]
                print(
                    f"  {Colors.GREEN}✓{Colors.NC} {tool_name}@{version} - {tool_desc}"
                )
            else:
                print(f"  {Colors.RED}✗{Colors.NC} {tool_name} - {tool_desc}")
    print()


def main_loop():
    try:
        curses.wrapper(run_curses)
    except Exception as e:
        log_error(f"Interactive UI failed: {e}. Falling back to text mode.")
        show_status_text_mode()


if __name__ == "__main__":
    if not shutil.which("npm") or not shutil.which("node"):
        log_error("npm and node must be installed and in your PATH.")
        sys.exit(1)
    main_loop()
