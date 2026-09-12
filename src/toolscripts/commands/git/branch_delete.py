"""``git-branch-delete`` - interactively delete local/remote git branches.

Opens a curses picker with two sections — **local** branches and
**remote-tracking** branches — annotated with their tracking
relationships: local rows show ``→ upstream`` plus ahead/behind counts,
``[gone]`` markers and merged status; remote rows show ``← tracked-by``.
The two sides of a tracking pair highlight each other as the cursor
moves.

Keys: ``j``/``k`` move · ``Space`` toggle · ``a`` select-all in section ·
``Enter`` delete · ``p`` fetch --prune · ``r`` refresh · ``q`` quit.

This command rolls its own curses loop (like ``npm-tools``) instead of
using ``core.ui_curses.select_many``: it needs a sectioned two-group
layout with per-row tracking annotations and cross-highlighting between
counterparts, which the shared flat pickers don't model.
"""

from __future__ import annotations

import argparse
import contextlib
import sys
from dataclasses import dataclass

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.prompts import yes_no
from toolscripts.core.shell import CommandNotFoundError, require, run
from toolscripts.core.ui_curses import ensure_curses_available, select_many
from toolscripts.git_utils.branches import (
    BranchSnapshot,
    LocalBranch,
    RemoteBranch,
    collect_snapshot,
)
from toolscripts.git_utils.repo import is_git_repo

log = get_logger(__name__)

# color pair ids (initialized in the picker)
_C_CYAN = 1
_C_RED = 2
_C_YELLOW = 3
_C_DEFAULT = 4
_C_GREEN = 5
_C_MAGENTA = 6

_NAME_COL = 36  # max width of the branch-name column


@dataclass
class _Row:
    """One renderable line of the picker."""

    kind: str  # "header" | "local" | "remote"
    label: str = ""  # header text
    key: str | None = None  # selection key: "L:<ref>" / "R:<ref>"
    disabled: bool = False  # checked out somewhere — cannot delete
    link: str | None = None  # counterpart row key (local ↔ remote)
    branch: LocalBranch | RemoteBranch | None = None


def _build_rows(snap: BranchSnapshot) -> list[_Row]:
    rows: list[_Row] = []
    local_for_remote: dict[str, LocalBranch] = {}
    for b in snap.local:
        if b.upstream and b.upstream not in local_for_remote:
            local_for_remote[b.upstream] = b

    if snap.local:
        rows.append(_Row(kind="header", label="LOCAL"))
        for b in snap.local:
            link = f"R:{b.upstream}" if b.upstream in snap.remote_by_ref else None
            rows.append(
                _Row(kind="local", key=f"L:{b.ref}", disabled=bool(b.worktree), link=link, branch=b)
            )
    for remote_name, branches in snap.remote_groups:
        rows.append(_Row(kind="header", label=f"REMOTE {remote_name}"))
        for rb in branches:
            tracker = local_for_remote.get(rb.ref)
            link = f"L:{tracker.ref}" if tracker else None
            rows.append(_Row(kind="remote", key=f"R:{rb.ref}", link=link, branch=rb))
    return rows


def _picker(
    snap: BranchSnapshot, *, force: bool
) -> tuple[list[LocalBranch], list[RemoteBranch]] | None:
    """Show the sectioned multi-select picker.

    Returns ``(local, remote)`` selections, or ``None`` on cancel.
    """
    ensure_curses_available()
    import curses

    def _run(stdscr):  # type: ignore[no-untyped-def]
        return _picker_impl(stdscr, snap, force=force)

    return curses.wrapper(_run)


def _picker_impl(stdscr, snap: BranchSnapshot, *, force: bool):  # type: ignore[no-untyped-def]
    import curses

    with contextlib.suppress(curses.error):
        curses.curs_set(0)
    has_color = False
    with contextlib.suppress(curses.error):
        curses.use_default_colors()
        curses.init_pair(_C_CYAN, curses.COLOR_CYAN, -1)
        curses.init_pair(_C_RED, curses.COLOR_RED, -1)
        curses.init_pair(_C_YELLOW, curses.COLOR_YELLOW, -1)
        curses.init_pair(_C_DEFAULT, -1, -1)
        curses.init_pair(_C_GREEN, curses.COLOR_GREEN, -1)
        curses.init_pair(_C_MAGENTA, curses.COLOR_MAGENTA, -1)
        has_color = True

    def cp(n: int) -> int:
        return curses.color_pair(n) if has_color else 0

    BODY_TOP = 3  # title, hint, divider
    FOOTER_ROWS = 2  # detail line, status line

    snapshot = snap
    rows = _build_rows(snapshot)
    selected: set[str] = set()
    cursor = 0
    top = 0
    message = ""

    def clamp_cursor() -> None:
        nonlocal cursor
        if not rows:
            cursor = 0
            return
        cursor = max(0, min(cursor, len(rows) - 1))
        if rows[cursor].kind == "header":
            for step in (1, -1):
                i = cursor + step
                while 0 <= i < len(rows):
                    if rows[i].kind != "header":
                        cursor = i
                        return
                    i += step

    def move(delta: int) -> None:
        nonlocal cursor
        i = cursor
        while 0 <= i + delta < len(rows):
            i += delta
            if rows[i].kind != "header":
                cursor = i
                return

    def first_row() -> None:
        nonlocal cursor
        cursor = 0
        clamp_cursor()

    def last_row() -> None:
        nonlocal cursor
        cursor = len(rows) - 1
        clamp_cursor()

    def section_bounds(idx: int) -> tuple[int, int]:
        start = idx
        while start > 0 and rows[start - 1].kind != "header":
            start -= 1
        end = idx
        while end + 1 < len(rows) and rows[end + 1].kind != "header":
            end += 1
        return start, end

    def toggle_section() -> None:
        start, end = section_bounds(cursor)
        toggleable = [
            rows[i] for i in range(start, end + 1) if rows[i].key and not rows[i].disabled
        ]
        if not toggleable:
            set_message("nothing selectable in this section")
            return
        all_on = all(r.key in selected for r in toggleable)
        for r in toggleable:
            if all_on:
                selected.discard(r.key)
            else:
                selected.add(r.key)

    def counts() -> tuple[int, int]:
        loc = rem = 0
        for r in rows:
            if r.key and not r.disabled and r.key in selected:
                if r.kind == "local":
                    loc += 1
                else:
                    rem += 1
        return loc, rem

    def set_message(text: str) -> None:
        nonlocal message
        message = text

    def sync_data(fetched: bool) -> None:
        nonlocal snapshot, rows
        if fetched:
            curses.def_prog_mode()
            curses.endwin()
            rc = run(["git", "fetch", "--prune"], check=False).returncode
            with contextlib.suppress(EOFError, KeyboardInterrupt):
                input("\nPress Enter to return to the picker...")
            curses.reset_prog_mode()
            stdscr.keypad(True)
            stdscr.refresh()
            if rc != 0:
                set_message("fetch --prune failed (see output above)")
                return
        try:
            snapshot = collect_snapshot()
            rows = _build_rows(snapshot)
        except Exception as exc:  # noqa: BLE001 — keep the picker alive on refresh errors
            set_message(f"refresh failed: {exc}")
            return
        live = {r.key for r in rows if r.key}
        selected.intersection_update(live)
        clamp_cursor()
        set_message("refreshed" if not fetched else "fetch --prune done")

    def track_label(lb: LocalBranch) -> str:
        if not lb.upstream:
            return "no upstream"
        if lb.gone:
            return "upstream gone"
        if lb.ahead and lb.behind:
            return f"{lb.ahead} ahead, {lb.behind} behind"
        if lb.ahead:
            return f"{lb.ahead} ahead"
        if lb.behind:
            return f"{lb.behind} behind"
        return "in sync"

    def detail_text() -> str:
        if not rows or not 0 <= cursor < len(rows):
            return ""
        r = rows[cursor]
        if r.branch is None:
            return ""
        if r.kind == "local":
            lb: LocalBranch = r.branch
            if lb.name == snapshot.current:
                head = "current branch — switch away before deleting"
            elif lb.worktree:
                head = f"checked out in {lb.worktree} — cannot delete here"
            else:
                flag = "-D" if force else "-d"
                head = f"will run: git branch {flag} {lb.name}"
            bits = [
                head,
                f"{track_label(lb)}" + (f" ({lb.upstream_short})" if lb.upstream else ""),
                "merged (safe -d)" if lb.safe_to_delete else "unmerged (-d refuses)",
                f'{lb.date} "{lb.subject}"',
            ]
        else:
            rb: RemoteBranch = r.branch
            tracker = snapshot.tracked_by(rb.ref)
            bits = [
                f"will run: git push {rb.remote} --delete {rb.name}  (server-side)",
                f"tracked by {tracker.name}" if tracker else "no local branch tracks it",
                "merged into HEAD" if rb.merged_into_head else "not merged into HEAD",
                f'{rb.date} "{rb.subject}"',
            ]
        return " · ".join(bits)

    def row_parts(r: _Row, name_w: int) -> list[tuple[str, int]]:  # type: ignore[type-arg]
        is_sel = bool(r.key and r.key in selected)
        if r.kind == "header":
            return [(f"  {r.label}", curses.A_BOLD | cp(_C_CYAN))]

        dim = curses.A_DIM if r.disabled else 0
        linked = bool(r.link and r.link == rows[cursor].key and r.key != rows[cursor].key)
        name_color = cp(_C_MAGENTA) if linked else (cp(_C_GREEN) if is_sel else cp(_C_DEFAULT))
        base = curses.A_REVERSE if r.key == rows[cursor].key else 0
        parts: list[tuple[str, int]] = []

        mark = "[x]" if is_sel else ("[-]" if r.disabled else "[ ]")
        parts.append((f"  {mark} ", base | dim))
        if r.kind == "local":
            lb: LocalBranch = r.branch
            name = lb.name + (" *" if lb.name == snapshot.current else "")
            parts.append((name, base | dim | name_color | (curses.A_BOLD if linked else 0)))
            parts.append((" " * max(1, name_w - len(name) + 2), 0))
            if lb.worktree and lb.name != snapshot.current:
                parts.append(("(worktree) ", dim))
            if lb.upstream:
                parts.append((f"→ {lb.upstream_short} ", cp(_C_CYAN)))
                if lb.gone:
                    parts.append(("[gone]", cp(_C_RED)))
                elif lb.ahead or lb.behind:
                    counts_txt = (f"↑{lb.ahead}" if lb.ahead else "") + (
                        f"↓{lb.behind}" if lb.behind else ""
                    )
                    parts.append((counts_txt, cp(_C_YELLOW)))
                if lb.safe_to_delete:
                    parts.append(("  (merged)", cp(_C_GREEN)))
            else:
                parts.append(("(no upstream)", dim))
        else:
            rb: RemoteBranch = r.branch
            parts.append((rb.short, base | dim | name_color | (curses.A_BOLD if linked else 0)))
            parts.append((" " * max(1, name_w - len(rb.short) + 2), 0))
            tracker = snapshot.tracked_by(rb.ref)
            if tracker:
                parts.append((f"← {tracker.name}", cp(_C_CYAN)))
            else:
                parts.append(("(no local)", dim))
            if rb.merged_into_head:
                parts.append(("  (merged)", cp(_C_GREEN)))
        return parts

    def draw() -> None:
        nonlocal top
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        title = f" git branches — {snapshot.repo_name}"
        if not snapshot.current and snapshot.local:
            title += "  (detached HEAD)"
        with contextlib.suppress(curses.error):
            stdscr.addstr(0, 0, title[: width - 1], curses.A_BOLD)
        hint = "j/k move · Space toggle · a all in section · Enter delete · p fetch --prune · r refresh · q quit"
        with contextlib.suppress(curses.error):
            stdscr.addstr(1, 0, hint[: width - 1], cp(_C_YELLOW))
        with contextlib.suppress(curses.error):
            stdscr.hline(2, 0, curses.ACS_HLINE, width)

        list_h = max(1, height - BODY_TOP - FOOTER_ROWS)
        if cursor < top:
            top = cursor
        elif cursor >= top + list_h:
            top = cursor - list_h + 1

        name_w = min(
            _NAME_COL,
            max(
                (
                    len(r.branch.name if r.kind == "local" else r.branch.short)
                    for r in rows
                    if r.branch
                ),
                default=0,
            ),
        )

        # per-section selected/total counts, keyed by header row index
        stats: dict[int, list[int]] = {}
        current_header: int | None = None
        for i, r in enumerate(rows):
            if r.kind == "header":
                current_header = i
                stats[i] = [0, 0]
            elif current_header is not None:
                if not r.disabled:
                    stats[current_header][1] += 1
                if r.key and r.key in selected:
                    stats[current_header][0] += 1

        for vis, idx in enumerate(range(top, min(top + list_h, len(rows)))):
            r = rows[idx]
            y = BODY_TOP + vis
            if r.kind == "header":
                sel, tot = stats.get(idx, (0, 0))
                text = f"  {r.label}" + (f"  ({sel}/{tot} selected)" if tot else "  (none)")
                with contextlib.suppress(curses.error):
                    stdscr.addstr(y, 0, text[: width - 1], curses.A_BOLD | cp(_C_CYAN))
                continue
            x = 0
            for text, attr in row_parts(r, name_w):
                if x >= width - 1:
                    break
                with contextlib.suppress(curses.error):
                    stdscr.addstr(y, x, text[: width - 1 - x], attr)
                x += len(text)

        with contextlib.suppress(curses.error):
            stdscr.addstr(height - 2, 0, detail_text()[: width - 1], cp(_C_CYAN))
        if message:
            status = f" {message}"
        else:
            loc, rem = counts()
            status = f" {loc} local + {rem} remote selected — Enter to delete"
        with contextlib.suppress(curses.error):
            stdscr.addstr(height - 1, 0, status[: width - 1], cp(_C_YELLOW))

        stdscr.refresh()

    def collect() -> tuple[list[LocalBranch], list[RemoteBranch]]:
        locs: list[LocalBranch] = []
        rems: list[RemoteBranch] = []
        for r in rows:
            if r.key and not r.disabled and r.key in selected and r.branch is not None:
                if r.kind == "local":
                    locs.append(r.branch)
                else:
                    rems.append(r.branch)
        return locs, rems

    clamp_cursor()
    while True:
        draw()
        key = stdscr.getch()
        message = ""

        if key in (curses.KEY_UP, ord("k")):
            move(-1)
        elif key in (curses.KEY_DOWN, ord("j")):
            move(1)
        elif key == curses.KEY_PPAGE:
            cursor = max(0, cursor - max(1, curses.LINES - BODY_TOP - FOOTER_ROWS))
            clamp_cursor()
        elif key == curses.KEY_NPAGE:
            cursor = min(len(rows) - 1, cursor + max(1, curses.LINES - BODY_TOP - FOOTER_ROWS))
            clamp_cursor()
        elif key == ord("g"):
            if stdscr.getch() == ord("g"):
                first_row()
        elif key == ord("G"):
            last_row()
        elif key == ord(" "):
            r = rows[cursor]
            if r.kind == "header":
                pass
            elif r.disabled:
                if r.kind == "local" and r.branch.name == snapshot.current:
                    set_message("cannot delete the current branch")
                else:
                    set_message("branch is checked out in a worktree — switch away first")
            else:
                assert r.key is not None
                if r.key in selected:
                    selected.discard(r.key)
                else:
                    selected.add(r.key)
        elif key == ord("a"):
            toggle_section()
        elif key in (curses.KEY_ENTER, 10, 13):
            loc, rem = counts()
            if not loc and not rem:
                set_message("nothing selected — press Space to select rows")
            else:
                return collect()
        elif key == ord("p"):
            sync_data(fetched=True)
        elif key == ord("r"):
            sync_data(fetched=False)
        elif key in (ord("q"), 27):
            return None
        # anything else (KEY_RESIZE, unknown keys): just redraw


def _execute(
    locals_: list[LocalBranch],
    remotes_: list[RemoteBranch],
    *,
    force: bool,
    assume_yes: bool,
) -> None:
    local_flag = "-D" if force else "-d"
    print("Will delete:")
    if locals_:
        print(f"  local  (git branch {local_flag}):")
        for b in locals_:
            print(f"    {b.name}")
    if remotes_:
        print("  remote (git push <remote> --delete):")
        for rb in remotes_:
            print(f"    {rb.short}")

    if not assume_yes and not yes_no("\nProceed with deletion?", default=False):
        log.warning("deletion cancelled")
        return

    failed_local: list[LocalBranch] = []
    for b in locals_:
        rc = run(["git", "branch", local_flag, b.name], check=False).returncode
        if rc == 0:
            log.success("deleted local branch %s", b.name)
        else:
            log.error("failed to delete local branch %s (see git output above)", b.name)
            failed_local.append(b)

    if failed_local and not force:
        log.warning("%d local branch(es) have unmerged commits", len(failed_local))
        names = [b.name for b in failed_local]
        pick = select_many("Select branches to FORCE delete (git branch -D):", names)
        for i in pick or []:
            rc = run(["git", "branch", "-D", names[i]], check=False).returncode
            if rc == 0:
                log.success("force deleted %s", names[i])
            else:
                log.error("failed to force delete %s (see git output above)", names[i])

    for rb in remotes_:
        rc = run(["git", "push", rb.remote, "--delete", rb.name], check=False).returncode
        if rc == 0:
            log.success("deleted remote branch %s", rb.short)
        else:
            log.error("failed to delete remote branch %s (see git output above)", rb.short)

    log.info(
        "finished: %d local + %d remote branch(es) processed",
        len(locals_),
        len(remotes_),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="git-branch-delete",
        description=(
            "Interactively delete local and remote git branches. "
            "Opens a curses picker with a LOCAL and a REMOTE section, shows "
            "tracking relationships (upstream, ahead/behind, gone, merged), "
            "and deletes what you select."
        ),
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="use git branch -D (delete unmerged local branches)",
    )
    parser.add_argument("-y", "--yes", action="store_true", help="skip the final confirmation")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        require("git")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)

    if not is_git_repo():
        log.error("not a git repository (or any of the parent directories)")
        sys.exit(1)

    snap = collect_snapshot()
    if not snap.local and not snap.remote_groups:
        log.info("no branches found — nothing to delete")
        return

    chosen = _picker(snap, force=args.force)
    if chosen is None:
        log.info("cancelled — nothing deleted")
        return
    locals_, remotes_ = chosen
    if not locals_ and not remotes_:
        log.info("nothing selected")
        return
    _execute(locals_, remotes_, force=args.force, assume_yes=args.yes)


if __name__ == "__main__":
    main()
