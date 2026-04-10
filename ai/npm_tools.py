#!/usr/bin/env python3
import curses
import json
import subprocess
import sys
import shutil
import threading

# Packages bundled with Node.js — skip these
BUILTIN_PACKAGES = {"npm", "corepack"}


class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    NC = "\033[0m"


# Curses color pair IDs
CP_GREEN = 1
CP_YELLOW = 2
CP_SEL = 3   # black text on green background — selected row highlight

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


def get_installed_packages():
    """Returns dict of {package_name: version} for all global npm packages, excluding builtins."""
    _, stdout = run_command(["npm", "list", "-g", "--depth=0", "--json"], timeout=30)
    if not stdout:
        return {}
    try:
        data = json.loads(stdout)
        deps = data.get("dependencies", {})
        return {
            name: info.get("version", "unknown")
            for name, info in deps.items()
            if name not in BUILTIN_PACKAGES
        }
    except json.JSONDecodeError:
        return {}


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

    def __init__(self, package_names):
        self._versions = {name: _PENDING for name in package_names}
        self._lock = threading.Lock()
        for name in package_names:
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


def init_curses_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(CP_GREEN,  curses.COLOR_GREEN,  -1)
    curses.init_pair(CP_YELLOW, curses.COLOR_YELLOW, -1)
    curses.init_pair(CP_SEL,    curses.COLOR_BLACK,  curses.COLOR_GREEN)


def _addstr(stdscr, y, x, text, attr=0):
    try:
        stdscr.addstr(y, x, text, attr)
    except curses.error:
        pass


def _run_ops_outside_curses(stdscr, ops):
    """Temporarily exit curses, run npm ops, re-enter. ops: list of (action, pkg_name)."""
    curses.def_prog_mode()
    curses.endwin()
    print()
    for action, pkg in ops:
        if action == "uninstall":
            log_info(f"Uninstalling {pkg}...")
            run_command(["npm", "uninstall", "-g", pkg], stream=True)
        elif action == "update":
            log_info(f"Updating {pkg}...")
            run_command(["npm", "install", "-g", f"{pkg}@latest"], stream=True)
    print()
    input("Press Enter to return to the menu...")
    curses.reset_prog_mode()
    stdscr.keypad(True)
    stdscr.refresh()


def _render_package_row(stdscr, row, w, pkg_name, is_current, is_selected, installed_ver, latest):
    checkbox = "[*]" if is_selected else "[ ]"
    ver_col = f"{installed_ver:<13}"

    if is_current:
        base = curses.A_REVERSE
    elif is_selected:
        base = curses.color_pair(CP_SEL)
    else:
        base = curses.A_NORMAL

    def accent(cp, extra=0):
        if is_current or is_selected:
            return base | extra
        return curses.color_pair(cp) | extra

    if latest is _PENDING:
        latest_text = "⟳"
        latest_attr = accent(CP_YELLOW, curses.A_DIM)
    elif not latest:
        latest_text = "?"
        latest_attr = base | curses.A_DIM
    elif installed_ver == latest:
        latest_text = "✓"
        latest_attr = accent(CP_GREEN)
    else:
        latest_text = f"↑ {latest}"
        latest_attr = accent(CP_YELLOW, curses.A_BOLD)

    try:
        x = 2
        stdscr.addstr(row, x, f"  {checkbox} {pkg_name:<38} {ver_col}", base)
        x += 6 + 38 + 1 + 13
        stdscr.addstr(row, x, latest_text[:max(0, w - x - 1)], latest_attr)
    except curses.error:
        pass


def run_curses(stdscr):
    init_curses_colors()
    curses.curs_set(0)
    stdscr.timeout(200)  # unblock getch() every 200ms for async version updates

    installed = get_installed_packages()
    pkg_names = sorted(installed.keys())
    fetcher = VersionFetcher(pkg_names)

    nav_pos = 0
    selected = set()
    scroll_top = 0

    # Fixed chrome rows: title, blank, help×2, blank, col-hdr, separator
    HEADER_ROWS = 7
    FOOTER_ROWS = 1  # status bar only

    col_hdr = f"{'':8}{'Package':<39}{'Installed':<13}Latest"

    while True:
        h, w = stdscr.getmaxyx()
        list_height = max(1, h - HEADER_ROWS - FOOTER_ROWS)

        if pkg_names:
            nav_pos = max(0, min(nav_pos, len(pkg_names) - 1))
            current_name = pkg_names[nav_pos]
        else:
            nav_pos = 0
            current_name = ""

        # Keep the focused item inside the visible scroll window
        if nav_pos < scroll_top:
            scroll_top = nav_pos
        elif nav_pos >= scroll_top + list_height:
            scroll_top = nav_pos - list_height + 1

        stdscr.clear()

        # ── Header ────────────────────────────────────────────────────────────
        title = " NPM Global Packages "
        _addstr(stdscr, 0, max(0, (w - len(title)) // 2), title, curses.A_BOLD | curses.A_UNDERLINE)
        _addstr(stdscr, 2, 2, "[i/k/↑] Up  [j/↓] Down  [Space] Select  [s] Select All/None", curses.A_DIM)
        _addstr(stdscr, 3, 2, "[d] Uninstall  [u] Update  [r] Refresh  [q] Quit", curses.A_DIM)
        _addstr(stdscr, 5, 2, col_hdr[:w - 4], curses.A_BOLD)
        _addstr(stdscr, 6, 2, "─" * min(len(col_hdr), w - 4), curses.A_DIM)

        # ── List ──────────────────────────────────────────────────────────────
        row = HEADER_ROWS
        for idx in range(scroll_top, len(pkg_names)):
            if row >= h - FOOTER_ROWS:
                break
            name = pkg_names[idx]
            _render_package_row(
                stdscr, row, w, name,
                is_current=(idx == nav_pos),
                is_selected=(name in selected),
                installed_ver=installed.get(name, ""),
                latest=fetcher.get(name),
            )
            row += 1

        # ── Footer ────────────────────────────────────────────────────────────
        fetching = "" if fetcher.all_done() else "  ⟳ fetching latest…"
        status = f" {len(selected)} selected · {len(pkg_names)} packages{fetching} "
        _addstr(stdscr, h - 1, max(0, (w - len(status)) // 2), status[:w], curses.A_REVERSE)

        stdscr.refresh()
        key = stdscr.getch()

        if key == -1:
            continue  # timeout — redraw to pick up fresh version data
        elif key in (ord("q"), ord("Q")):
            break
        elif key in (ord("r"), ord("R")):
            installed = get_installed_packages()
            pkg_names = sorted(installed.keys())
            fetcher = VersionFetcher(pkg_names)
            nav_pos = min(nav_pos, max(0, len(pkg_names) - 1))
            selected.clear()
        elif key in (curses.KEY_UP, ord("i"), ord("k")):
            nav_pos = max(0, nav_pos - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
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
            installed = get_installed_packages()
            pkg_names = sorted(installed.keys())
            fetcher = VersionFetcher(pkg_names)
            nav_pos = min(nav_pos, max(0, len(pkg_names) - 1))
            selected.clear()
        elif key in (ord("u"), ord("U")) and selected:
            ops = []
            for t in selected:
                latest = fetcher.get(t)
                if latest is not _PENDING and latest and latest == installed.get(t):
                    continue  # already up to date
                ops.append(("update", t))
            if ops:
                _run_ops_outside_curses(stdscr, ops)
                installed = get_installed_packages()
                pkg_names = sorted(installed.keys())
                fetcher = VersionFetcher(pkg_names)
                selected.clear()


def show_status_text_mode():
    log_info("Checking globally installed npm packages...")
    print()
    installed = get_installed_packages()
    if not installed:
        print(f"  {Colors.YELLOW}No globally installed packages found.{Colors.NC}")
        return
    for name, version in sorted(installed.items()):
        print(f"  {Colors.GREEN}✓{Colors.NC} {name}@{version}")
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
