"""``git-copy-diff`` - copy various git diffs to the clipboard, optionally with an AI review prompt."""

from __future__ import annotations

import argparse
import re
import subprocess
from urllib.parse import urlparse

from toolscripts.core.clipboard import copy_to_clipboard
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)


def _run(cmd: list[str]) -> str | None:
    try:
        result = subprocess.run(
            cmd, check=True, capture_output=True, text=True
        )
        return result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _select_from_list(options: list[str], prompt: str = "Please select: ") -> int:
    for idx, opt in enumerate(options):
        print(f"{idx}. {opt}")
    while True:
        try:
            value = int(input(prompt))
            if 0 <= value < len(options):
                return value
        except ValueError:
            pass
        print("Invalid input, please try again.")


def _print_menu(options: list[str]) -> None:
    print()
    for idx, opt in enumerate(options, 1):
        print(f"{idx}. {opt}")
    print()
    print("0. Exit")


def _menu_select(num: int) -> int:
    while True:
        try:
            value = int(input("Please select: "))
            if 0 <= value <= num:
                return value
        except ValueError:
            pass
        print("Invalid input, please try again.")


def _current_branch() -> str:
    out = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    return (out or "").strip()


def _commit_format() -> str | None:
    branch = _current_branch()
    if not branch or branch.count("/") < 1:
        return None
    parts = branch.split("/", 2)
    return f"{parts[0]}[{parts[1]}] <message>"


def _recent_commits(n: int = 20) -> list[tuple[str, str]]:
    out = _run(["git", "log", "--oneline", "-n", str(n)])
    if not out:
        return []
    commits: list[tuple[str, str]] = []
    for line in out.strip().splitlines():
        if not line:
            continue
        parts = line.split(" ", 1)
        commits.append((parts[0], parts[1] if len(parts) == 2 else ""))
    return commits


def _staged_diff() -> tuple[str | None, dict[str, str]]:
    return (
        _run(["git", "diff", "--cached"]),
        {"success_msg": "Staged diff copied to clipboard.", "empty_msg": "No staged diff to copy."},
    )


def _working_diff() -> tuple[str | None, dict[str, str]]:
    return (
        _run(["git", "diff"]),
        {"success_msg": "Working directory diff copied to clipboard.", "empty_msg": "No diff to copy."},
    )


def _single_commit_diff() -> tuple[str | None, dict[str, str]]:
    while True:
        commits = _recent_commits()
        if not commits:
            return None, {"empty_msg": "No recent commits found."}
        opts = ["Back to previous menu"] + [f"{h} {m}" for h, m in commits]
        sel = _select_from_list(opts, prompt="Select a commit: ")
        if sel == 0:
            return None, {}
        h = commits[sel - 1][0]
        diff = _run(["git", "show", h])
        return diff, {
            "success_msg": f"Diff of commit {h} copied to clipboard.",
            "empty_msg": "No diff to copy.",
        }


def _multi_commit_diff() -> tuple[str | None, dict[str, str]]:
    raw = input("Enter commit hashes (comma separated): ")
    hashes = [h.strip() for h in raw.split(",") if h.strip()]
    if not hashes:
        return None, {"empty_msg": "No valid commit hashes entered."}
    chunks: list[str] = []
    for h in hashes:
        d = _run(["git", "show", h])
        if d and d.strip():
            chunks.append(d)
        else:
            log.warning("could not get diff for commit %s", h)
    if not chunks:
        return None, {"empty_msg": "No diffs could be generated."}
    return "\n\n".join(chunks), {"success_msg": "Combined diffs copied to clipboard."}


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
        "origin/main", "origin/master", "origin/develop", "origin/dev",
        "main", "master", "develop", "dev",
    ]
    auto = next((c for c in candidates if _run(["git", "rev-parse", "--verify", c]) is not None), None)
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
    print("\nDo you want to include a review prompt?")
    print("1. No")
    print("2. En (English)")
    print("3. Zh (中文)")
    print("0. Back to main menu")
    while True:
        raw = input("Please select (default: 1): ").strip()
        if not raw:
            return None
        try:
            value = int(raw)
        except ValueError:
            print("Please enter a number.")
            continue
        if value == 0:
            return "back"
        if value == 1:
            return None
        if value == 2:
            return "en"
        if value == 3:
            return "zh-cn"
        print("Invalid input, please try again.")


def _format_and_copy(diff: str, prompt_type: str | None, info: dict[str, str]) -> None:
    payload = "```\n" + diff + "```\n"
    if prompt_type:
        current = info.get("current_branch") or _current_branch()
        fmt = _commit_format()
        if prompt_type == "en":
            commit_instr = (
                "   - Generate a concise, accurate, and conventional commit message for this change."
            )
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
    options = ["English (en)", "中文 (zh-cn)"]
    print("\nSelect review prompt language:")
    for idx, opt in enumerate(options, 1):
        print(f"{idx}. {opt}")
    print("0. Exit")
    while True:
        try:
            value = int(input("Please select: "))
        except ValueError:
            print("Please enter a number.")
            continue
        if value == 0:
            return
        if value == 1:
            text = _PROMPT_EN.format(
                commit_msg_instruction="   - Generate a concise, accurate, and conventional commit message."
            )
            copy_to_clipboard(text)
            log.success("English review prompt copied to clipboard.")
            return
        if value == 2:
            text = _PROMPT_ZH.format(
                commit_msg_instruction="   - 为此变更生成简洁、准确且符合规范的提交信息，提交信息使用英文。"
            )
            copy_to_clipboard(text)
            log.success("中文审查提示已复制到剪贴板。")
            return
        print("Invalid input, please try again.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="git-copy-diff",
        description="Interactively copy git diffs (staged, working, commit, branch, PR) to clipboard.",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    options = [
        "Staged diff (git diff --cached)",
        "Working directory diff (git diff)",
        "Diff of a specific commit",
        "Diffs of multiple commits (input hashes)",
        "Branch diff from merge-base (e.g. vs main/master)",
        "PR diff (gh pr diff)",
        "Generate review prompt for clipboard",
    ]
    handlers = {
        1: _staged_diff,
        2: _working_diff,
        3: _single_commit_diff,
        4: _multi_commit_diff,
        5: _branch_diff,
        6: _pr_diff,
    }

    while True:
        print("\nPlease select the diff type to copy:")
        _print_menu(options)
        try:
            sel = _menu_select(len(options))
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if sel == 0:
            return
        if sel == 7:
            _review_prompt_only()
            continue

        diff, info = handlers[sel]()
        if diff is None or not diff.strip():
            log.info(info.get("empty_msg", "No diff to copy."))
            continue

        prompt_type = _ask_prompt_type()
        if prompt_type == "back":
            continue

        _format_and_copy(diff, prompt_type, info)


if __name__ == "__main__":
    main()
