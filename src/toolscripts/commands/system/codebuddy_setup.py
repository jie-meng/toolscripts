"""``codebuddy-setup`` - install the CodeBuddy PreToolUse hook that auto-approves
temp-dir cleanups.

CodeBuddy hard-codes ``rm -rf`` as a HIGH risk command that always prompts in
interactive sessions, and permission ``allow`` rules cannot cover compound
commands (every subcommand must match one single rule). The bundled
``allow-tmp-removal.py`` PreToolUse hook is the only reliable escape hatch: it
emits ``permissionDecision: "allow"`` for commands whose only destructive part
is a ``/tmp`` cleanup, so those never pop the "High risk operation detected"
dialog.

What this command does (all idempotent):

* copy the bundled hook to ``~/.codebuddy/hooks/allow-tmp-removal.py``
* merge a ``hooks.PreToolUse`` entry into ``~/.codebuddy/settings.json``
  (Bash matcher) without touching any of your other settings

See ``docs-pick`` -> ``ai/CODEBUDDY-TMP-CLEANUP-HOOK.md`` for the design
rationale and the exact safety boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from importlib import resources
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)

HOOK_NAME = "allow-tmp-removal.py"
MATCHER = "Bash"
_HOOK_MARKER = "allow-tmp-removal.py"

HOOK_DIR = Path.home() / ".codebuddy" / "hooks"
SETTINGS_PATH = Path.home() / ".codebuddy" / "settings.json"


def _bundled_hook() -> Path | None:
    """Return the bundled hook file, or an in-repo fallback when uninstalled."""
    try:
        ref = resources.files("toolscripts.data.codebuddy").joinpath(HOOK_NAME)
        with resources.as_file(ref) as path:
            if path.is_file():
                return Path(path)
    except (ModuleNotFoundError, AttributeError, FileNotFoundError):
        pass
    fallback = Path(__file__).resolve().parents[2] / "data" / "codebuddy" / HOOK_NAME
    return fallback if fallback.is_file() else None


def _sha256(path: Path | None) -> str:
    if not path or not path.is_file():
        return "-"
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _load_settings() -> dict:
    if not SETTINGS_PATH.is_file():
        return {}
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"cannot parse {SETTINGS_PATH}: {exc}") from exc


def _write_settings(cfg: dict) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _bash_entries(cfg: dict) -> list[dict]:
    entries = (cfg.get("hooks") or {}).get("PreToolUse") or []
    out = []
    for entry in entries:
        if isinstance(entry, dict) and str(entry.get("matcher", "")).lower() == MATCHER.lower():
            out.append(entry)
    return out


def _references_hook(entry: dict) -> bool:
    return any(_HOOK_MARKER in str(h.get("command", "")) for h in entry.get("hooks") or [])


def _install_hook_file(force: bool) -> Path | None:
    bundled = _bundled_hook()
    if bundled is None:
        log.error("bundled hook not found - re-install the package")
        return None
    HOOK_DIR.mkdir(parents=True, exist_ok=True)
    target = HOOK_DIR / HOOK_NAME
    if force or not target.is_file() or target.read_text(encoding="utf-8") != bundled.read_text(encoding="utf-8"):
        shutil.copyfile(bundled, target)
        target.chmod(0o755)
        if force:
            log.success("hook rewritten from bundled template: %s", target)
        else:
            log.success("installed hook: %s", target)
    else:
        log.success("hook already current: %s", target)
    return target


def _install(force: bool = False) -> None:
    target = _install_hook_file(force)
    if target is None:
        sys.exit(1)

    cfg = _load_settings()
    if _bash_entries(cfg) and any(_references_hook(e) for e in _bash_entries(cfg)):
        log.success("settings already reference the hook (no change to %s)", SETTINGS_PATH)
        return

    cmd = f"python3 {target}"
    bash = next(iter(_bash_entries(cfg)), None)
    if bash is None:
        cfg.setdefault("hooks", {}).setdefault("PreToolUse", []).append(
            {"matcher": MATCHER, "hooks": [{"type": "command", "command": cmd}]}
        )
        log.success("added PreToolUse/%s entry to %s", MATCHER, SETTINGS_PATH)
    else:
        bash.setdefault("hooks", []).append({"type": "command", "command": cmd})
        log.success("added hook command to existing PreToolUse/%s entry", MATCHER)
    _write_settings(cfg)
def _report_status() -> None:
    if not SETTINGS_PATH.is_file():
        log.warning("settings not found at %s - run codebuddy-setup to install", SETTINGS_PATH)
    else:
        cfg = _load_settings()
        matched = _bash_entries(cfg)
        if matched and any(_references_hook(e) for e in matched):
            log.success("settings: PreToolUse/%s entry present in %s", MATCHER, SETTINGS_PATH)
        else:
            log.warning("settings: no PreToolUse/%s entry referencing %s in %s", MATCHER, HOOK_NAME, SETTINGS_PATH)

    target = HOOK_DIR / HOOK_NAME
    if not target.is_file():
        log.warning("hook file missing at %s - run codebuddy-setup to install", target)
    else:
        bundled = _bundled_hook()
        if bundled is not None and _sha256(bundled) == _sha256(target):
            log.success("hook file present and matches bundled template (%s)", target)
        else:
            log.warning("hook file present but DIFFERS from bundled template (yours may be customized)")
            log.warning("  bundled: %s, on disk: %s", _sha256(bundled), _sha256(target))

    log.info("why this hook exists + how it behaves: run `docs-pick` -> ai/CODEBUDDY-TMP-CLEANUP-HOOK.md")


def _remove() -> None:
    cfg = _load_settings()
    entries = (cfg.get("hooks") or {}).get("PreToolUse")
    if not entries:
        log.info("nothing to remove - no PreToolUse entries")
        return

    kept, removed = [], False
    for entry in entries:
        if not isinstance(entry, dict) or str(entry.get("matcher", "")).lower() != MATCHER.lower():
            kept.append(entry)
            continue
        hooks = [h for h in entry.get("hooks") or [] if _HOOK_MARKER not in str(h.get("command", ""))]
        if len(hooks) != len(entry.get("hooks") or []):
            removed = True
        if hooks:
            entry["hooks"] = hooks
            kept.append(entry)
        # entry with no hooks left is dropped entirely

    if not removed:
        log.info("settings: hook entry not found; nothing removed")
        return
    cfg["hooks"]["PreToolUse"] = kept
    if not cfg["hooks"]["PreToolUse"]:
        del cfg["hooks"]["PreToolUse"]
    if not cfg.get("hooks"):
        del cfg["hooks"]
    _write_settings(cfg)
    log.success("removed hook entry from %s", SETTINGS_PATH)
    log.info("hook file left at %s (delete it manually if you want it gone)", HOOK_DIR / HOOK_NAME)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="codebuddy-setup",
        description=(
            "Install/verify the CodeBuddy PreToolUse hook that auto-approves temp-dir "
            "cleanups, so `rm -rf /tmp/...` compound commands stop asking every time."
        ),
    )
    parser.add_argument("--status", action="store_true", help="check the current installation state")
    parser.add_argument(
        "--remove", action="store_true", help="remove the PreToolUse entry from settings (keeps the hook file)"
    )
    parser.add_argument(
        "--force", action="store_true", help="rewrite the on-disk hook from the bundled template"
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    if args.status:
        _report_status()
    elif args.remove:
        _remove()
    else:
        _install(force=args.force)


if __name__ == "__main__":
    main()
    log.info("no codebuddy restart needed - hooks are re-executed on every tool call")