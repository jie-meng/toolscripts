"""``iterm-setup`` - install bundled iTerm2 Python scripts and a keyboard shortcut.

Migrated from ``shell/iterm-setup``. macOS-only (iTerm2).
"""

from __future__ import annotations

import argparse
import plistlib
import shutil
import subprocess
import sys
from importlib import resources
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.platform import require_platform
from toolscripts.core.prompts import yes_no
from toolscripts.core.shell import capture, which

log = get_logger(__name__)

ITERM_APP = Path("/Applications/iTerm.app")
ITERM_APPSUPPORT = Path.home() / "Library/Application Support/iTerm2"
ITERM_SCRIPTS = ITERM_APPSUPPORT / "Scripts"
ITERM_AUTOLAUNCH = ITERM_SCRIPTS / "AutoLaunch"
PLIST = Path.home() / "Library/Preferences/com.googlecode.iterm2.plist"
PLIST_BUDDY = "/usr/libexec/PlistBuddy"

# (plist key, human-readable shortcut, iTerm2 action id, action parameter).
# The plist key is "<character>-<modifiers>-<virtual key code>"; 0x180000 is
# Cmd+Opt. Action ids come from iterm2.binding.BindingAction in the Python API
# bundled with iTerm2.
ACTION_INVOKE_SCRIPT_FUNCTION = 60
ACTION_SWAP_PANE_LEFT = 53

SHORTCUTS = [
    ("0x6c-0x180000-0x25", "Cmd+Opt+L", ACTION_INVOKE_SCRIPT_FUNCTION, "split_vertical_quarter()"),
    # iTerm2's built-in "Swap With Split Pane on Left" key action, so no
    # script is needed (no swap RPC in the Python API, no menu item).
    ("0x6b-0x180000-0x28", "Cmd+Opt+K", ACTION_SWAP_PANE_LEFT, ""),
]


def _bundled_scripts_dir() -> Path | None:
    try:
        ref = resources.files("toolscripts.data.iterm")
    except (ModuleNotFoundError, AttributeError):
        return None
    try:
        with resources.as_file(ref) as path:
            return Path(path)
    except Exception:  # noqa: BLE001
        return None


def _bundled_scripts() -> list[Path]:
    """Shipped scripts, excluding the data package's own ``__init__.py``."""
    src = _bundled_scripts_dir()
    if src is None or not src.is_dir():
        return []
    return sorted(p for p in src.glob("*.py") if p.name != "__init__.py")


def _plist_buddy(*args: str) -> bool:
    if not Path(PLIST_BUDDY).is_file():
        log.warning("PlistBuddy not found; skipping shortcut configuration")
        return False
    res = subprocess.run([PLIST_BUDDY, *args, str(PLIST)], capture_output=True, text=True)
    return res.returncode == 0


def _configure_shortcuts() -> None:
    # Creating the container fails when it already exists, which is expected.
    _plist_buddy("-c", "Add :GlobalKeyMap dict")
    for key, label, action, param in SHORTCUTS:
        log.info("configuring %s ...", label)
        _plist_buddy("-c", f"Delete :GlobalKeyMap:{key}")
        if not _plist_buddy("-c", f"Add :GlobalKeyMap:{key} dict"):
            log.error("could not add %s; skipping", label)
            continue
        _plist_buddy("-c", f"Add :GlobalKeyMap:{key}:Action integer {action}")
        if action == ACTION_INVOKE_SCRIPT_FUNCTION:
            # Extra fields iTerm2's own preferences UI writes for text actions.
            _plist_buddy("-c", f"Add :GlobalKeyMap:{key}:'Apply Mode' integer 0")
            _plist_buddy("-c", f"Add :GlobalKeyMap:{key}:Escaping integer 2")
            _plist_buddy("-c", f"Add :GlobalKeyMap:{key}:Version integer 2")
        _plist_buddy("-c", f"Add :GlobalKeyMap:{key}:Text string '{param}'")
        log.success("%s -> action %d", label, action)


def _prefs() -> dict:
    if not PLIST.is_file():
        return {}
    with PLIST.open("rb") as handle:
        return plistlib.load(handle)


def _report_runtime() -> None:
    # iTerm2 3.7+ runs scripts from a uv-managed venv; older versions use the
    # bundled iterm2env tree. Either one being absent means scripts never start.
    venvs = ITERM_APPSUPPORT / "uv" / "venvs"
    if venvs.is_dir():
        names = sorted(p.name for p in venvs.iterdir() if p.is_dir())
        if names:
            log.success("python runtime: uv venv %s", ", ".join(names))
            return
    legacy = ITERM_APPSUPPORT / "iterm2env" / "versions"
    if legacy.is_dir():
        names = sorted(p.name for p in legacy.iterdir() if p.is_dir())
        if names:
            log.success("python runtime: iterm2env %s", ", ".join(names))
            return
    log.warning("python runtime: not installed - Scripts > Manage > Install Python Runtime")


def _report_scripts() -> None:
    running = capture(["pgrep", "-fl", "AutoLaunch"], check=False)
    for script in _bundled_scripts():
        if not (ITERM_AUTOLAUNCH / script.name).is_file():
            log.warning("%s: not installed", script.name)
            continue
        if script.stem in running:
            log.success("%s: installed, running", script.name)
        else:
            log.warning(
                "%s: installed but NOT running, so its functions are not registered; "
                "quit iTerm2 (Cmd+Q) and reopen",
                script.name,
            )


def _report_status() -> None:
    version = ITERM_APPSUPPORT / "version.txt"
    log.info("iTerm2 %s", version.read_text().strip() if version.is_file() else "?")

    prefs = _prefs()
    if prefs.get("EnableAPIServer"):
        log.success("python api: enabled")
    else:
        log.warning("python api: disabled - enable it in Preferences > General > Magic")

    _report_runtime()

    if not _bundled_scripts():
        log.error("bundled iterm scripts not found - re-install the package")
        return
    _report_scripts()

    keymap = prefs.get("GlobalKeyMap")
    if not isinstance(keymap, dict):
        keymap = {}
    for key, label, action, param in SHORTCUTS:
        binding = keymap.get(key)
        if not isinstance(binding, dict):
            log.warning("%s: not bound - re-run iterm-setup", label)
        elif binding.get("Action") == action:
            log.success("%s: bound to action %d (%s)", label, action, param or "built-in")
        else:
            log.warning("%s: bound to action %s, expected %d", label, binding.get("Action"), action)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="iterm-setup",
        description="Install iTerm2 Python scripts and a keyboard shortcut (macOS).",
    )
    parser.add_argument(
        "--no-shortcut", action="store_true", help="do not configure keyboard shortcut"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="diagnose why the shortcut does not work (runtime, AutoLaunch, binding)",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    require_platform("macos")

    if args.status:
        _report_status()
        return

    if not ITERM_APP.is_dir() and not yes_no(
        "iTerm2 was not detected in /Applications - continue anyway?", default=False
    ):
        log.info("cancelled")
        return

    ITERM_SCRIPTS.mkdir(parents=True, exist_ok=True)
    ITERM_AUTOLAUNCH.mkdir(parents=True, exist_ok=True)

    scripts = _bundled_scripts()
    if not scripts:
        log.error("bundled iterm scripts not found - re-install the package")
        sys.exit(1)

    for script in scripts:
        target = ITERM_AUTOLAUNCH / script.name
        shutil.copyfile(script, target)
        target.chmod(0o755)
        log.success("installed %s", target)

    if not args.no_shortcut:
        _configure_shortcuts()

    log.info(
        "next steps: completely quit iTerm2 (Cmd+Q) and reopen so the AutoLaunch script picks up;"
        " also enable 'Python API' in iTerm2 Preferences -> General -> Magic"
    )
    log.info("if the shortcut later reports 'No function registered', run: iterm-setup --status")

    if which("which"):
        return


if __name__ == "__main__":
    main()
