"""``iterm-setup`` - install bundled iTerm2 Python scripts and a keyboard shortcut.

Migrated from ``shell/iterm-setup``. macOS-only (iTerm2).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from importlib import resources
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.platform import require_platform
from toolscripts.core.prompts import yes_no
from toolscripts.core.shell import which

log = get_logger(__name__)

ITERM_APP = Path("/Applications/iTerm.app")
ITERM_SCRIPTS = Path.home() / "Library/Application Support/iTerm2/Scripts"
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


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="iterm-setup",
        description="Install iTerm2 Python scripts and a keyboard shortcut (macOS).",
    )
    parser.add_argument(
        "--no-shortcut", action="store_true", help="do not configure keyboard shortcut"
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    require_platform("macos")

    if not ITERM_APP.is_dir() and not yes_no(
        "iTerm2 was not detected in /Applications - continue anyway?", default=False
    ):
        log.info("cancelled")
        return

    ITERM_SCRIPTS.mkdir(parents=True, exist_ok=True)
    ITERM_AUTOLAUNCH.mkdir(parents=True, exist_ok=True)

    src = _bundled_scripts_dir()
    if src is None or not src.is_dir():
        log.error("bundled iterm scripts not found - re-install the package")
        sys.exit(1)

    for script in src.glob("*.py"):
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

    if which("which"):
        return


if __name__ == "__main__":
    main()
