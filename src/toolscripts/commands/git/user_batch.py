"""``git-user-batch`` - batch read or set git user.name/email for all subdirectory repos."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.prompts import ask

log = get_logger(__name__)


def _is_git_repo(path: Path) -> bool:
    return (path / ".git").exists()


def _git_repos() -> list[Path]:
    cwd = Path.cwd()
    return sorted(p for p in cwd.iterdir() if p.is_dir() and not p.name.startswith(".") and _is_git_repo(p))


def _config_get(repo: Path, key: str) -> str:
    out = subprocess.run(
        ["git", "-C", str(repo), "config", key],
        capture_output=True,
        text=True,
        check=False,
    )
    return out.stdout.strip() or "(not set)"


def _do_read() -> None:
    repos = _git_repos()
    if not repos:
        log.warning("no git repositories found in subdirectories")
        return
    print()
    for repo in repos:
        name = _config_get(repo, "user.name")
        email = _config_get(repo, "user.email")
        print(f"\033[1m{repo.name}\033[0m")
        print(f"  Username: {name}")
        print(f"  Email:    {email}")


def _do_write() -> None:
    repos = _git_repos()
    if not repos:
        log.warning("no git repositories found in subdirectories")
        return
    print()
    print(f"Found {len(repos)} git repositories:")
    for repo in repos:
        print(f"  - {repo.name}")
    print()
    name = ask("Enter Git Username")
    email = ask("Enter Git Email")
    if not name or not email:
        log.error("username and email cannot be empty")
        sys.exit(1)
    print("\nUpdating git config for all repositories...\n")
    for repo in repos:
        subprocess.run(
            ["git", "-C", str(repo), "config", "user.name", name], check=True
        )
        subprocess.run(
            ["git", "-C", str(repo), "config", "user.email", email], check=True
        )
        log.success("%s", repo.name)
    print()
    log.success("all repositories updated")
    print(f"  Username: {name}")
    print(f"  Email:    {email}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="git-user-batch",
        description="Batch read or write git user config across subdirectory repositories.",
    )
    parser.add_argument("action", choices=("read", "write"), help="read or write")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    if args.action == "read":
        _do_read()
    else:
        _do_write()


if __name__ == "__main__":
    main()
