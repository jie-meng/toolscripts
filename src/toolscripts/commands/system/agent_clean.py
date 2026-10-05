"""``agent-clean`` - detect installed CLI agents and clean up their sessions.

Scans the per-tool data directories registered in ``agent_clean_profiles``,
measures each cleanable part, then lets the user pick parts to delete through
the shared curses picker (``select_many_help``). Sessions are disposable;
logs and package caches are offered too, since they are often the real space
hogs.

Scope is command-line agents only. GUI/IDE agents (Qoder, ZCode, WorkBuddy,
DeepSeek Harness, ...) are not covered: their chats live in app-internal
databases behind the app sidebar and must be cleaned from inside the app.

User-supplied part overrides live in
``~/.config/toolscripts/agent-clean.json`` so tool-version drift can be
patched without touching code. Run ``agent-clean --help`` for the non-
interactive ``--list`` / ``--del`` modes.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.prompts import yes_no
from toolscripts.core.size import human_size, path_size
from toolscripts.core.ui_curses import select_many_help

from .agent_clean_profiles import CleanPart, ToolProfile, load_profiles, resolve_part_paths

log = get_logger(__name__)


@dataclass
class PartRow:
    """A resolvable cleanable part belonging to one detected tool."""

    tool_id: str
    tool_name: str
    part: CleanPart
    paths: list[Path]
    size: int


def build_rows(profiles: list[ToolProfile]) -> list[PartRow]:
    """Expand every profile into rows; rows without existing paths are dropped."""

    rows: list[PartRow] = []
    for prof in profiles:
        tool_rows: list[PartRow] = []
        for part in prof.parts:
            paths = resolve_part_paths(part)
            if not paths:
                continue
            size = sum(path_size(p) for p in paths)
            tool_rows.append(PartRow(prof.tool_id, prof.name, part, paths, size))
        tool_rows.sort(key=lambda r: r.size, reverse=True)
        rows.extend(tool_rows)
    return rows


def select_matching_rows(rows: list[PartRow], specs: list[str]) -> list[PartRow] | None:
    """Resolve ``--del TOOL[:PART]`` specs against rows; ``None`` when a spec is unknown.

    ``TOOL`` selects that tool's *default* parts, ``TOOL:PART`` a specific part
    (default or not), and ``all`` every default part across all tools.
    """

    picked: list[PartRow] = []
    seen: set[tuple[str, str]] = set()
    for spec in specs:
        if spec == "all":
            matches = [r for r in rows if r.part.default]
        else:
            tool_id, sep, key = spec.partition(":")
            matches = [r for r in rows if r.tool_id == tool_id and (not sep or r.part.key == key)]
            if sep:
                matches = [r for r in matches if r.part.key == key]
            else:
                matches = [r for r in matches if r.part.default]
        if not matches:
            if spec != "all":
                log.error("no such tool or part: %s (run `agent-clean --list` for the ids)", spec)
                return None
            continue
        for r in matches:
            if (r.tool_id, r.part.key) not in seen:
                seen.add((r.tool_id, r.part.key))
                picked.append(r)
    return picked


def _print_rows(rows: list[PartRow]) -> None:
    current: str | None = None
    total = 0
    for r in rows:
        if r.tool_name != current:
            print(r.tool_name)
            current = r.tool_name
        marker = "[x]" if r.part.default else "[ ]"
        print(f"  {marker} {r.part.key:<20} {human_size(r.size):>8}  {r.part.label}")
        if r.part.note:
            print(f"         {r.part.note}")
        total += r.size
    print(f"\ntotal cleanable: {human_size(total)}  ({len(rows)} part(s))")


def _remove_paths(paths: list[Path]) -> int:
    """Delete every path; return the bytes actually freed."""

    freed = 0
    for path in paths:
        size = path_size(path)
        try:
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()
        except OSError as exc:
            log.warning("could not remove %s: %s", path, exc)
            continue
        freed += size
    return freed


def _delete(selected: list[PartRow], *, dry_run: bool, yes: bool = False) -> None:
    total = sum(r.size for r in selected)
    print("Will delete:")
    for r in selected:
        print(f"  {r.tool_name} · {r.part.label}  {human_size(r.size)}  {r.part.note}")
    print(f"total: {human_size(total)} ({len(selected)} part(s))")
    if dry_run:
        log.info("dry-run — nothing deleted")
        return
    if not yes and not yes_no(
        f"Really delete these {len(selected)} items, freeing ~{human_size(total)}?", default=False
    ):
        log.info("aborted")
        return
    freed = 0
    for r in selected:
        freed += _remove_paths(r.paths)
    log.success("freed ~%s", human_size(freed))


def _interactive(rows: list[PartRow], *, dry_run: bool) -> None:
    if not rows:
        log.info("no installed CLI agent data found (GUI agents are out of scope)")
        return

    items = [f"{r.tool_name} · {r.part.label}  {human_size(r.size)}" for r in rows]
    helps = [r.part.note or ", ".join(str(p) for p in r.paths[:2]) for r in rows]
    preselected = [r.part.default for r in rows]

    indices = select_many_help(
        "Select parts to DELETE (j/k move, Space toggle, a all/none, Enter confirm, q cancel)",
        items,
        helps,
        preselected=preselected,
    )
    if indices is None:
        log.info("cancelled")
        return
    selected = [rows[i] for i in indices]
    if not selected:
        log.info("nothing selected — exiting")
        return
    _delete(selected, dry_run=dry_run)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agent-clean",
        description=(
            "Detect installed CLI agent tools, show how much space their sessions, "
            "logs and caches take, and delete the parts you pick."
        ),
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="list detected tools and parts with sizes, then exit",
    )
    parser.add_argument(
        "--del",
        dest="delete",
        action="append",
        metavar="TOOL[:PART]",
        help=(
            "delete non-interactively; TOOL uses its default parts, TOOL:PART a specific "
            "one (repeatable; combine with --yes / --dry-run)"
        ),
    )
    parser.add_argument("-y", "--yes", action="store_true", help="skip the confirmation prompt")
    parser.add_argument(
        "--dry-run", action="store_true", help="show what would be deleted, delete nothing"
    )
    parser.add_argument(
        "--config",
        metavar="FILE",
        help="override file for tool/part definitions (default: ~/.config/toolscripts/agent-clean.json)",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    profiles = load_profiles(Path(args.config) if args.config else None)
    rows = build_rows(profiles)

    if args.list:
        _print_rows(rows)
        return

    if args.delete:
        selected = select_matching_rows(rows, args.delete)
        if selected is None:
            sys.exit(1)
        if not selected:
            log.info("nothing selected to delete")
            return
        _delete(selected, dry_run=args.dry_run, yes=args.yes)
        return

    _interactive(rows, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
