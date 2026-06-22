"""``uvcmd`` - interactive browser for common ``uv`` commands."""

from __future__ import annotations

import argparse
import contextlib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import CommandNotFoundError, require, run

log = get_logger(__name__)


@dataclass
class UvCommand:
    name: str
    command: str
    base_args: list[str]
    description: str
    examples: list[str]
    needs_args: bool = False
    needs_project: bool = False


_UV_COMMANDS: list[UvCommand] = [
    # ── Python management (do first, before any project work) ──────────────
    UvCommand(
        name="Python list",
        command="uv python list",
        base_args=["python", "list"],
        description="Run anywhere. "
        "Lists all Python interpreters known to uv — both uv-managed installations "
        "and system/Homebrew/pyenv Pythons. Shows path or '<download available>'.",
        examples=[
            "uv python list          # all interpreters",
            "uv python list --only-installed  # only installed ones",
        ],
    ),
    UvCommand(
        name="Python install",
        command="uv python install <VERSION>",
        base_args=["python", "install"],
        description="Run anywhere — installs globally into ~/.local/share/uv/python/. "
        "Downloads and installs a specific Python version managed by uv. "
        "You will be shown a picker of available versions to select from.",
        examples=[
            "uv python install 3.13",
            "uv python install 3.12.10",
            "uv python install cpython-3.11.14-macos-aarch64-none",
        ],
    ),
    UvCommand(
        name="Python uninstall",
        command="uv python uninstall <VERSION>",
        base_args=["python", "uninstall"],
        description="Run anywhere — uninstalls from ~/.local/share/uv/python/. "
        "Removes a uv-managed Python installation. "
        "You will be shown a picker of installed versions to select from.",
        examples=[
            "uv python uninstall 3.11.14",
            "uv python uninstall cpython-3.11.14-macos-aarch64-none",
        ],
    ),
    # ── Project setup ──────────────────────────────────────────────────────
    UvCommand(
        name="Init project",
        command="uv init [OPTIONS]",
        base_args=["init"],
        description="Run in an empty directory where you want to start a new project. "
        "Creates pyproject.toml + src/ layout — a minimal, PEP-compliant scaffold.",
        examples=[
            "uv init                 # creates pyproject.toml + src/",
            "uv init --name my-lib  # name the package",
            "uv init --lib          # start a library (src/ layout, no __main__)",
            "uv init --package     # start a package (src/ layout)",
        ],
    ),
    UvCommand(
        name="Create venv",
        command="uv venv [OPTIONS]",
        base_args=["venv"],
        description="Run in your project directory (after uv init). "
        "Creates a virtual environment (default: .venv) and writes .python-version. "
        "You will be prompted to pick from uv-managed Python versions already installed.",
        examples=[
            "uv venv                # use Python from pyproject.toml or default",
            "uv venv --python 3.12 # use Python 3.12",
            "uv venv .venv --python python3.11",
        ],
    ),
    UvCommand(
        name="Python pin",
        command="uv python pin <VERSION>",
        base_args=["python", "pin"],
        description="Run in the project root (where pyproject.toml is). "
        "Writes .python-version to pin the interpreter used by uv run and uv sync.",
        examples=[
            "uv python pin 3.12",
            "uv python pin 3.11.8",
        ],
        needs_args=True,
    ),
    # ── Dependency management ──────────────────────────────────────────────
    UvCommand(
        name="Add dependency",
        command="uv add <PACKAGE> [OPTIONS]",
        base_args=["add"],
        description="Run in the project root (where pyproject.toml is). "
        "Adds one or more packages to pyproject.toml and updates the lockfile. "
        "Dev-only deps use --dev.",
        examples=[
            "uv add requests            # latest version",
            "uv add 'requests>=2.28'    # with version constraint",
            "uv add --dev pytest        # dev dependency",
            "uv add git+https://...      # from git",
        ],
        needs_args=True,
        needs_project=True,
    ),
    UvCommand(
        name="Remove dependency",
        command="uv remove <PACKAGE>",
        base_args=["remove"],
        description="Run in the project root (where pyproject.toml is). "
        "Removes a package from pyproject.toml and updates the lockfile.",
        examples=[
            "uv remove requests",
            "uv remove pytest --dev",
        ],
        needs_args=True,
        needs_project=True,
    ),
    UvCommand(
        name="Sync / install",
        command="uv sync [OPTIONS]",
        base_args=["sync"],
        description="Run in the project root (where pyproject.toml is). "
        "Syncs the virtual environment with the lockfile — installs, removes, or "
        "updates packages to match pyproject.toml.",
        examples=[
            "uv sync               # install all deps from lockfile",
            "uv sync --all-packages  # include dev deps",
            "uv sync --no-dev     # skip dev dependencies",
        ],
        needs_project=True,
    ),
    UvCommand(
        name="Lock (generate)",
        command="uv lock [OPTIONS]",
        base_args=["lock"],
        description="Run in the project root (where pyproject.toml is). "
        "Updates uv.lock to reflect changes in pyproject.toml. "
        "Always safe — reads the existing lock and minimizes changes.",
        examples=[
            "uv lock              # update uv.lock",
            "uv lock --upgrade    # upgrade all packages to latest",
            "uv lock --upgrade-package requests  # upgrade one",
        ],
        needs_project=True,
    ),
    # ── Running code ───────────────────────────────────────────────────────
    UvCommand(
        name="Run script",
        command="uv run <SCRIPT> [OPTIONS]",
        base_args=["run"],
        description="Run in the project root (where pyproject.toml is). "
        "Runs a Python script or command in an environment configured by pyproject.toml. "
        "Automatically resolves and installs dependencies.",
        examples=[
            "uv run python main.py          # run a script",
            "uv run -- pytest tests/        # run pytest",
            "uv run python -c 'print(1)'    # inline command",
        ],
        needs_args=True,
        needs_project=True,
    ),
    UvCommand(
        name="Run shell",
        command="uv run python",
        base_args=["run", "--python", "python3"],
        description="Run in the project root (where pyproject.toml is). "
        "Opens an interactive Python REPL with all project dependencies available.",
        examples=[
            "uv run python                    # basic REPL",
            "uv run --python python3.12       # specific Python REPL",
        ],
        needs_project=True,
    ),
    # ── Project info ───────────────────────────────────────────────────────
    UvCommand(
        name="Tree (deps)",
        command="uv tree [OPTIONS]",
        base_args=["tree"],
        description="Run in the project root (where pyproject.toml is). "
        "Displays the dependency tree of the current project.",
        examples=[
            "uv tree",
            "uv tree --depth 2       # limit depth",
            "uv tree --no-dedupe     # show all duplicates",
        ],
        needs_project=True,
    ),
    UvCommand(
        name="Check project",
        command="uv check [OPTIONS]",
        base_args=["check"],
        description="Run in the project root (where pyproject.toml is). "
        "Verifies that locked dependencies satisfy pyproject.toml constraints. "
        "Used in CI to check lockfile freshness.",
        examples=[
            "uv check",
            "uv check --strict   # also check that all env vars are declared",
        ],
        needs_project=True,
    ),
    # ── Publishing ─────────────────────────────────────────────────────────
    UvCommand(
        name="Build package",
        command="uv build [OPTIONS]",
        base_args=["build"],
        description="Run in the project root (where pyproject.toml is). "
        "Builds source and wheel distributions for publishing. Outputs to dist/.",
        examples=[
            "uv build                 # build sdist + wheel",
            "uv build --sdist         # source distribution only",
            "uv build --wheel        # wheel only",
        ],
        needs_project=True,
    ),
    UvCommand(
        name="Publish to PyPI",
        command="uv publish [OPTIONS]",
        base_args=["publish"],
        description="Run in the project root (where pyproject.toml is). "
        "Uploads built distributions from dist/ to PyPI. "
        "Reads credentials from pyproject.toml or --token.",
        examples=[
            "uv publish                    # upload dist/*",
            "uv publish --token pypi-xxx   # with explicit token",
            "uv publish --repository testpypi  # TestPyPI",
        ],
        needs_project=True,
    ),
    # ── pip (non-project / active venv) ───────────────────────────────────
    UvCommand(
        name="Pip install",
        command="uv pip install <PACKAGE> [OPTIONS]",
        base_args=["pip", "install"],
        description="Run anywhere with an active virtual environment. "
        "Installs packages directly into the active Python environment (not a project). "
        "Activate a venv first with: source .venv/bin/activate",
        examples=[
            "uv pip install requests        # into active venv",
            "uv pip install -r requirements.txt",
            "uv pip install --system        # system Python (requires --system)",
        ],
        needs_args=True,
    ),
    UvCommand(
        name="Pip uninstall",
        command="uv pip uninstall <PACKAGE>",
        base_args=["pip", "uninstall"],
        description="Run anywhere with an active virtual environment. "
        "Uninstalls packages from the active Python environment.",
        examples=[
            "uv pip uninstall requests",
            "uv pip uninstall -r requirements.txt",
        ],
        needs_args=True,
    ),
    UvCommand(
        name="Pip list",
        command="uv pip list [OPTIONS]",
        base_args=["pip", "list"],
        description="Run anywhere with an active virtual environment. "
        "Lists all packages installed in the active Python environment.",
        examples=[
            "uv pip list                  # all packages",
            "uv pip list --outdated       # packages with newer versions",
            "uv pip list --format freeze  # pip freeze format",
        ],
    ),
    UvCommand(
        name="Pip freeze",
        command="uv pip freeze",
        base_args=["pip", "freeze"],
        description="Run anywhere with an active virtual environment. "
        "Outputs all installed packages in requirements.txt format.",
        examples=[
            "uv pip freeze > requirements.txt  # save current env",
        ],
    ),
    # ── Global tools ───────────────────────────────────────────────────────
    UvCommand(
        name="Tool install",
        command="uv tool install <PACKAGE> [OPTIONS]",
        base_args=["tool", "install"],
        description="Run anywhere — installs globally. "
        "Installs a standalone CLI tool and makes its executables available on $PATH.",
        examples=[
            "uv tool install httpie           # install a CLI tool",
            "uv tool install --python 3.12 ruff  # specific Python",
            "uv tool install --from git+https://... some-tool",
        ],
        needs_args=True,
    ),
    UvCommand(
        name="Tool run",
        command="uv tool run <TOOL>",
        base_args=["tool", "run"],
        description="Run anywhere. "
        "Runs a named tool from the tool cache without installing it permanently. "
        "Shorthand: uvx <TOOL>.",
        examples=[
            "uv tool run ruff check .",
            "uvx pycowsay hello",
        ],
        needs_args=True,
    ),
    UvCommand(
        name="Tool list",
        command="uv tool list",
        base_args=["tool", "list"],
        description="Run anywhere. " "Lists all installed standalone tools and their executables.",
        examples=[
            "uv tool list --show-paths",
        ],
    ),
    UvCommand(
        name="Tool update",
        command="uv tool update <TOOL>",
        base_args=["tool", "update"],
        description="Run anywhere — updates globally installed tools. "
        "Updates installed tools to their latest versions.",
        examples=[
            "uv tool update          # update all",
            "uv tool update ruff     # update one",
        ],
    ),
    # ── Cache ──────────────────────────────────────────────────────────────
    UvCommand(
        name="Cache clean",
        command="uv cache clean [OPTIONS]",
        base_args=["cache", "clean"],
        description="Run anywhere. "
        "Deletes the uv cache — downloaded wheels, built wheels, and other cached data.",
        examples=[
            "uv cache clean              # clean everything",
            "uv cache clean --package requests  # clean one package only",
        ],
    ),
    UvCommand(
        name="Cache dir",
        command="uv cache dir",
        base_args=["cache", "dir"],
        description="Run anywhere. Prints the path to the uv cache directory.",
        examples=[
            "uv cache dir",
        ],
    ),
]


def _is_project() -> bool:
    return Path("pyproject.toml").is_file()


def _get_uv_python_installed() -> list[str]:
    """Return unique installed Python version keys known to uv (deduped)."""
    try:
        out = subprocess.check_output(
            ["uv", "python", "list", "--only-installed"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    seen: set[str] = set()
    result: list[str] = []
    for line in out.splitlines():
        parts = line.split()
        if parts and parts[0] not in seen:
            seen.add(parts[0])
            result.append(parts[0])
    return result


def _get_uv_python_downloadable() -> list[str]:
    """Return version keys available for download but not yet installed."""
    try:
        out = subprocess.check_output(
            ["uv", "python", "list"], text=True, stderr=subprocess.DEVNULL
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    installed_keys: set[str] = set()
    downloadable: list[str] = []
    seen_dl: set[str] = set()
    for line in out.splitlines():
        parts = line.split()
        if not parts:
            continue
        key = parts[0]
        is_download = len(parts) >= 2 and parts[1].startswith("<download")
        if is_download:
            if key not in seen_dl:
                seen_dl.add(key)
                downloadable.append(key)
        else:
            installed_keys.add(key)
    return [k for k in downloadable if k not in installed_keys]


def _run_interactive_command(cmd: UvCommand) -> None:
    if cmd.needs_project and not _is_project():
        print(
            "No pyproject.toml found in the current directory.\n"
            "This command requires a project context.\n"
            "Hint: run 'uv init' first, or 'cd' into a project directory."
        )
        return

    if cmd.name == "Create venv":
        _handle_venv_create()
        return

    if cmd.name == "Python install":
        _handle_python_install()
        return

    if cmd.name == "Python uninstall":
        _handle_python_uninstall()
        return

    if cmd.name == "Add dependency":
        _handle_add_dependency()
        return

    if cmd.name == "Remove dependency":
        _handle_remove_dependency()
        return

    if cmd.name == "Sync / install":
        _handle_sync()
        return

    args: list[str] = []
    if cmd.needs_args:
        prompt = "Enter argument (package name, path, etc.): "
        try:
            raw = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not raw:
            print("Cancelled.")
            return
        args = raw.split()

    run(["uv", *cmd.base_args, *args])


def _handle_venv_create() -> None:
    from toolscripts.core.ui_curses import select_one

    print("Fetching installed Python versions from uv...")
    versions = _get_uv_python_installed()
    if not versions:
        print(
            "No Python versions found via uv.\n"
            "Hint: use 'Python install' in this browser to install one first."
        )
        return

    idx = select_one("Select Python version for venv", versions)
    if idx is None:
        print("Cancelled.")
        return
    selected = versions[idx]

    venv_name = ".venv"
    try:
        venv_raw = input(f"venv directory [{venv_name}]: ").strip()
        if venv_raw:
            venv_name = venv_raw
    except (EOFError, KeyboardInterrupt):
        print()
        return

    # Extract bare version string (e.g. cpython-3.13.3-macos-aarch64-none -> 3.13.3)
    parts = selected.split("-")
    version_str = parts[1] if len(parts) > 1 and parts[1][0].isdigit() else selected
    Path(".python-version").write_text(version_str + "\n", encoding="utf-8")
    run(["uv", "venv", venv_name, "--python", selected])
    print(f"\nCreated {venv_name} with Python {selected}")
    print(f"Activate with: source {venv_name}/bin/activate")


def _handle_python_install() -> None:
    from toolscripts.core.ui_curses import select_many

    print("Fetching available Python versions from uv...")
    versions = _get_uv_python_downloadable()
    if not versions:
        print("No additional Python versions available for download (all are already installed).")
        return

    indices = select_many("Select Python versions to install", versions)
    if indices is None:
        print("Cancelled.")
        return
    if not indices:
        print("No versions selected.")
        return

    for i in indices:
        run(["uv", "python", "install", versions[i]])


def _handle_python_uninstall() -> None:
    from toolscripts.core.ui_curses import select_many

    print("Fetching installed Python versions from uv...")
    versions = _get_uv_python_installed()
    if not versions:
        print("No uv-managed Python versions found.")
        return

    indices = select_many("Select Python versions to uninstall", versions)
    if indices is None:
        print("Cancelled.")
        return
    if not indices:
        print("No versions selected.")
        return

    for i in indices:
        run(["uv", "python", "uninstall", versions[i]])


def _handle_add_dependency() -> None:
    from toolscripts.core.ui_curses import select_one

    try:
        raw = input("Package name (e.g. requests, 'fastapi>=0.100'): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    if not raw:
        print("Cancelled.")
        return

    choice = select_one(
        "Dependency type?",
        [
            "Runtime      uv add <package>",
            "Dev          uv add <package> --dev",
            "Optional     uv add <package> --optional <group>",
        ],
    )
    if choice is None:
        print("Cancelled.")
        return

    if choice == 0:
        run(["uv", "add", *raw.split()])
    elif choice == 1:
        run(["uv", "add", "--dev", *raw.split()])
    else:
        try:
            group = input("Optional group name (e.g. viz, docs): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not group:
            print("Cancelled.")
            return
        run(["uv", "add", "--optional", group, *raw.split()])


def _handle_remove_dependency() -> None:
    from toolscripts.core.ui_curses import select_one

    try:
        raw = input("Package name to remove: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    if not raw:
        print("Cancelled.")
        return

    choice = select_one(
        "Remove from which group?",
        [
            "Runtime      uv remove <package>",
            "Dev          uv remove <package> --dev",
        ],
    )
    if choice is None:
        print("Cancelled.")
        return

    dev_flag = ["--dev"] if choice == 1 else []
    run(["uv", "remove", *dev_flag, *raw.split()])


def _handle_sync() -> None:
    from toolscripts.core.ui_curses import select_one

    choice = select_one(
        "Sync mode?",
        [
            "All deps          uv sync             (runtime + dev)",
            "Production only   uv sync --no-dev    (skip dev, use for deploy)",
            "All packages      uv sync --all-packages  (include optional groups)",
        ],
    )
    if choice is None:
        print("Cancelled.")
        return

    if choice == 0:
        run(["uv", "sync"])
    elif choice == 1:
        run(["uv", "sync", "--no-dev"])
    else:
        run(["uv", "sync", "--all-packages"])


def _ensure_curses() -> None:
    try:
        import curses  # noqa: F401

        return
    except ImportError:
        from toolscripts.core.log import get_logger

        log = get_logger(__name__)
        if sys.platform == "win32":
            log.error("curses not available on Windows. Install with: pip install windows-curses")
        else:
            log.error("curses module not available on this Python build.")
        sys.exit(1)


def _run_curses(stdscr) -> None:
    import curses

    def _init_colors() -> None:
        curses.curs_set(0)
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.init_pair(4, curses.COLOR_WHITE, -1)
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)
        curses.init_pair(6, curses.COLOR_RED, -1)

    _init_colors()

    def cp(n: int) -> int:
        return curses.color_pair(n)

    commands = _UV_COMMANDS
    cursor = 0
    top = 0

    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        preview_top = height - 13
        list_height = max(1, preview_top - 4)

        title = " uvcmd - uv command browser "
        stdscr.addstr(0, 0, title.center(width, " "), cp(1) | curses.A_BOLD)
        hint = "j/k or arrows: move  |  gg/G jump  |  Enter: execute  |  q: quit"
        stdscr.addstr(1, 0, hint[:width], cp(3))
        stdscr.hline(2, 0, curses.ACS_HLINE, width)

        cmd = commands[cursor]

        visible_count = list_height
        if cursor < top:
            top = cursor
        elif cursor >= top + visible_count:
            top = cursor - visible_count + 1
        top = max(0, min(top, len(commands) - visible_count))

        for i in range(visible_count):
            idx = top + i
            if idx >= len(commands):
                break
            c = commands[idx]
            is_selected = idx == cursor
            marker = "▶" if is_selected else " "
            attr = curses.A_REVERSE if is_selected else 0
            color = cp(2) if is_selected else cp(4)

            name_text = f" {marker}  {c.name}"
            with contextlib.suppress(curses.error):
                stdscr.addstr(3 + i, 0, name_text[: width - 1], attr | color)

        stdscr.hline(preview_top - 1, 0, curses.ACS_HLINE, width)

        try:
            stdscr.addstr(preview_top, 2, "Command:", cp(5) | curses.A_BOLD)
            stdscr.addstr(preview_top + 1, 4, cmd.command[: width - 4], cp(2))
        except curses.error:
            pass

        desc_lines = _wrap(cmd.description, width - 4)
        try:
            stdscr.addstr(preview_top + 3, 2, "Description:", cp(5) | curses.A_BOLD)
            for li, line in enumerate(desc_lines[:3]):
                stdscr.addstr(preview_top + 4 + li, 4, line[: width - 4], cp(4))
        except curses.error:
            pass

        offset = preview_top + 4 + len(desc_lines[:3]) + 1
        with contextlib.suppress(curses.error):
            stdscr.addstr(offset, 2, "Examples:", cp(5) | curses.A_BOLD)
        for li, ex in enumerate(cmd.examples[:3]):
            line = f"  $ {ex}"
            with contextlib.suppress(curses.error):
                stdscr.addstr(offset + 1 + li, 4, line[: width - 4], cp(1))

        status = f"  {cursor + 1}/{len(commands)}"
        if _is_project():
            status += "  [project detected]"
        else:
            status += "  [no project]"
        with contextlib.suppress(curses.error):
            stdscr.addstr(height - 1, 0, status[: width - 1], cp(3))

        stdscr.refresh()
        key = stdscr.getch()

        if key in (curses.KEY_UP, ord("k")):
            cursor = max(0, cursor - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            cursor = min(len(commands) - 1, cursor + 1)
        elif key == ord("g"):
            key2 = stdscr.getch()
            if key2 == ord("g"):
                cursor = 0
        elif key == ord("G"):
            cursor = len(commands) - 1
        elif key in (curses.KEY_ENTER, 10, 13):
            curses.endwin()
            try:
                _run_interactive_command(commands[cursor])
            except Exception as exc:
                print(f"Error: {exc}")
            input("\nPress Enter to return to the browser...")
            # re-apply curses settings: the inner curses.wrapper() (used by
            # select_one/select_many) calls initscr() which overwrites the
            # saved prog mode, so reset_prog_mode() alone is insufficient.
            curses.noecho()
            curses.cbreak()
            stdscr.keypad(True)
            _init_colors()
            stdscr.clearok(True)
            stdscr.refresh()
        elif key in (ord("q"), 27):
            break


def _wrap(text: str, width: int) -> list[str]:
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
        if line:
            out.append(line)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="uvcmd",
        description="Interactive browser for common uv commands with live preview.",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        require("uv")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        log.warning("install uv: https://docs.astral.sh/uv/getting-started/installation/")
        sys.exit(1)

    _ensure_curses()
    import curses

    curses.wrapper(_run_curses)


if __name__ == "__main__":
    main()
