import subprocess
import pyperclip
import sys

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

def main():
    options = [
        "Staged diff (git diff --cached)",
        "Working directory diff (git diff)",
        "Diff of a specific commit",
        "Diffs of multiple commits (input hashes)",
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

if __name__ == "__main__":
    main()
