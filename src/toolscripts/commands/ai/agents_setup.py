"""``agents-setup`` - install or remove agent definitions for AI tools.

Single curses interface: tools with agents already installed are pre-selected.
Deselecting a tool removes its agents.  Confirming applies both setup and
cleanup in one pass.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from importlib import resources
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.ui_curses import select_many

from .tools import AI_TOOLS, AITool

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Bundled agent / instruction discovery
# ---------------------------------------------------------------------------


def _data_dir() -> Path | None:
    try:
        ref = resources.files("toolscripts.data.ai")
    except (ModuleNotFoundError, AttributeError):
        return None
    try:
        with resources.as_file(ref) as path:
            return Path(path)
    except Exception:  # noqa: BLE001
        return None


def _agents_dir() -> Path | None:
    base = _data_dir()
    if base is None:
        return None
    candidate = base / "agents"
    return candidate if candidate.exists() else None


def _instructions_source() -> Path | None:
    base = _data_dir()
    if base is None:
        return None
    candidate = base / "AGENTS.md"
    return candidate if candidate.exists() else None


def _load_agent(path: Path) -> dict | None:
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return None
    end = content.find("\n---", 3)
    if end < 0:
        return None
    front = content[3:end].strip()
    metadata: dict[str, str] = {}
    for line in front.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"').strip("'")
    if "name" not in metadata:
        return None
    return {
        "name": metadata["name"],
        "description": metadata.get("description", ""),
        "model": metadata.get("model", "inherit"),
        "source_path": path,
    }


def _discover_agents() -> list[dict]:
    base = _agents_dir()
    if base is None:
        return []
    agents = []
    for md in base.glob("*.md"):
        agent = _load_agent(md)
        if agent:
            agents.append(agent)
    return agents


# ---------------------------------------------------------------------------
# Per-tool state helpers
# ---------------------------------------------------------------------------


def _agent_count(integ: AITool) -> int:
    d = integ.get_agents_dir()
    if not d.exists():
        return 0
    return sum(1 for _ in d.glob("*.md"))


def _has_instructions(integ: AITool) -> bool:
    return integ.get_instructions_path().exists()


def _has_anything(integ: AITool) -> bool:
    return _agent_count(integ) > 0 or _has_instructions(integ)


# ---------------------------------------------------------------------------
# Setup / cleanup actions
# ---------------------------------------------------------------------------


def _setup_one(integ: AITool, agents: list[dict]) -> None:
    log.info("setting up %s ...", integ.tool_name)
    if not integ.is_installed():
        log.warning("not detected, skipping")
        return

    target_dir = integ.get_agents_dir()
    target_dir.mkdir(parents=True, exist_ok=True)

    installed = []
    for agent in agents:
        target = target_dir / f"{agent['name']}.md"
        target.write_text(agent["source_path"].read_text(encoding="utf-8"), encoding="utf-8")
        installed.append(agent["name"])
    if installed:
        log.success("%d agents installed: %s", len(installed), ", ".join(installed))

    src = _instructions_source()
    if src is not None:
        out = integ.get_instructions_path()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        log.success("installed %s -> %s", integ.instructions_filename, out)


def _cleanup_one(integ: AITool) -> None:
    log.info("cleaning up %s ...", integ.tool_name)
    if not _has_anything(integ):
        log.info("nothing to clean")
        return

    parts: list[str] = []
    agents_dir = integ.get_agents_dir()
    if agents_dir.exists():
        count = _agent_count(integ)
        if count:
            shutil.rmtree(agents_dir)
            parts.append(f"removed {count} agent(s)")

    inst = integ.get_instructions_path()
    if inst.exists():
        inst.unlink()
        parts.append(f"removed {integ.instructions_filename}")

    if parts:
        log.success(", ".join(parts))


# ---------------------------------------------------------------------------
# Status line for each tool in the curses picker
# ---------------------------------------------------------------------------


def _status_line(integ: AITool) -> tuple[str, bool, bool]:
    """Return (label, is_preselected, is_disabled)."""
    agents = _agent_count(integ)
    inst = _has_instructions(integ)
    tags: list[str] = []
    if agents:
        tags.append(f"{agents} agent(s)")
    if inst:
        tags.append(integ.instructions_filename)

    if not integ.is_installed():
        return f"{integ.tool_name} (not installed)", False, True
    if tags:
        return f"{integ.tool_name} [{', '.join(tags)}]", True, False
    return f"{integ.tool_name}", False, False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agents-setup",
        description="Install or remove AI agent definitions via a unified curses interface.",
    )
    parser.add_argument("--all", "-a", action="store_true", help="setup all installed tools")
    parser.add_argument("--tool", "-t", help="setup a single tool by id")
    parser.add_argument("--list", "-l", action="store_true", help="list tools and agents")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    agents = _discover_agents()
    if not agents and not args.list:
        log.error(
            "no agent definitions bundled - rebuild the package after adding files in data/ai/agents/"
        )
        sys.exit(1)

    # --list: print status and exit
    if args.list:
        log.info("Available AI Tools:")
        for integ in AI_TOOLS:
            agents_n = _agent_count(integ)
            inst = _has_instructions(integ)
            tags: list[str] = []
            if agents_n:
                tags.append(f"{agents_n} agents")
            if inst:
                tags.append(integ.instructions_filename)
            status = (
                ", ".join(tags)
                if tags
                else ("installed" if integ.is_installed() else "not installed")
            )
            print(f"  {integ.tool_id:<14} {integ.tool_name:<18} [{status}]")
        log.info("Available Agents:")
        for agent in agents:
            print(f"  - {agent['name']}: {agent['description']}")
        return

    # --all: setup every installed tool
    if args.all:
        installed = [i for i in AI_TOOLS if i.is_installed()]
        if not installed:
            log.warning("no installed AI tools detected")
            return
        for integ in installed:
            _setup_one(integ, agents)
        return

    # --tool: setup a single tool by id
    if args.tool:
        for integ in AI_TOOLS:
            if integ.tool_id == args.tool:
                _setup_one(integ, agents)
                return
        log.error("unknown tool: %s (use --list to see options)", args.tool)
        sys.exit(1)

    # Interactive curses picker
    items: list[str] = []
    preselected: list[bool] = []
    disabled: set[int] = set()
    for i, integ in enumerate(AI_TOOLS):
        label, sel, dis = _status_line(integ)
        items.append(label)
        preselected.append(sel)
        if dis:
            disabled.add(i)

    indices = select_many(
        "Select AI tools to set up (deselect to cleanup):",
        items,
        preselected=preselected,
        disabled=disabled,
    )
    if indices is None:
        log.warning("cancelled")
        return

    selected = set(indices)

    # Setup selected tools
    for idx in selected:
        _setup_one(AI_TOOLS[idx], agents)

    # Cleanup deselected (but installed) tools
    for idx, integ in enumerate(AI_TOOLS):
        if idx not in selected and integ.is_installed() and _has_anything(integ):
            _cleanup_one(integ)


if __name__ == "__main__":
    main()
