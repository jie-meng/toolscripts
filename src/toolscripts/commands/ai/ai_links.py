"""``ai-links`` - create symlinks linking AGENTS.md to per-tool instruction files."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)

SYMLINK_FILES = ("CLAUDE.md", "GEMINI.md", "QWEN.md")
IGNORE_DIRS = (".claude/", ".cursor/", ".gemini/", ".qwen/", ".specify/")
AI_TOOL_DIRS = (".claude", ".cursor", ".gemini", ".qwen")
MAIN_AGENTS_FILE = "AGENTS.md"
MAIN_CONFIG_DIR = ".agents"
MAIN_SKILLS_DIR = f"{MAIN_CONFIG_DIR}/skills"
GITIGNORE_FILE = ".gitignore"


def _find_agents_root(start: Path) -> Path | None:
    current = start.resolve()
    while True:
        if (current / MAIN_AGENTS_FILE).is_file():
            return current
        if current.parent == current:
            return None
        current = current.parent


def _replace_link(target: Path, link: Path) -> None:
    if link.is_symlink() or link.exists():
        if link.is_dir() and not link.is_symlink():
            import shutil
            shutil.rmtree(link)
        else:
            link.unlink()
    link.symlink_to(target)
    log.info("symlink: %s -> %s", link, target)


def _update_gitignore(root: Path) -> None:
    gitignore = root / GITIGNORE_FILE
    if not gitignore.exists():
        return

    content = gitignore.read_text(encoding="utf-8")
    pattern = re.compile(
        r"\n*# AI tools config\n(?:[^\n]*\n)*?(?=\n# |\Z)",
        re.MULTILINE,
    )
    cleaned = pattern.sub("", content).rstrip()

    block = ["", "# AI tools config", *SYMLINK_FILES, *IGNORE_DIRS]
    new = cleaned + "\n" + "\n".join(block) + "\n"
    gitignore.write_text(new, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ai-links",
        description=(
            "Create symlinks linking AGENTS.md to per-tool files (CLAUDE.md/GEMINI.md/QWEN.md), "
            "set up the .agents/skills directory, and update .gitignore."
        ),
    )
    parser.add_argument(
        "--start", default=".", help="starting directory (default: cwd)"
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    root = _find_agents_root(Path(args.start))
    if root is None:
        log.error("no AGENTS.md found in current dir or its parents.")
        sys.exit(1)
    log.info("found AGENTS.md at %s", root / MAIN_AGENTS_FILE)

    for name in SYMLINK_FILES:
        _replace_link(root / MAIN_AGENTS_FILE, root / name)

    if not (root / ".git").exists():
        log.warning("no .git directory found - skipping .agents/skills setup")
        log.success("symlinks created.")
        return

    (root / MAIN_CONFIG_DIR).mkdir(parents=True, exist_ok=True)
    (root / MAIN_SKILLS_DIR).mkdir(parents=True, exist_ok=True)

    for tool in AI_TOOL_DIRS:
        tool_path = root / tool
        tool_path.mkdir(parents=True, exist_ok=True)
        skills_link = tool_path / "skills"
        target = Path("..") / MAIN_SKILLS_DIR
        _replace_link(target, skills_link)

    _update_gitignore(root)
    log.success("AI agent configuration links created in %s", root)


if __name__ == "__main__":
    main()
