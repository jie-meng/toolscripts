"""``graphify-setup`` - install/uninstall graphify skill for AI coding tools.

Requires the ``graphify`` CLI (``pipx install graphifyy``).  Shows a curses
multi-select where tools with graphify already installed are pre-selected.
Deselecting a tool uninstalls graphify from it; selecting installs.

Each platform has two levels:

* **User-level** — ``graphify install --platform <P>`` installs the skill to
  the platform's config directory (e.g. ``~/.claude/skills/graphify/``).
* **Project-level** — ``graphify <P> install`` writes config into the current
  project directory (e.g. ``CLAUDE.md``, ``.opencode/``).

Install runs both levels.  Uninstall reverses: project-level first, then
removes the user-level skill directory.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import which
from toolscripts.core.ui_curses import select_many

from .tools import AI_TOOLS

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Graphify platform mapping
# ---------------------------------------------------------------------------


class _GraphifyPlatform:
    """Maps an AITool to its graphify CLI subcommand."""

    __slots__ = ("tool_id", "subcommand", "skill_path", "project_marker")

    def __init__(
        self,
        tool_id: str,
        subcommand: str,
        skill_path: Path | None = None,
        *,
        project_marker: str | None = None,
    ) -> None:
        self.tool_id = tool_id
        self.subcommand = subcommand
        self.skill_path = skill_path
        self.project_marker = project_marker

    def is_installed(self) -> bool:
        """Check if graphify is installed (user-level or project-level)."""
        if self.skill_path is not None:
            return self.skill_path.is_dir() or self.skill_path.is_file()
        if self.project_marker is not None:
            return Path(self.project_marker).exists()
        return False


_HOME = Path.home()

# graphify subcommand for each platform
# Platforms with user-level skill: skill_path points to the install dir.
# Platforms with only project-level config: project_marker is a relative path
# checked against the current working directory.
# fmt: off
GRAPHIFY_PLATFORMS: list[_GraphifyPlatform] = [
    _GraphifyPlatform("claude-code", "claude",   _HOME / ".claude" / "skills" / "graphify"),
    _GraphifyPlatform("codex",       "codex",     _HOME / ".agents" / "skills" / "graphify"),
    _GraphifyPlatform("copilot",     "copilot",   _HOME / ".copilot" / "skills" / "graphify"),
    _GraphifyPlatform("cursor",      "cursor",    project_marker=".cursor/rules/graphify.mdc"),
    _GraphifyPlatform("gemini",      "gemini",    _HOME / ".gemini" / "skills" / "graphify"),
    _GraphifyPlatform("opencode",    "opencode",  _HOME / ".config" / "opencode" / "skills" / "graphify"),
]
# fmt: on

_PLATFORM_BY_ID: dict[str, _GraphifyPlatform] = {p.tool_id: p for p in GRAPHIFY_PLATFORMS}


# ---------------------------------------------------------------------------
# Install / uninstall
# ---------------------------------------------------------------------------


def _run_graphify(*args: str) -> bool:
    """Run ``graphify <args>``; return True on success."""
    cmd = ["graphify", *args]
    log.info("running: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        log.error("graphify failed (exit %d): %s", result.returncode, stderr or "(no output)")
        return False
    if result.stdout.strip():
        log.debug("%s", result.stdout.strip())
    return True


def _install_one(plat: _GraphifyPlatform) -> None:
    """Install graphify for a platform: user-level skill + project-level config."""
    if plat.skill_path is not None:
        # user-level: install skill to platform config dir
        _run_graphify("install", "--platform", plat.subcommand)
    # project-level: write config in current directory
    if _run_graphify(plat.subcommand, "install"):
        log.success("graphify installed for %s", plat.subcommand)


def _uninstall_one(plat: _GraphifyPlatform) -> None:
    """Uninstall graphify for a platform: project-level first, then user-level skill."""
    # 1) project-level: remove config from current directory
    _run_graphify(plat.subcommand, "uninstall")
    # 2) user-level: remove skill directory / files (if user-level exists)
    target = plat.skill_path
    if target is not None:
        if target.is_dir():
            shutil.rmtree(target)
            log.info("removed user-level skill: %s", target)
        elif target.is_file():
            target.unlink()
            log.info("removed user-level skill: %s", target)
    log.success("graphify uninstalled for %s", plat.subcommand)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _check_graphify() -> bool:
    if which("graphify") is None:
        log.error(
            "graphify CLI not found. Install it first:\n"
            "  pipx install graphifyy && graphify install\n"
            "  # or: uv tool install graphifyy && graphify install"
        )
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="graphify-setup",
        description="Install/uninstall the graphify skill for AI coding tools.",
    )
    parser.add_argument("--all", "-a", action="store_true", help="install for all detected tools")
    parser.add_argument("--tool", "-t", help="install for a single tool by id")
    parser.add_argument("--list", "-l", action="store_true", help="list graphify platform status")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    if not _check_graphify():
        sys.exit(1)

    # --list
    if args.list:
        log.info("Graphify platform support:")
        for integ in AI_TOOLS:
            plat = _PLATFORM_BY_ID.get(integ.tool_id)
            if plat is None:
                continue
            installed = integ.is_installed()
            has_graphify = plat.is_installed() if installed else False
            status = (
                "graphify installed"
                if has_graphify
                else ("installed" if installed else "not installed")
            )
            print(f"  {integ.tool_id:<14} {integ.tool_name:<18} [{status}]")
        return

    # --all
    if args.all:
        for integ in AI_TOOLS:
            plat = _PLATFORM_BY_ID.get(integ.tool_id)
            if plat is None:
                continue
            if integ.is_installed():
                _install_one(plat)
        return

    # --tool
    if args.tool:
        plat = _PLATFORM_BY_ID.get(args.tool)
        if plat is None:
            log.error(
                "unknown graphify platform: %s (supported: %s)",
                args.tool,
                ", ".join(p.tool_id for p in GRAPHIFY_PLATFORMS),
            )
            sys.exit(1)
        _install_one(plat)
        return

    # Interactive curses picker
    items: list[str] = []
    preselected: list[bool] = []
    disabled: set[int] = set()
    platform_indices: list[int] = []  # maps picker index → AI_TOOLS index

    for i, integ in enumerate(AI_TOOLS):
        plat = _PLATFORM_BY_ID.get(integ.tool_id)
        if plat is None:
            continue
        platform_indices.append(i)
        if not integ.is_installed():
            items.append(f"{integ.tool_name} (not installed)")
            preselected.append(False)
            disabled.add(len(items) - 1)
        elif plat.is_installed():
            items.append(f"{integ.tool_name} [graphify installed]")
            preselected.append(True)
        else:
            items.append(f"{integ.tool_name}")
            preselected.append(False)

    indices = select_many(
        "Select AI tools for graphify (deselect to uninstall):",
        items,
        preselected=preselected,
        disabled=disabled,
    )
    if indices is None:
        log.warning("cancelled")
        return

    selected = set(indices)

    # Install selected
    for picker_idx in selected:
        tool_idx = platform_indices[picker_idx]
        plat = _PLATFORM_BY_ID[AI_TOOLS[tool_idx].tool_id]
        _install_one(plat)

    # Uninstall deselected (that have graphify)
    for picker_idx, tool_idx in enumerate(platform_indices):
        if picker_idx not in selected:
            plat = _PLATFORM_BY_ID[AI_TOOLS[tool_idx].tool_id]
            if plat.is_installed():
                _uninstall_one(plat)


if __name__ == "__main__":
    main()
