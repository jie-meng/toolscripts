import subprocess
import pyperclip
import sys
import re
from urllib.parse import urlparse


def run_cmd(cmd):
    """Run a shell command and return its output, or None if error."""
    try:
        result = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr}")
        return None


def select_from_list(options, prompt="Please select: "):
    """Display a list of options and return the selected index."""
    for idx, opt in enumerate(options):
        print(f"{idx}. {opt}")
    while True:
        try:
            sel = int(input(prompt))
            if 0 <= sel < len(options):
                return sel
            else:
                print("Invalid input, please try again.")
        except Exception:
            print("Please enter a number.")


def get_recent_commits(n=20):
    """Get a list of recent commits (hash and message)."""
    log = run_cmd(f"git log --oneline -n {n}")
    if not log:
        return []
    lines = log.strip().split('\n')
    commits = []
    for line in lines:
        if line:
            parts = line.split(' ', 1)
            if len(parts) == 2:
                commits.append((parts[0], parts[1]))
            else:
                commits.append((parts[0], ''))
    return commits


def print_menu(options):
    print()
    for idx, opt in enumerate(options, 1):
        print(f"{idx}. {opt}")
    print()
    print("0. Exit")


def get_menu_selection(num_options):
    while True:
        try:
            sel = int(input("Please select: "))
            if 0 <= sel <= num_options:
                return sel
            else:
                print("Invalid input, please try again.")
        except Exception:
            print("Please enter a number.")


def copy_and_exit(diff, success_msg, empty_msg):
    if diff is not None and diff.strip():
        pyperclip.copy(diff)
        print(success_msg)
        sys.exit(0)
    else:
        print(empty_msg)
        sys.exit(0)


def handle_staged_diff():
    diff = run_cmd("git diff --cached")
    copy_and_exit(diff, "Staged diff copied to clipboard.\n", "No diff to copy.\n")


def handle_working_diff():
    diff = run_cmd("git diff")
    copy_and_exit(diff, "Working directory diff copied to clipboard.\n", "No diff to copy.\n")


def handle_single_commit():
    while True:
        commits = get_recent_commits()
        commit_options = ["Back to previous menu"] + [f"{c[0]} {c[1]}" for c in commits]
        csel = select_from_list(commit_options, prompt="Select a commit: ")
        if csel == 0:
            break
        else:
            commit_hash = commits[csel-1][0]
            diff = run_cmd(f"git show {commit_hash}")
            copy_and_exit(diff, f"Diff of commit {commit_hash} copied to clipboard.\n", "No diff to copy.\n")


def handle_multiple_commits():
    hashes_input = input("Enter commit hashes (comma separated): ")
    hashes = [h.strip() for h in hashes_input.split(',') if h.strip()]
    if not hashes:
        print("No valid commit hashes entered.\n")
        sys.exit(0)
    all_diffs = []
    for h in hashes:
        diff = run_cmd(f"git show {h}")
        if diff is not None and diff.strip():
            all_diffs.append(diff)
        else:
            print(f"Warning: Could not get diff for commit {h}.")
    if all_diffs:
        combined = '\n\n'.join(all_diffs)
        pyperclip.copy(combined)
        print("Combined diffs copied to clipboard.\n")
        sys.exit(0)
    else:
        print("No diffs copied.\n")
        sys.exit(0)


def parse_pr_input(pr_input):
    """Parse user input for PR.

    Return tuple (repo, number, raw, hostname)
    - repo: owner/repo or None
    - number: PR number or None
    - raw: original input to fallback to gh
    - hostname: hostname from URL if provided (e.g. git.realestate.com.au) else None
    """
    pr_input = pr_input.strip()
    # numeric only
    if re.match(r'^\d+$', pr_input):
        return (None, pr_input, pr_input, None)

    # owner/repo#number
    m = re.match(r'^([^/\s]+/[^#\s]+)#(\d+)$', pr_input)
    if m:
        repo = m.group(1)
        number = m.group(2)
        return (repo, number, pr_input, None)

    # URL
    try:
        parsed = urlparse(pr_input)
        if parsed.scheme and parsed.netloc:
            hostname = parsed.netloc
            # Remove potential port
            if ':' in hostname:
                hostname = hostname.split(':', 1)[0]
            # Expecting paths like /owner/repo/pull/123 or /owner/repo/pulls/123
            parts = [p for p in parsed.path.split('/') if p]
            if len(parts) >= 4 and parts[-2] in ('pull', 'pulls'):
                owner = parts[0]
                repo_name = parts[1]
                number = parts[3] if parts[2] in ('pull', 'pulls') else parts[-1]
                repo = f"{owner}/{repo_name}"
                if re.match(r'^\d+$', number):
                    return (repo, number, pr_input, hostname)
            # fallback: try to extract number at end
            end_number = None
            for part in reversed(parts):
                if re.match(r'^\d+$', part):
                    end_number = part
                    break
            if end_number:
                if len(parts) >= 2:
                    repo = f"{parts[0]}/{parts[1]}"
                    return (repo, end_number, pr_input, hostname)
                return (None, end_number, pr_input, hostname)
    except Exception:
        pass

    # fallback: return raw input and let gh attempt
    return (None, None, pr_input, None)


def handle_pr_diff():
    """Handle copying a PR diff using gh pr diff. Accepts PR URL, number, or owner/repo#number.

    For GitHub Enterprise instances, use the full URL directly instead of --hostname flag.
    """
    pr_input = input("Enter PR URL, number (e.g. 123) or owner/repo#number: ")
    if not pr_input.strip():
        print("No PR provided.\n")
        return
    repo, number, raw, hostname = parse_pr_input(pr_input)

    # Build gh command based on what we parsed
    # For GitHub Enterprise (non-github.com), use the full URL directly
    if hostname and hostname.lower() not in ("github.com", "api.github.com"):
        # Use the original URL for GitHub Enterprise
        cmd = f"gh pr diff {raw}"
    elif repo and number:
        # GitHub.com: use repo + number
        cmd = f"gh pr diff {number} --repo {repo}"
    elif number and not repo:
        # number only, assume current repo
        cmd = f"gh pr diff {number}"
    else:
        # fallback: pass raw input directly to gh
        cmd = f"gh pr diff {raw}"

    print(f"Running: {cmd}")
    diff = run_cmd(cmd)
    copy_and_exit(diff, f"PR diff copied to clipboard.\n", "No diff to copy.\n")


def handle_review_prompt():
    lang_options = ["English (en)", "中文 (zh-cn)"]
    print("\nSelect review prompt language:")
    for idx, opt in enumerate(lang_options, 1):
        print(f"{idx}. {opt}")
    print("0. Exit")
    while True:
        try:
            sel = int(input("Please select: "))
            if sel == 0:
                sys.exit(0)
            elif sel == 1:
                prompt = (
                    "You are a professional AI code review assistant. I will then give you pull requests (including added, deleted, and modified code), file types and project background are unknown. Please strictly analyze and summarize according to these requirements:\n\n"
                    "Tech Stack Inference\n\n"
                    "Infer the primary programming language, frameworks, or libraries used, as well as whether it is backend, frontend, or full-stack, based on the diff.\n"
                    "Briefly explain your reasoning (e.g., language syntax, imported libraries, project structure clues, etc.).\n"
                    "Overview of Code Changes\n\n"
                    "Summarize in concise technical language what the main changes in this diff are (e.g., bug fixes, feature additions, refactoring, configuration changes).\n"
                    "Indicate the primary modules or business functionalities affected by these changes.\n"
                    "Code Quality & Clean Code Evaluation\n\n"
                    "Thoroughly assess code style, naming conventions, comments and documentation, readability, maintainability, architecture and modularity, code duplication, etc.\n"
                    "Identify error-prone code, unsafe patterns, inefficient implementations, anti-patterns, or parts that violate best practices.\n"
                    "Clearly specify the exact location and nature of each problem (line number, filename, code snippet, or sufficiently precise description).\n"
                    "Provide actionable suggestions for fixes/refactoring/optimization, along with explanatory reasoning.\n"
                    "Major Issues and Risks\n\n"
                    "Evaluate whether there are hard-to-detect logic bugs, unhandled exceptions, missing boundary checks, performance bottlenecks, or security vulnerabilities.\n"
                    "Clearly point out these suspicious parts and briefly explain their potential impact.\n"
                    "Incremental Suggestions\n\n"
                    "Offer further suggestions to improve code quality, maintainability, and test coverage (such as unit tests, better comments, type annotations, or improved documentation).\n"
                    "Please follow this structure for a professional review report. The review should be comprehensive and rigorous—highlight any and all suspicious or problematic code, and provide practical, actionable advice. Do not omit seemingly minor issues.\n\n"
                )
                pyperclip.copy(prompt)
                print("English review prompt copied to clipboard.\n")
                sys.exit(0)
            elif sel == 2:
                prompt = (
                    "你是专业的代码审查(AI Code Review)助手。接下来我会不断给出 Pull Request 的 DIFF（包含增删改），文件类型和项目上下文未知。请你按照以下要求严格分析和总结：\n\n"
                    "技术栈推断\n\n"
                    "根据 diff 内容推断主要使用的编程语言、框架或库，以及明显的后端/前端/全栈类型（如有）。\n"
                    "简单说明推断的依据（如语法、导入库、项目结构线索等）。\n"
                    "代码变更概览\n\n"
                    "用简明扼要的语言总结此 diff 主要做了哪些事情（例如：修复 bug、添加功能、重构、配置变更等）。\n"
                    "说明受影响的主要模块或功能业务。\n"
                    "代码质量 & Clean Code 评价\n\n"
                    "全面评估变更的代码风格、命名、注释、可读性、可维护性、设计架构、模块解耦、重复代码等。\n"
                    "发现任何易错写法、不安全代码、低效实现、反模式或不符合最佳实践的地方要具体列出。\n"
                    "指出被修改的具体位置与问题描述（行号/文件名/代码片段，或足够明确的定位描述）。\n"
                    "提出详细的修复/重构/优化建议，并解释理由。\n"
                    "潜在的重大问题和风险\n\n"
                    "检查代码逻辑是否存在难以发现的 bug、异常未处理、未校验边界条件、性能瓶颈、安全隐患等。\n"
                    "指出这些疑点，并简单说明为何值得关注。\n"
                    "增量建议\n\n"
                    "给出进一步增强代码质量、工程可维护性、测试覆盖的建议（如单测、注释、类型声明、文档完善等）。\n"
                    "请严格按照上述结构给出专业分析报告。审查要全面严谨，发现问题要清晰具体，并给出实际可行的建议。不要遗漏任何看起来可疑的写法。\n\n"
                )
                pyperclip.copy(prompt)
                print("中文审查提示已复制到剪贴板。\n")
                sys.exit(0)
            else:
                print("Invalid input, please try again.")
        except Exception:
            print("Please enter a number.")


def main():
    options = [
        "Staged diff (git diff --cached)",
        "Working directory diff (git diff)",
        "Diff of a specific commit",
        "Diffs of multiple commits (input hashes)",
        "PR diff (gh pr diff)",
        "Generate review prompt from working diff",
    ]
    while True:
        print("\nPlease select the diff type to copy:")
        print_menu(options)
        sel = get_menu_selection(len(options))
        if sel == 0:
            sys.exit(0)
        elif sel == 1:
            handle_staged_diff()
        elif sel == 2:
            handle_working_diff()
        elif sel == 3:
            handle_single_commit()
        elif sel == 4:
            handle_multiple_commits()
        elif sel == 5:
            handle_pr_diff()
        elif sel == 6:
            handle_review_prompt()


if __name__ == "__main__":
    main()

