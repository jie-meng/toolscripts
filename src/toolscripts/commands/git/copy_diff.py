"""``git-copy-diff`` - copy various git diffs to the clipboard, optionally with an AI review prompt."""

from __future__ import annotations

import argparse
import re
import subprocess
from urllib.parse import urlparse

from toolscripts.core.clipboard import copy_to_clipboard
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.ui_curses import select_one

log = get_logger(__name__)


def _run(cmd: list[str]) -> str | None:
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _current_branch() -> str:
    out = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    return (out or "").strip()


def _commit_format() -> str | None:
    branch = _current_branch()
    if not branch or branch.count("/") < 1:
        return None
    parts = branch.split("/", 2)
    return f"{parts[0]}[{parts[1]}] <message>"


def _recent_commits(n: int = 50, offset: int = 0) -> list[tuple[str, str]]:
    cmd = ["git", "log", "--oneline", "-n", str(n + offset), "--skip", str(offset)]
    out = _run(cmd)
    if not out:
        return []
    lines = out.strip().splitlines()[offset:]
    commits: list[tuple[str, str]] = []
    for line in lines:
        if not line:
            continue
        parts = line.split(" ", 1)
        commits.append((parts[0], parts[1] if len(parts) == 2 else ""))
    return commits[:n]


_PAGE_SIZE = 20


def _pick_commits_paginated(max_count: int) -> list[tuple[str, str]] | None:
    """Curses paginated multi-select for commits. Returns selected commits or None on cancel."""
    import contextlib
    import curses

    commits: list[tuple[str, str]] = []
    fetch_offset = 0
    page_offset = 0
    selected: set[int] = set()
    cursor = 0
    top = 0
    sel_scroll = 0
    loading = False
    has_more = True

    def _load_page() -> None:
        nonlocal loading, has_more, fetch_offset
        if loading or not has_more:
            return
        loading = True
        page = _recent_commits(_PAGE_SIZE, fetch_offset)
        loading = False
        if not page:
            has_more = False
            return
        commits.extend(page)
        fetch_offset += _PAGE_SIZE
        if len(page) < _PAGE_SIZE:
            has_more = False

    def _page_commits() -> list[tuple[str, str]]:
        return commits[page_offset : page_offset + _PAGE_SIZE]

    def _draw(stdscr: curses.window) -> None:
        nonlocal top, sel_scroll
        stdscr.clear()
        stdscr.addstr(0, 0, "Select commits", curses.A_BOLD)
        hint = "j/k move | [/] prev/next page | Space toggle | a all/none | Enter confirm | q quit"
        stdscr.addstr(1, 0, hint, curses.color_pair(3))

        height, width = stdscr.getmaxyx()
        body_row = 3
        page_items = _page_commits()
        total_items = len(page_items)
        list_h = min(_PAGE_SIZE, height - body_row - 3)

        if cursor < top:
            top = cursor
        elif cursor >= top + list_h:
            top = cursor - list_h + 1

        visible = range(top, min(top + list_h, total_items))
        row = body_row
        for idx in visible:
            h, m = page_items[idx]
            abs_idx = page_offset + idx
            marker = "[x]" if abs_idx in selected else "[ ]"
            attr = curses.A_REVERSE if cursor == idx else 0
            color = curses.color_pair(5) if abs_idx in selected else curses.color_pair(4)
            with contextlib.suppress(curses.error):
                text = f"  {marker}  {h} {m}"[: width - 1]
                stdscr.addstr(row, 0, text, attr | color)
            row += 1

        sep_row = body_row + list_h
        with contextlib.suppress(curses.error):
            stdscr.addstr(sep_row, 0, " " + "-" * min(width - 2, 60), curses.color_pair(3))

        sel_start = sep_row + 1
        sel_area_h = height - sel_start - 2
        if sel_area_h > 0 and selected:
            with contextlib.suppress(curses.error):
                stdscr.addstr(sel_start, 0, "  Selected:", curses.A_BOLD | curses.color_pair(5))
            sel_list = sorted(selected)
            if sel_scroll >= len(sel_list):
                sel_scroll = max(0, len(sel_list) - sel_area_h + 1)
            vis_sel = sel_list[sel_scroll : sel_scroll + sel_area_h - 1]
            for i, idx in enumerate(vis_sel):
                h, m = commits[idx]
                with contextlib.suppress(curses.error):
                    text = f"    {i + sel_scroll + 1:2}. {h} {m}"[: width - 1]
                    stdscr.addstr(sel_start + 1 + i, 0, text, curses.color_pair(5))

        count = len(selected)
        page_num = page_offset // _PAGE_SIZE + 1
        status = f"  {count} selected | page {page_num} | {len(commits)} loaded"
        if loading:
            status += " | loading..."
        with contextlib.suppress(curses.error):
            stdscr.addstr(height - 1, 0, status, curses.color_pair(3))
        stdscr.refresh()

    def _run(stdscr: curses.window) -> list[tuple[str, str]] | None:
        nonlocal cursor, top, sel_scroll, page_offset, selected

        curses.curs_set(0)
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_RED, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.init_pair(4, curses.COLOR_WHITE, -1)
        curses.init_pair(5, curses.COLOR_GREEN, -1)

        _load_page()
        if not commits:
            return None

        while True:
            _draw(stdscr)
            key = stdscr.getch()

            page_items = _page_commits()
            total_items = len(page_items)

            if key == curses.KEY_UP or key == ord("k"):
                cursor = max(0, cursor - 1)
            elif key == curses.KEY_DOWN or key == ord("j"):
                cursor = min(total_items - 1, cursor + 1)
            elif key == ord("g"):
                key2 = stdscr.getch()
                if key2 == ord("g"):
                    cursor = 0
            elif key == ord("G"):
                cursor = total_items - 1
            elif key == ord("]"):
                if has_more and not loading:
                    _load_page()
                    page_offset += _PAGE_SIZE
                    cursor = 0
                    top = 0
            elif key == ord("["):
                if page_offset >= _PAGE_SIZE:
                    page_offset -= _PAGE_SIZE
                    cursor = 0
                    top = 0
            elif key == ord(" "):
                if cursor < len(page_items):
                    abs_idx = page_offset + cursor
                    if abs_idx in selected:
                        selected.discard(abs_idx)
                    else:
                        selected.add(abs_idx)
                    sel_scroll = max(0, len(selected) - 1)
            elif key == ord("a"):
                page_abs = {page_offset + i for i in range(len(page_items))}
                if selected & page_abs == page_abs:
                    selected -= page_abs
                else:
                    selected |= page_abs
                sel_scroll = max(0, len(selected) - 1)
            elif key in (curses.KEY_ENTER, 10, 13) or key == ord("o"):
                return [commits[i] for i in sorted(selected)]
            elif key in (ord("q"), 27):
                return None

    return curses.wrapper(_run)


def _staged_diff() -> tuple[str | None, dict[str, str]]:
    return (
        _run(["git", "diff", "--cached"]),
        {"success_msg": "Staged diff copied to clipboard.", "empty_msg": "No staged diff to copy."},
    )


def _working_diff() -> tuple[str | None, dict[str, str]]:
    return (
        _run(["git", "diff"]),
        {
            "success_msg": "Working directory diff copied to clipboard.",
            "empty_msg": "No diff to copy.",
        },
    )


def _single_commit_diff(count: int = 50) -> tuple[str | None, dict[str, str]]:
    commits = _pick_commits_paginated(count)
    if not commits:
        return None, {}
    h = commits[0][0]
    diff = _run(["git", "show", h])
    return diff, {
        "success_msg": f"Diff of commit {h} copied to clipboard.",
        "empty_msg": "No diff to copy.",
    }


def _multi_commit_diff(count: int = 50) -> tuple[str | None, dict[str, str]]:
    commits = _pick_commits_paginated(count)
    if not commits:
        return None, {}
    hashes = [h for h, _ in commits]

    mode_items = ["Combined (like PR diff)", "Separate (each commit individually)"]
    mode = select_one("How to view the diff?", mode_items, default_index=0)
    if mode is None:
        return None, {}

    if mode == 0:
        newest = hashes[0]
        oldest = hashes[-1]
        parent_out = _run(["git", "rev-parse", f"{oldest}^"])
        if parent_out:
            base = parent_out.strip()
            diff = _run(["git", "diff", f"{base}..{newest}"])
        else:
            diff = ""
            for h in hashes:
                d = _run(["git", "show", h])
                if d and d.strip():
                    diff = (diff + "\n\n" + d).strip()
    else:
        diff = ""
        for h in hashes:
            d = _run(["git", "show", h])
            if d and d.strip():
                diff = (diff + "\n\n" + d).strip()

    if not diff or not diff.strip():
        return None, {"empty_msg": "No diff to copy."}
    labels = " ".join(hashes)
    return diff, {"success_msg": f"Diff of {labels} copied to clipboard."}


def _parse_pr(value: str) -> tuple[str | None, str | None, str, str | None]:
    value = value.strip()
    if re.match(r"^\d+$", value):
        return None, value, value, None
    m = re.match(r"^([^/\s]+/[^#\s]+)#(\d+)$", value)
    if m:
        return m.group(1), m.group(2), value, None
    try:
        parsed = urlparse(value)
        if parsed.scheme and parsed.netloc:
            host = parsed.netloc.split(":", 1)[0]
            parts = [p for p in parsed.path.split("/") if p]
            if len(parts) >= 4 and parts[-2] in ("pull", "pulls"):
                owner, repo_name = parts[0], parts[1]
                number = parts[3] if parts[2] in ("pull", "pulls") else parts[-1]
                if re.match(r"^\d+$", number):
                    return f"{owner}/{repo_name}", number, value, host
            for part in reversed(parts):
                if re.match(r"^\d+$", part):
                    repo = f"{parts[0]}/{parts[1]}" if len(parts) >= 2 else None
                    return repo, part, value, host
    except (ValueError, AttributeError):
        pass
    return None, None, value, None


def _pr_diff() -> tuple[str | None, dict[str, str]]:
    raw = input("Enter PR URL, number (e.g. 123) or owner/repo#number: ")
    if not raw.strip():
        return None, {"empty_msg": "No PR provided."}
    repo, number, original, host = _parse_pr(raw)

    if host and host.lower() not in ("github.com", "api.github.com"):
        cmd = ["gh", "pr", "diff", original]
    elif repo and number:
        cmd = ["gh", "pr", "diff", number, "--repo", repo]
    elif number:
        cmd = ["gh", "pr", "diff", number]
    else:
        cmd = ["gh", "pr", "diff", original]

    log.info("running: %s", " ".join(cmd))
    return _run(cmd), {
        "success_msg": "PR diff copied to clipboard.",
        "empty_msg": "No diff to copy.",
    }


def _branch_diff() -> tuple[str | None, dict[str, str]]:
    current = _current_branch()
    if not current:
        return None, {"empty_msg": "Could not determine the current branch."}
    candidates = [
        "origin/main",
        "origin/master",
        "origin/develop",
        "origin/dev",
        "main",
        "master",
        "develop",
        "dev",
    ]
    auto = next(
        (c for c in candidates if _run(["git", "rev-parse", "--verify", c]) is not None), None
    )
    if auto:
        user = input(
            f"Automatically selected '{auto}' as the base. "
            "Press Enter to confirm, or enter a different branch/commit hash: "
        ).strip()
        base = user or auto
    else:
        user = input(
            "Could not automatically find a base branch. Enter a base branch or commit hash: "
        ).strip()
        if not user:
            return None, {"empty_msg": "No base branch provided. Aborting."}
        base = user

    log.info("running: git diff %s...%s", base, current)
    diff = _run(["git", "diff", f"{base}...{current}"])
    return diff, {
        "success_msg": f"Diff of branch '{current}' from base '{base}' copied to clipboard.",
        "empty_msg": "No diff to copy.",
        "current_branch": current,
    }


_PROMPT_EN = (
    "As a professional code reviewer, please analyze the above git diff and output your review in clear, "
    "structured English Markdown. Strictly follow this format:\n\n"
    "1. **Problematic Code & Explanation**\n"
    "   - List all code snippets with potential issues (bugs, design flaws, maintainability, performance, etc.), "
    "and clearly explain the reason and impact for each.\n\n"
    "2. **Improvement Suggestions**\n"
    "   - For each issue, provide concrete suggestions for improvement or fixes.\n\n"
    "3. **Overall Assessment**\n"
    "   - Summarize the strengths and risks of this change, and highlight anything that needs special attention.\n\n"
    "4. **Recommended Commit Message**\n"
    "{commit_msg_instruction}\n\n"
    "Format your output in clean Markdown for easy copy-paste into review tools or commit descriptions."
)

_PROMPT_ZH = (
    "作为一名专业的代码审查员，请分析上述 git diff 并以清晰、结构化的中文 Markdown 格式输出您的审查意见。请严格遵循以下格式：\n\n"
    "1. **问题代码及说明**\n"
    "   - 列出所有存在潜在问题的代码片段（bug、设计缺陷、可维护性、性能等），并清楚说明每个问题的原因和影响。\n\n"
    "2. **改进建议**\n"
    "   - 针对每个问题，提供具体的改进或修复建议。\n\n"
    "3. **整体评估**\n"
    "   - 总结此次变更的优势和风险，并突出需要特别关注的地方。\n\n"
    "4. **推荐提交信息**\n"
    "{commit_msg_instruction}\n\n"
    "请以清晰的 Markdown 格式输出，便于复制粘贴到审查工具或提交描述中。"
)


def _ask_prompt_type() -> str | None:
    items = ["No", "En (English)", "Zh (中文)"]
    sel = select_one("Include review prompt?", items, default_index=0)
    if sel is None:
        return "back"
    return [None, "en", "zh-cn"][sel]


def _format_and_copy(diff: str, prompt_type: str | None, info: dict[str, str]) -> None:
    payload = "```\n" + diff + "```\n"
    if prompt_type:
        current = info.get("current_branch") or _current_branch()
        fmt = _commit_format()
        if prompt_type == "en":
            commit_instr = "   - Generate a concise, accurate, and conventional commit message for this change."
            if fmt:
                commit_instr = (
                    "   - Generate a concise, accurate commit message for this change. "
                    f"Based on the branch name '{current}', use the format: '{fmt}'."
                )
            payload += "\n\n" + _PROMPT_EN.format(commit_msg_instruction=commit_instr)
        elif prompt_type == "zh-cn":
            commit_instr = "   - 为此变更生成简洁、准确且符合规范的提交信息，提交信息使用英文。"
            if fmt:
                commit_instr = (
                    "   - 为此变更生成简洁、准确且符合规范的提交信息。"
                    f"基于分支名 '{current}'，使用格式: '{fmt}'。提交信息使用英文。"
                )
            payload += "\n\n" + _PROMPT_ZH.format(commit_msg_instruction=commit_instr)

    if copy_to_clipboard(payload):
        log.success(info.get("success_msg", "Diff copied to clipboard."))
    else:
        log.warning("could not copy to clipboard")


def _review_prompt_only() -> None:
    items = ["English (en)", "中文 (zh-cn)"]
    sel = select_one("Select review prompt language", items)
    if sel is None:
        return
    if sel == 0:
        text = _PROMPT_EN.format(
            commit_msg_instruction="   - Generate a concise, accurate, and conventional commit message."
        )
        copy_to_clipboard(text)
        log.success("English review prompt copied to clipboard.")
    elif sel == 1:
        text = _PROMPT_ZH.format(
            commit_msg_instruction="   - 为此变更生成简洁、准确且符合规范的提交信息，提交信息使用英文。"
        )
        copy_to_clipboard(text)
        log.success("中文审查提示已复制到剪贴板。")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="git-copy-diff",
        description="Interactively copy git diffs (staged, working, commit, branch, PR) to clipboard.",
    )
    parser.add_argument(
        "-n",
        "--count",
        type=int,
        default=50,
        help="number of recent commits to list for commit selection (default: 50)",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    options = [
        "Staged diff (git diff --cached)",
        "Working directory diff (git diff)",
        "Diff of a specific commit",
        "Diffs of multiple commits",
        "Branch diff from merge-base (e.g. vs main/master)",
        "PR diff (gh pr diff)",
        "Generate review prompt for clipboard",
    ]
    handlers = {
        0: _staged_diff,
        1: _working_diff,
        2: _single_commit_diff,
        3: _multi_commit_diff,
        4: _branch_diff,
        5: _pr_diff,
    }

    while True:
        sel = select_one("Select the diff type to copy", options)
        if sel is None:
            return
        if sel == 6:
            _review_prompt_only()
            continue

        if sel in (2, 3):
            diff, info = handlers[sel](args.count)
        else:
            diff, info = handlers[sel]()
        if diff is None or not diff.strip():
            log.info(info.get("empty_msg", "No diff to copy."))
            return

        prompt_type = _ask_prompt_type()
        if prompt_type == "back":
            continue

        _format_and_copy(diff, prompt_type, info)
        return


if __name__ == "__main__":
    main()
