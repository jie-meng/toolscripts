"""``git-quick-commit`` - interactive commit wizard with pattern-based message suggestions.

Analyzes the current branch name and staged file paths/statuses to suggest
conventional commit messages — no AI, no network, instant.

Rules
-----
- Trunk branches (main, master, dev, develop, …) → plain message, no type prefix.
- Branches with a ``type/description`` pattern (feat/, fix/, refactor/, …)
  → conventional commit with the matching type and an inferred scope.
- Scope comes from the dominant top-level directory of the staged files.
- Action (add / update / remove) comes from git status codes.
- The TUI is a custom curses screen: branch info + staged summary at the top,
  message list in the middle, amend toggle at the bottom.
"""

from __future__ import annotations

import argparse
import contextlib
import re
import subprocess
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.prompts import yes_no
from toolscripts.core.shell import CommandNotFoundError, capture, require, run
from toolscripts.git_utils.repo import current_branch, is_git_repo

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TRUNK_BRANCHES: frozenset[str] = frozenset(
    {"main", "master", "dev", "develop", "development", "staging", "production", "trunk"}
)

_BRANCH_TYPE: dict[str, str] = {
    "feat": "feat",
    "feature": "feat",
    "fix": "fix",
    "bugfix": "fix",
    "hotfix": "fix",
    "refactor": "refactor",
    "chore": "chore",
    "docs": "docs",
    "doc": "docs",
    "test": "test",
    "tests": "test",
    "build": "build",
    "ci": "ci",
    "perf": "perf",
    "style": "style",
}

# File path regexes for category detection
_RE_DOCS = re.compile(
    r"(^docs?/|\.md$|\.rst$|\.txt$|README|CHANGELOG|CONTRIBUTING|LICENSE)",
    re.IGNORECASE,
)
_RE_TESTS = re.compile(r"(^tests?/|_test\.|test_|\.spec\.|\.test\.)", re.IGNORECASE)
_RE_CONFIG = re.compile(
    r"(\.github/|\.gitlab/|Makefile|Dockerfile|docker-compose"
    r"|pyproject\.toml|setup\.py|setup\.cfg|requirements.*\.txt"
    r"|\.ya?ml$|\.toml$|\.ini$|\.cfg$)",
    re.IGNORECASE,
)

_RE_VERSION_FILE = re.compile(
    r"(version\.txt$|VERSION$|package\.json$|pyproject\.toml$|setup\.py$|setup\.cfg$)",
    re.IGNORECASE,
)

_RE_VERSION_NUMBER = re.compile(r"(\d+\.\d+\.\d+(?:[-.][a-zA-Z0-9]+)*)")

_STATUS_LABEL: dict[str, str] = {
    "M": "modified",
    "A": "new",
    "D": "deleted",
    "R": "renamed",
    "C": "copied",
}

# ---------------------------------------------------------------------------
# Branch analysis
# ---------------------------------------------------------------------------


def _parse_branch(branch: str) -> tuple[str | None, str | None]:
    """Return (commit_type, description_hint) from branch name.

    Returns (None, None) for trunk branches → caller omits the type prefix.
    """
    if branch.lower() in TRUNK_BRANCHES:
        return None, None

    if "/" in branch:
        prefix, rest = branch.split("/", 1)
        commit_type = _BRANCH_TYPE.get(prefix.lower(), "feat")
        # Strip leading ticket numbers like PROJ-123- or 123-
        desc = re.sub(r"^[A-Z]+-\d+[-_]?|^\d+[-_]?", "", rest, flags=re.IGNORECASE)
        desc = re.sub(r"[-_]+", " ", desc).strip().lower()
        return commit_type, desc or None

    # Flat branch name — infer type from keywords
    lower = branch.lower()
    if any(kw in lower for kw in ("fix", "bug", "patch", "hotfix")):
        return "fix", re.sub(r"[-_]+", " ", branch).strip().lower()
    if any(kw in lower for kw in ("doc", "readme", "changelog")):
        return "docs", None
    if any(kw in lower for kw in ("test", "spec")):
        return "test", None
    if any(kw in lower for kw in ("refactor", "cleanup", "clean")):
        return "refactor", None
    if any(kw in lower for kw in ("chore", "deps", "build", "ci")):
        return "chore", None

    return "feat", re.sub(r"[-_]+", " ", branch).strip().lower()


# ---------------------------------------------------------------------------
# Staged file analysis
# ---------------------------------------------------------------------------


def _get_staged_info() -> tuple[list[tuple[str, str]], str]:
    """Return ([(status_code, path), ...], shortstat_line)."""
    raw = capture(["git", "diff", "--cached", "--name-status"], check=False)
    files: list[tuple[str, str]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        status_code = parts[0][0]  # first char: M, A, D, R, C …
        path = parts[-1]  # last field is the (new) path
        files.append((status_code, path))

    shortstat = capture(["git", "diff", "--cached", "--shortstat"], check=False).strip()
    return files, shortstat


def _dominant_scope(paths: list[str]) -> str:
    """Return the most common meaningful directory segment from staged paths."""
    counts: dict[str, int] = {}
    for p in paths:
        parts = Path(p).parts
        # Strip common wrapper dirs
        for skip in ("src", "toolscripts"):
            if parts and parts[0] == skip:
                parts = parts[1:]
        # Use first remaining segment if it looks like a directory (not a file)
        if len(parts) >= 2:
            counts[parts[0]] = counts.get(parts[0], 0) + 1

    return max(counts, key=lambda k: counts[k]) if counts else ""


def _classify_staged(files: list[tuple[str, str]]) -> dict:
    """Classify staged files; return a dict with category, scope, action."""
    statuses = [s for s, _ in files]
    paths = [p for _, p in files]
    n = len(paths)

    n_docs = sum(1 for p in paths if _RE_DOCS.search(p))
    n_tests = sum(1 for p in paths if _RE_TESTS.search(p))
    n_config = sum(1 for p in paths if _RE_CONFIG.search(p))

    if n_docs == n:
        category = "docs"
    elif n_tests == n:
        category = "test"
    elif n_config == n:
        category = "chore"
    else:
        category = "code"

    all_added = all(s == "A" for s in statuses)
    all_deleted = all(s == "D" for s in statuses)
    action = "add" if all_added else ("remove" if all_deleted else "update")

    scope = _dominant_scope(paths)

    # For a single file, use the stem as a secondary subject hint
    single_subject = ""
    if n == 1:
        single_subject = Path(paths[0]).stem.replace("_", " ").replace("-", " ").lower()

    return {
        "category": category,
        "scope": scope,
        "action": action,
        "single_subject": single_subject,
    }


def _detect_version_bump(files: list[tuple[str, str]]) -> str | None:
    """If staged files include version changes, return a 'bump version' message."""
    version_files = [p for _, p in files if _RE_VERSION_FILE.search(p)]
    if not version_files:
        return None

    for vf in version_files:
        diff = capture(["git", "diff", "--cached", "-U0", "--", vf], check=False)
        if not diff:
            continue

        old_version: str | None = None
        new_version: str | None = None
        for line in diff.splitlines():
            m = _RE_VERSION_NUMBER.search(line)
            if not m:
                continue
            if line.startswith("-"):
                old_version = m.group(1)
            elif line.startswith("+"):
                new_version = m.group(1)

        if old_version and new_version and old_version != new_version:
            return f"bump version to {new_version}"
        if new_version and not old_version:
            return f"set version to {new_version}"

    return None


# ---------------------------------------------------------------------------
# Message generation
# ---------------------------------------------------------------------------


def _fmt(commit_type: str | None, scope: str | None, msg: str) -> str:
    if commit_type is None:
        return msg
    if scope:
        return f"{commit_type}({scope}): {msg}"
    return f"{commit_type}: {msg}"


def generate_suggestions(branch: str, file_info: dict, files: list[tuple[str, str]]) -> list[str]:
    """Return up to 5 ranked commit message suggestions (no AI, pure patterns)."""
    version_msg = _detect_version_bump(files)

    commit_type, branch_desc = _parse_branch(branch)
    category = file_info["category"]
    scope = file_info["scope"]
    action = file_info["action"]
    single_subject = file_info["single_subject"]

    # For non-code categories, override commit type when branch doesn't specify
    if category == "docs" and commit_type in ("feat", None):
        effective_type = "docs" if commit_type == "feat" else None
    elif category == "test" and commit_type in ("feat", None):
        effective_type = "test" if commit_type == "feat" else None
    elif category == "chore" and commit_type in ("feat", None):
        effective_type = "chore" if commit_type == "feat" else None
    else:
        effective_type = commit_type

    # Build a natural-language subject
    if branch_desc:
        primary = branch_desc
    elif single_subject:
        primary = f"{action} {single_subject}"
    elif scope:
        primary = f"{action} {scope}"
    else:
        _fallbacks = {
            "docs": "update documentation",
            "test": "add tests",
            "chore": "update configuration",
            "code": "update implementation",
        }
        primary = _fallbacks.get(category, "update code")

    suggestions: list[str] = []

    def _add(t: str | None, s: str | None, msg: str) -> None:
        candidate = _fmt(t, s, msg)
        if candidate not in suggestions:
            suggestions.append(candidate)

    # 0. Version bump (highest priority when detected)
    if version_msg:
        _add(effective_type, scope or None, version_msg)

    # 1. Most specific: type(scope): branch_desc or derived subject
    _add(effective_type, scope or None, primary)

    # 2. Same type but without scope
    if scope:
        _add(effective_type, None, primary)

    # 3. Generic action phrase with scope
    generic = {
        "docs": "update docs",
        "test": "add unit tests",
        "chore": "update config",
        "code": f"{action} {scope}" if scope else f"{action} code",
    }.get(category, primary)
    _add(effective_type, scope or None, generic)

    # 4. If branch description is long, add a shortened version
    if branch_desc and len(branch_desc.split()) > 3:
        short = " ".join(branch_desc.split()[:3])
        _add(effective_type, scope or None, short)

    # 5. Plain imperative fallback without any prefix
    plain = primary
    if plain not in suggestions:
        suggestions.append(plain)

    # Deduplicate while preserving order, cap at 5
    seen: set[str] = set()
    result: list[str] = []
    for s in suggestions:
        s = s.strip()
        if s and s not in seen:
            seen.add(s)
            result.append(s)
    return result[:5]


# ---------------------------------------------------------------------------
# Curses TUI
# ---------------------------------------------------------------------------


def _run_commit_ui(
    branch: str,
    staged_files: list[tuple[str, str]],
    shortstat: str,
    suggestions: list[str],
) -> str | None:
    """Show a curses commit wizard.

    Returns the selected message, or None when the user cancels.

    Layout
    ------
    Row 0   : header — branch name + type hint
    Row 1   : staged shortstat
    Row 2…N : up to 4 staged file paths
    divider
    Row N+1 : "Commit message:" label
    Row N+2…: selectable suggestions + custom option
    divider
    Row -2  : key-binding hint
    """
    try:
        import curses
    except ImportError:
        log.error("curses module is not available; install windows-curses on Windows")
        sys.exit(1)

    commit_type, _ = _parse_branch(branch)
    type_hint = f"  [{commit_type}:]" if commit_type else "  [trunk]"

    file_lines: list[str] = []
    for s, p in staged_files[:4]:
        label = _STATUS_LABEL.get(s, s)
        file_lines.append(f"  \u2022 {p}  ({label})")
    if len(staged_files) > 4:
        file_lines.append(f"  \u2026 and {len(staged_files) - 4} more files")

    CUSTOM_LABEL = "[ \u270e enter custom message ]"
    items = suggestions + [CUSTOM_LABEL]

    state = {
        "cursor": 0,
        "edit_mode": False,
        "edit_buf": "",
        "result_msg": None,
        "cancelled": False,
    }

    def _draw(stdscr, cursor: int, edit_mode: bool, edit_buf: str) -> None:
        import curses

        stdscr.erase()
        h, w = stdscr.getmaxyx()
        safe = w - 1

        def put(row: int, text: str, attr: int = 0) -> None:
            with contextlib.suppress(curses.error):
                stdscr.addstr(row, 0, text[:safe], attr)

        row = 0
        put(
            row,
            f" git-quick-commit  branch: {branch}{type_hint}",
            curses.A_BOLD | curses.color_pair(1),
        )
        row += 1
        put(row, f" staged: {shortstat}", curses.color_pair(3))
        row += 1
        for fline in file_lines:
            put(row, fline, curses.color_pair(4))
            row += 1

        with contextlib.suppress(curses.error):
            stdscr.hline(row, 0, curses.ACS_HLINE, w)
        row += 1

        if not edit_mode:
            put(row, " Commit message:", curses.A_BOLD | curses.color_pair(4))
            row += 1
            for i, item in enumerate(items):
                is_sel = i == cursor
                marker = ">" if is_sel else " "
                attr = curses.A_BOLD | curses.A_REVERSE if is_sel else 0
                color = (
                    curses.color_pair(3)
                    if i == len(items) - 1
                    else (curses.color_pair(2) if is_sel else curses.color_pair(4))
                )
                put(row, f"  {marker}  {item}", attr | color)
                row += 1
        else:
            put(row, " Custom commit message:", curses.color_pair(3))
            row += 1
            put(row, f" > {edit_buf}_", curses.A_BOLD | curses.color_pair(2))
            row += 1
            put(row, "  Enter to confirm  Esc to cancel", curses.color_pair(3))
            row += 1

        with contextlib.suppress(curses.error):
            stdscr.hline(row, 0, curses.ACS_HLINE, w)
        row += 1

        hint = (
            " type message  Enter confirm  Esc cancel"
            if edit_mode
            else " j/k move  Enter commit  q quit"
        )
        put(min(row, h - 1), hint, curses.color_pair(3))
        stdscr.refresh()

    def _curses_main(stdscr) -> None:
        import curses

        curses.curs_set(0)
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)  # header
        curses.init_pair(2, curses.COLOR_GREEN, -1)  # selected item
        curses.init_pair(3, curses.COLOR_YELLOW, -1)  # hints / custom option
        curses.init_pair(4, curses.COLOR_WHITE, -1)  # normal text

        cursor = 0
        edit_mode = False
        edit_buf = ""

        while True:
            _draw(stdscr, cursor, edit_mode, edit_buf)
            key = stdscr.getch()

            if edit_mode:
                if key in (curses.KEY_ENTER, 10, 13):
                    msg = edit_buf.strip()
                    if msg:
                        state["result_msg"] = msg
                        return
                    edit_mode = False
                elif key == 27:  # Esc
                    edit_mode = False
                    edit_buf = ""
                    with contextlib.suppress(curses.error):
                        curses.curs_set(0)
                elif key in (curses.KEY_BACKSPACE, 127, 8):
                    edit_buf = edit_buf[:-1]
                elif 32 <= key < 127:
                    edit_buf += chr(key)
            else:
                if key in (ord("q"), 27):
                    state["cancelled"] = True
                    return
                elif key in (curses.KEY_UP, ord("k")):
                    cursor = max(0, cursor - 1)
                elif key in (curses.KEY_DOWN, ord("j")):
                    cursor = min(len(items) - 1, cursor + 1)
                elif key in (curses.KEY_ENTER, 10, 13):
                    if cursor == len(items) - 1:
                        edit_mode = True
                        edit_buf = ""
                        with contextlib.suppress(curses.error):
                            curses.curs_set(1)
                    else:
                        state["result_msg"] = items[cursor]
                        return

    try:
        import curses

        curses.wrapper(_curses_main)
    except Exception as exc:  # noqa: BLE001
        log.error("curses error: %s", exc)
        sys.exit(1)

    if state["cancelled"] or state["result_msg"] is None:
        return None
    return state["result_msg"]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="git-quick-commit",
        description=(
            "Interactive commit wizard. Suggests commit messages by analysing "
            "the branch name and staged file paths — no AI, no network."
        ),
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        require("git")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)

    if not is_git_repo():
        log.error("not inside a git repository")
        sys.exit(1)

    branch = current_branch()
    if not branch:
        log.warning("detached HEAD — proceeding without branch-based hints")
        branch = "(detached)"

    staged_files, shortstat = _get_staged_info()
    if not staged_files:
        log.error("nothing staged — run `git add` first")
        sys.exit(1)

    file_info = _classify_staged(staged_files)
    suggestions = generate_suggestions(branch, file_info, staged_files)

    message = _run_commit_ui(branch, staged_files, shortstat, suggestions)

    if not message:
        log.info("cancelled")
        sys.exit(0)

    do_amend = yes_no("Amend last commit?", default=False)

    cmd = ["git", "commit", "-m", message]
    if do_amend:
        cmd.append("--amend")

    log.info("committing: %s%s", message, "  (--amend)" if do_amend else "")
    try:
        run(cmd)
        log.success("committed!")
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        if stderr:
            print(stderr, file=sys.stderr)
        log.error("commit failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
