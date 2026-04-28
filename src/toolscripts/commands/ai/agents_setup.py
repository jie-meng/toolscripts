"""``agents-setup`` - install agent definitions to AI tool config directories."""

from __future__ import annotations

import argparse
import sys
from importlib import resources
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.ui_curses import select_many

from ._integrations import INTEGRATIONS, Integration

log = get_logger(__name__)


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


def _setup_one(integration: Integration, agents: list[dict]) -> None:
    log.info("setting up %s ...", integration.tool_name)
    if not integration.is_installed():
        log.warning("not detected, skipping")
        return

    target_dir = integration.get_agents_dir()
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
        out = integration.get_instructions_path()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        log.success("installed %s -> %s", integration.instructions_filename, out)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agents-setup",
        description="Install AI agent definitions into tool config directories.",
    )
    parser.add_argument("--all", "-a", action="store_true", help="all detected tools")
    parser.add_argument("--tool", "-t", help="setup a single tool by id")
    parser.add_argument("--list", "-l", action="store_true", help="list tools and agents")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    agents = _discover_agents()
    if not agents and not args.list:
        log.error("no agent definitions bundled - rebuild the package after adding files in data/ai/agents/")
        sys.exit(1)

    if args.list:
        log.info("Available AI Tools:")
        for integ in INTEGRATIONS:
            status = "installed" if integ.is_installed() else "not installed"
            print(f"  {integ.tool_id:<14} {integ.tool_name:<18} [{status}]")
        log.info("Available Agents:")
        for agent in agents:
            print(f"  - {agent['name']}: {agent['description']}")
        return

    if args.all:
        installed = [i for i in INTEGRATIONS if i.is_installed()]
        if not installed:
            log.warning("no installed AI tools detected")
            return
        for integ in installed:
            _setup_one(integ, agents)
        return

    if args.tool:
        for integ in INTEGRATIONS:
            if integ.tool_id == args.tool:
                _setup_one(integ, agents)
                return
        log.error("unknown tool: %s (use --list to see options)", args.tool)
        sys.exit(1)

    items: list[str] = []
    preselected: list[bool] = []
    disabled: set[int] = set()
    for i, integ in enumerate(INTEGRATIONS):
        if integ.is_installed():
            items.append(f"{integ.tool_name} (~/{integ.config_dir_name})")
            preselected.append(True)
        else:
            items.append(f"{integ.tool_name} (not installed)")
            preselected.append(False)
            disabled.add(i)

    indices = select_many(
        "Select AI tools to set up agents:",
        items,
        preselected=preselected,
        disabled=disabled,
    )
    if indices is None:
        log.warning("cancelled")
        return
    if not indices:
        log.info("no tools selected")
        return
    for idx in indices:
        _setup_one(INTEGRATIONS[idx], agents)


if __name__ == "__main__":
    main()
