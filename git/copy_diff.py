import subprocess
import sys
import re
import platform
from urllib.parse import urlparse


def run_cmd(cmd):
    """Run a shell command and return its output, or None if error."""
    try:
        result = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
        return result.stdout
    except subprocess.CalledProcessError:
        # Don't print error for commands that are expected to fail (like checks)
        return None


def copy_to_clipboard(content):
    """Copy content to clipboard using appropriate method for the OS."""
    system = platform.system()
    if system == "Darwin":  # macOS
        try:
            process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE, text=True)
            process.communicate(input=content)
            return True
        except Exception as e:
            print(f"Error: Failed to copy to clipboard: {e}")
            return False
    else:  # Other systems (Linux, Windows, etc.)
        try:
            import pyperclip
            pyperclip.copy(content)
            return True
        except Exception as e:
            print(f"Error: Failed to copy to clipboard: {e}")
            return False


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


def get_current_branch():
    """Get the current git branch name."""
    return run_cmd("git rev-parse --abbrev-ref HEAD")


def get_commit_message_format():
    """Determine commit message format based on branch name.
    
    If branch name is in A/B/C format (contains two slashes),
    return format like 'A[B] message' (e.g., 'feat[SNEC-001] message').
    Otherwise return None for default format.
    """
    branch = get_current_branch()
    if not branch:
        return None
    
    branch = branch.strip()
    # Check if branch name contains exactly two slashes (A/B/C format)
    if branch.count('/') == 2:
        parts = branch.split('/', 2)
        prefix = parts[0]  # A
        middle = parts[1]  # B
        # Return format string with placeholders
        return f"{prefix}[{middle}] <message>"
    
    return None


def get_staged_diff():
    """Get staged diff."""
    diff = run_cmd("git diff --cached")
    info = {"success_msg": "Staged diff copied to clipboard.\n", "empty_msg": "No staged diff to copy.\n"}
    return diff, info

def get_working_diff():
    """Get working directory diff."""
    diff = run_cmd("git diff")
    info = {"success_msg": "Working directory diff copied to clipboard.\n", "empty_msg": "No diff to copy.\n"}
    return diff, info

def get_single_commit_diff():
    """Get diff of a single, user-selected commit."""
    while True:
        commits = get_recent_commits()
        if not commits:
            return None, {"empty_msg": "No recent commits found.\n"}
        commit_options = ["Back to previous menu"] + [f"{c[0]} {c[1]}" for c in commits]
        csel = select_from_list(commit_options, prompt="Select a commit: ")
        if csel == 0:
            return None, {}  # User chose to go back
        else:
            commit_hash = commits[csel-1][0]
            diff = run_cmd(f"git show {commit_hash}")
            info = {
                "success_msg": f"Diff of commit {commit_hash} copied to clipboard.\n",
                "empty_msg": "No diff to copy.\n"
            }
            return diff, info

def get_multiple_commits_diff():
    """Get combined diff of multiple user-inputted commits."""
    hashes_input = input("Enter commit hashes (comma separated): ")
    hashes = [h.strip() for h in hashes_input.split(',') if h.strip()]
    if not hashes:
        return None, {"empty_msg": "No valid commit hashes entered.\n"}

    all_diffs = []
    for h in hashes:
        diff = run_cmd(f"git show {h}")
        if diff is not None and diff.strip():
            all_diffs.append(diff)
        else:
            print(f"Warning: Could not get diff for commit {h}.")

    if not all_diffs:
        return None, {"empty_msg": "No diffs could be generated.\n"}

    combined = '\n\n'.join(all_diffs)
    info = {"success_msg": "Combined diffs copied to clipboard.\n"}
    return combined, info

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


def get_pr_diff():
    """Get PR diff using gh command."""
    pr_input = input("Enter PR URL, number (e.g. 123) or owner/repo#number: ")
    if not pr_input.strip():
        return None, {"empty_msg": "No PR provided.\n"}
    
    repo, number, raw, hostname = parse_pr_input(pr_input)

    if hostname and hostname.lower() not in ("github.com", "api.github.com"):
        cmd = f"gh pr diff {raw}"
    elif repo and number:
        cmd = f"gh pr diff {number} --repo {repo}"
    elif number and not repo:
        cmd = f"gh pr diff {number}"
    else:
        cmd = f"gh pr diff {raw}"

    print(f"Running: {cmd}")
    diff = run_cmd(cmd)
    info = {"success_msg": "PR diff copied to clipboard.\n", "empty_msg": "No diff to copy.\n"}
    return diff, info

def get_branch_diff():
    """Get the combined diff for all commits on the current branch since it forked."""
    current_branch = get_current_branch()
    if not current_branch:
        return None, {"empty_msg": "Could not determine the current branch."}
    current_branch = current_branch.strip()

    base_branch_candidates = ['origin/main', 'origin/master', 'origin/develop', 'origin/dev', 'main', 'master', 'develop', 'dev']
    auto_detected_base = None

    for candidate in base_branch_candidates:
        proc = subprocess.run(f"git rev-parse --verify {candidate}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode == 0:
            auto_detected_base = candidate
            break

    final_base_branch = None
    if auto_detected_base:
        prompt_message = f"Automatically selected '{auto_detected_base}' as the base. Press Enter to confirm, or enter a different branch/commit hash: "
        user_input = input(prompt_message).strip()
        final_base_branch = user_input if user_input else auto_detected_base
    else:
        prompt_message = "Could not automatically find a base branch. Please enter a base branch or commit hash to compare against: "
        user_input = input(prompt_message).strip()
        if not user_input:
            return None, {"empty_msg": "No base branch provided. Aborting."}
        final_base_branch = user_input

    diff_cmd = f"git diff {final_base_branch}...{current_branch}"
    print(f"Running: {diff_cmd}")
    diff = run_cmd(diff_cmd)
    
    info = {
        "success_msg": f"Diff of branch '{current_branch}' from its fork point with '{final_base_branch}' copied to clipboard.\n",
        "empty_msg": "No diff to copy.\n",
        "current_branch": current_branch
    }
    return diff, info

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
                copy_to_clipboard(prompt)
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
                copy_to_clipboard(prompt)
                print("中文审查提示已复制到剪贴板。\n")
                sys.exit(0)
            else:
                print("Invalid input, please try again.")
        except Exception:
            print("Please enter a number.")


def ask_for_prompt_type():
    """Asks user for review prompt preference, returns prompt type or 'back'."""
    print("\nDo you want to include a review prompt?")
    print("1. No")
    print("2. En (English)")
    print("3. Zh (中文)")
    print("0. Back to main menu")

    while True:
        sel_input = input("Please select (default: 1): ").strip()
        if sel_input == '':
            return None  # No prompt
        try:
            sel_num = int(sel_input)
            if sel_num == 0:
                return 'back'
            elif sel_num == 1:
                return None  # No prompt
            elif sel_num == 2:
                return 'en'
            elif sel_num == 3:
                return 'zh-cn'
            else:
                print("Invalid input, please try again.")
        except ValueError:
            print("Please enter a number.")

def format_and_copy(diff, prompt_type, info):
    """Formats the diff with an optional review prompt and copies to clipboard."""
    content_to_copy = '```\n' + diff + '```\n'
    
    if prompt_type:
        current_branch = info.get("current_branch", get_current_branch().strip())
        commit_format = get_commit_message_format()

        if prompt_type == 'en':
            commit_msg_instruction = "- Generate a concise, accurate, and conventional commit message for this change."
            if commit_format:
                commit_msg_instruction = f"- Generate a concise, accurate commit message for this change. Based on the branch name '{current_branch}', use the format: '{commit_format}'."
            
            content_to_copy += '\n\n' + f'''As a professional code reviewer, please analyze the above git diff and output your review in clear, structured English Markdown. Strictly follow this format:

1. **Problematic Code & Explanation**
   - List all code snippets with potential issues (bugs, design flaws, maintainability, performance, etc.), and clearly explain the reason and impact for each.

2. **Improvement Suggestions**
   - For each issue, provide concrete suggestions for improvement or fixes.

3. **Overall Assessment**
   - Summarize the strengths and risks of this change, and highlight anything that needs special attention.

4. **Recommended Commit Message**
   {commit_msg_instruction}

Format your output in clean Markdown for easy copy-paste into review tools or commit descriptions.'''
        elif prompt_type == 'zh-cn':
            commit_msg_instruction = "- 为此变更生成简洁、准确且符合规范的提交信息，提交信息使用英文。"
            if commit_format:
                commit_msg_instruction = f"- 为此变更生成简洁、准确且符合规范的提交信息。基于分支名 '{current_branch}'，使用格式: '{commit_format}'。提交信息使用英文。"
            
            content_to_copy += '\n\n' + f'''作为一名专业的代码审查员，请分析上述 git diff 并以清晰、结构化的中文 Markdown 格式输出您的审查意见。请严格遵循以下格式：

1. **问题代码及说明**
   - 列出所有存在潜在问题的代码片段（bug、设计缺陷、可维护性、性能等），并清楚说明每个问题的原因和影响。

2. **改进建议**
   - 针对每个问题，提供具体的改进或修复建议。

3. **整体评估**
   - 总结此次变更的优势和风险，并突出需要特别关注的地方。

4. **推荐提交信息**
   {commit_msg_instruction}

请以清晰的 Markdown 格式输出，便于复制粘贴到审查工具或提交描述中。'''

    copy_to_clipboard(content_to_copy)
    print(info.get("success_msg", "Diff copied to clipboard.\n"))

def main():
    options = [
        "Staged diff (git diff --cached)",
        "Working directory diff (git diff)",
        "Diff of a specific commit",
        "Diffs of multiple commits (input hashes)",
        "Branch diff from merge-base (e.g. vs main/master)",
        "PR diff (gh pr diff)",
        "Generate review prompt for clipboard",
    ]
    
    diff_handlers = {
        1: get_staged_diff,
        2: get_working_diff,
        3: get_single_commit_diff,
        4: get_multiple_commits_diff,
        5: get_branch_diff,
        6: get_pr_diff,
    }

    while True:
        print("\nPlease select the diff type to copy:")
        print_menu(options)
        sel = get_menu_selection(len(options))

        if sel == 0:
            sys.exit(0)
        
        if sel == 7:
            handle_review_prompt()
            continue

        # Get diff content and info from the appropriate handler
        handler = diff_handlers.get(sel)
        if not handler:
            print("Invalid selection.")
            continue
            
        diff, info = handler()

        # If diff is None, it means operation failed, was cancelled, or produced no output.
        # The message should be in the info dict.
        if diff is None or not diff.strip():
            if "empty_msg" in info:
                print(info["empty_msg"])
            continue

        # Now that we have the diff, ask about the review prompt
        prompt_type = ask_for_prompt_type()
        if prompt_type == 'back':
            continue

        # Format with prompt and copy to clipboard
        format_and_copy(diff, prompt_type, info)


if __name__ == "__main__":
    main()