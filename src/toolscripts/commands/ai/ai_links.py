"""``ai-links`` - link AGENTS.md / .agents/{agents,skills} into per-tool config.

For every AI coding tool selected by the user, ``ai-links`` creates up to
three symlinks at the repository root:

* ``<tool's instructions filename> -> AGENTS.md`` — only for tools that
  insist on their own filename (claude → ``CLAUDE.md``, gemini → ``GEMINI.md``,
  qwen → ``QWEN.md``). Tools that already read ``AGENTS.md`` directly get
  no root link.
* ``<tool>/agents -> ../.agents/agents`` — exposes the project's shared
  agent definitions (when the tool supports it).
* ``<tool>/skills -> ../.agents/skills`` — only created for tools where
  the link genuinely helps (claude only reads ``.claude/skills``; cursor's
  slash commands only fire from ``.cursor/skills``). Tools that natively
  discover ``.agents/skills/`` (codex, gemini, qwen, opencode, copilot)
  skip this link to avoid clutter.

Every per-tool path is declared on its ``AITool`` row in ``tools.py`` —
that module is the single source of truth shared with ``agents-setup`` and
``ai-links``. When a vendor moves a path, you update one row.

Behavior
--------

* Already-linked tools come pre-checked in the picker. Deselecting a tool
  removes any of its links that this command had created.
* The picker shows whether each tool is installed under your home dir as
  an informational hint, but installation is *not* a precondition for
  linking — a repo can be prepared on a machine that doesn't have the
  tool installed yet.
* If the tool's config dir at the repo root is itself a symlink that
  resolves to the project's ``.agents/`` directory (a common manual setup
  where the user did ``ln -s .agents .claude``), ai-links *refuses* to
  create child links inside it — descending would produce a self-loop
  symlink. The user is told to remove the umbrella symlink first.
 * ``.gitignore`` is rewritten to ignore exactly the symlinks ai-links
 * would create — no blind appending, no ignoring of the user's other
 * config files.  ``.opencode`` is always included (opencode may create a
 * project-level config dir).
"""

from __future__ import annotations

import argparse
import contextlib
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.ui_curses import select_many

from .tools import AI_TOOLS, AITool

log = get_logger(__name__)

MAIN_AGENTS_FILE = "AGENTS.md"
MAIN_CONFIG_DIR = ".agents"
MAIN_AGENTS_SUBDIR = "agents"
MAIN_SKILLS_SUBDIR = "skills"
GITIGNORE_FILE = ".gitignore"
GITIGNORE_BLOCK_HEADER = "# AI tools config"

@dataclass(frozen=True)
class LinkSpec:
    """One symlink ai-links manages: ``link`` points at ``display_target``.

    * ``link``: where the symlink lives, relative to the repo root (e.g.
      ``.cursor/agents``).
    * ``display_target``: where the symlink resolves to, relative to the
      repo root (e.g. ``.agents/agents``). This is what we show users in
      log messages, the picker, and ``--list``.
    * ``link_target``: the actual string stored *inside* the symlink. It's
      relative to the link's parent dir (e.g. ``../.agents/agents``) so the
      link survives moving the repo around. Computed from
      ``display_target``; users never need to see this.
    """

    link: Path
    display_target: Path

    @property
    def link_target(self) -> Path:
        depth = len(self.link.parts) - 1
        return Path(*([".."] * depth)) / self.display_target


def _has_anything_to_link(tool: AITool) -> bool:
    return any(
        x is not None
        for x in (
            tool.repo_instructions_filename,
            tool.repo_umbrella_dir,
            tool.repo_agents_dir,
            tool.repo_skills_dir,
        )
    )


TOOLS: list[AITool] = sorted(
    (t for t in AI_TOOLS if _has_anything_to_link(t)),
    key=lambda t: t.tool_id,
)


def _link_specs(tool: AITool) -> list[LinkSpec]:
    """Every symlink ai-links would create for ``tool``, in apply order.

    Umbrella mode: if ``repo_umbrella_dir`` is set, one symlink replaces
    the tool's whole config dir with ``.agents/`` — covering ``agents/``,
    ``skills/``, and any future shared subdir at once. The per-subdir
    fields are ignored in this mode.
    """
    specs: list[LinkSpec] = []
    if tool.repo_instructions_filename:
        specs.append(LinkSpec(Path(tool.repo_instructions_filename), Path(MAIN_AGENTS_FILE)))
    if tool.repo_umbrella_dir:
        specs.append(LinkSpec(Path(tool.repo_umbrella_dir), Path(MAIN_CONFIG_DIR)))
    else:
        main_agents = Path(MAIN_CONFIG_DIR) / MAIN_AGENTS_SUBDIR
        main_skills = Path(MAIN_CONFIG_DIR) / MAIN_SKILLS_SUBDIR
        if tool.repo_agents_dir:
            specs.append(LinkSpec(Path(tool.repo_agents_dir), main_agents))
        if tool.repo_skills_dir:
            specs.append(LinkSpec(Path(tool.repo_skills_dir), main_skills))
    return specs


def _find_agents_root(start: Path) -> Path | None:
    current = start.resolve()
    while True:
        if (current / MAIN_AGENTS_FILE).is_file():
            return current
        if current.parent == current:
            return None
        current = current.parent


def _remove_path(path: Path) -> bool:
    if path.is_symlink() or path.exists():
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()
        return True
    return False


def _replace_link(spec: LinkSpec, link_path: Path) -> None:
    _remove_path(link_path)
    link_path.parent.mkdir(parents=True, exist_ok=True)
    link_path.symlink_to(spec.link_target)
    log.info("link: %s -> %s", spec.link, spec.display_target)


def _is_umbrella_symlink_to_main(root: Path, link_path: Path) -> bool:
    """Detect ``<root>/<config_dir> -> <root>/.agents`` style umbrella links.

    Walks up the link path's ancestors and returns True if any of them is a
    symlink whose resolved target is the project's ``.agents`` directory.
    Creating children under such a path would produce a symlink loop
    (e.g. ``.agents/skills -> ../.agents/skills``).
    """
    main_resolved = (root / MAIN_CONFIG_DIR).resolve()
    cur = root / link_path
    while cur != root:
        parent = cur.parent
        if parent.is_symlink():
            try:
                if parent.resolve() == main_resolved:
                    return True
            except OSError:
                pass
        cur = parent
    return False


def _apply_selection(root: Path, selected: set[str]) -> None:
    for tool in TOOLS:
        is_selected = tool.tool_id in selected
        for spec in _link_specs(tool):
            link_path = root / spec.link
            if _is_umbrella_symlink_to_main(root, spec.link):
                log.warning(
                    "skipping %s: an ancestor is a symlink to %s/ "
                    "(would create a self-loop). Remove the umbrella "
                    "symlink first if you want per-tool links instead.",
                    spec.link,
                    MAIN_CONFIG_DIR,
                )
                continue
            if is_selected:
                _replace_link(spec, link_path)
            elif _remove_path(link_path):
                log.info("removed: %s", spec.link)
                _maybe_rmdir_chain(link_path.parent, root)


def _maybe_rmdir_chain(start: Path, root: Path) -> None:
    """Remove ``start`` and its empty parents up to (but not including) ``root``.

    Stops at the first non-empty directory or anything that isn't an
    ordinary directory (e.g. a symlink). Never crosses ``root`` and never
    touches ``.agents/`` / ``.git/``.
    """
    cur = start
    while cur != root and cur.is_dir() and not cur.is_symlink():
        if cur.name in {MAIN_CONFIG_DIR, ".git"}:
            return
        with contextlib.suppress(OSError):
            if any(cur.iterdir()):
                return
            cur.rmdir()
            log.info("removed empty dir: %s", cur)
        cur = cur.parent


def _gitignore_entries(selected: set[str]) -> list[str]:
    entries: list[str] = []
    for tool in TOOLS:
        if tool.tool_id not in selected:
            continue
        for spec in _link_specs(tool):
            entries.append(str(spec.link))
    # .opencode — opencode has no repo-level symlinks, but may create a
    # project-level config directory that should be gitignored.  Always
    # include it (harmless if the dir doesn't exist).
    entries.append(".opencode")
    seen: set[str] = set()
    deduped: list[str] = []
    for entry in entries:
        if entry not in seen:
            seen.add(entry)
            deduped.append(entry)
    return deduped


def _update_gitignore(root: Path, selected: set[str]) -> None:
    gitignore = root / GITIGNORE_FILE
    if not gitignore.exists():
        return

    content = gitignore.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"\n*{re.escape(GITIGNORE_BLOCK_HEADER)}\n(?:[^\n]*\n)*?(?=\n*(?:# |\Z))",
        re.MULTILINE,
    )
    cleaned = pattern.sub("\n", content).strip("\n")

    entries = _gitignore_entries(selected)

    if not entries:
        new = (cleaned + "\n") if cleaned else ""
    else:
        block = "\n".join([GITIGNORE_BLOCK_HEADER, *entries])
        new = (cleaned + "\n\n" if cleaned else "") + block + "\n"

    if new != content:
        gitignore.write_text(new, encoding="utf-8")
        log.info("updated %s", gitignore)


def _ensure_main_subdir(root: Path, sub: str) -> None:
    """Make sure ``.agents/<sub>/`` is a real directory.

    Earlier versions of this command could leave behind a self-loop symlink
    here (e.g. ``.agents/skills -> ../.agents/skills``) when the user had
    set up an umbrella ``.<tool> -> .agents`` link. Heal that situation by
    removing the bogus symlink before recreating the directory.
    """
    path = root / MAIN_CONFIG_DIR / sub
    if path.is_symlink():
        log.warning("repairing bogus symlink: %s", path)
        path.unlink()
    path.mkdir(parents=True, exist_ok=True)


def _detect_current_selection(root: Path) -> set[str]:
    """Mark a tool as currently set up if any of its links already exists."""
    selected: set[str] = set()
    for tool in TOOLS:
        for spec in _link_specs(tool):
            if (root / spec.link).is_symlink():
                selected.add(tool.tool_id)
                break
    return selected


def _picker_label(tool: AITool) -> str:
    parts = [f"{spec.link} -> {spec.display_target}" for spec in _link_specs(tool)]
    installed = "installed" if tool.is_installed() else "not installed locally"
    return f"{tool.tool_name}  ({installed})  [{'; '.join(parts)}]"


def _interactive_pick(current: set[str]) -> set[str] | None:
    items = [_picker_label(tool) for tool in TOOLS]
    preselected = [tool.tool_id in current for tool in TOOLS]
    # Disable tools that are not installed and not already linked so they are
    # excluded from "Select All" and rendered dimmed. Tools that are already
    # linked remain fully toggleable so the user can remove those links.
    disabled = {
        i for i, tool in enumerate(TOOLS) if not tool.is_installed() and tool.tool_id not in current
    }
    indices = select_many(
        "Select AI tools — already-linked tools are pre-checked:",
        items,
        preselected=preselected,
        disabled=disabled or None,
    )
    if indices is None:
        return None
    return {TOOLS[i].tool_id for i in indices}


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ai-links",
        description=(
            "Link AGENTS.md and .agents/{agents,skills} into the AI tool "
            "config dirs you pick. Already-linked tools are pre-selected; "
            "deselecting one cleans its links up. .gitignore is rewritten "
            "to match the final selection."
        ),
    )
    parser.add_argument("--start", default=".", help="starting directory (default: cwd)")
    parser.add_argument("--all", "-a", action="store_true", help="link all known tools (no prompt)")
    parser.add_argument(
        "--tool",
        "-t",
        action="append",
        default=[],
        help="link a specific tool by id (repeatable). Implies non-interactive.",
    )
    parser.add_argument("--list", "-l", action="store_true", help="list known tools and exit")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    if args.list:
        log.info("Tools ai-links can configure (alphabetical):")
        for tool in TOOLS:
            spec_text = "; ".join(f"{s.link} -> {s.display_target}" for s in _link_specs(tool))
            installed = "installed" if tool.is_installed() else "not installed"
            print(f"  {tool.tool_id:<14} {tool.tool_name:<16} [{installed}]  {spec_text}")
        skipped = sorted(t.tool_id for t in AI_TOOLS if not _has_anything_to_link(t))
        if skipped:
            log.info(
                "Skipped (no symlink-able resources): %s",
                ", ".join(skipped),
            )
        return

    root = _find_agents_root(Path(args.start))
    if root is None:
        log.error("no %s found in current dir or its parents.", MAIN_AGENTS_FILE)
        sys.exit(1)
    log.info("found %s at %s", MAIN_AGENTS_FILE, root / MAIN_AGENTS_FILE)

    current = _detect_current_selection(root)

    if args.all:
        selected: set[str] | None = {tool.tool_id for tool in TOOLS}
    elif args.tool:
        configurable = {tool.tool_id for tool in TOOLS}
        all_known = {tool.tool_id for tool in AI_TOOLS}
        unknown = [t for t in args.tool if t not in all_known]
        if unknown:
            log.error("unknown tool id(s): %s (use --list to see options)", ", ".join(unknown))
            sys.exit(1)
        nothing_to_do = [t for t in args.tool if t not in configurable]
        if nothing_to_do:
            log.warning(
                "nothing to link for: %s (no symlink-able resources)",
                ", ".join(nothing_to_do),
            )
        selected = {t for t in args.tool if t in configurable}
    else:
        selected = _interactive_pick(current)
        if selected is None:
            log.warning("cancelled")
            return

    _ensure_main_subdir(root, MAIN_SKILLS_SUBDIR)
    _ensure_main_subdir(root, MAIN_AGENTS_SUBDIR)

    _apply_selection(root, selected)
    _update_gitignore(root, selected)

    if selected:
        log.success(
            "linked %d tool(s): %s",
            len(selected),
            ", ".join(sorted(selected)),
        )
    else:
        log.success("all AI tool links removed")


if __name__ == "__main__":
    main()
