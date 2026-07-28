"""Shared data model and operations for agents-setup / agents-cleanup."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from toolscripts.core.log import get_logger

from .tools import AI_TOOLS, AITool

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InstallableItem:
    """One independently-selectable file that can be installed or removed."""

    tool_id: str
    tool_name: str
    category: str  # "instructions" or "agent"
    name: str
    relative_path: str
    source: Path


# ---------------------------------------------------------------------------
# Bundled data discovery
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


def _instructions_source() -> Path | None:
    base = _data_dir()
    if base is None:
        return None
    candidate = base / "AGENTS.md"
    return candidate if candidate.exists() else None


def _agents_dir() -> Path | None:
    base = _data_dir()
    if base is None:
        return None
    candidate = base / "agents"
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
# Tool helpers
# ---------------------------------------------------------------------------


def _tool_by_id(tool_id: str) -> AITool | None:
    for t in AI_TOOLS:
        if t.tool_id == tool_id:
            return t
    return None


# ---------------------------------------------------------------------------
# Build item list
# ---------------------------------------------------------------------------


def _build_items() -> list[InstallableItem]:
    agents = _discover_agents()
    inst_src = _instructions_source()
    items: list[InstallableItem] = []

    for tool in AI_TOOLS:
        if inst_src is not None:
            items.append(
                InstallableItem(
                    tool_id=tool.tool_id,
                    tool_name=tool.tool_name,
                    category="instructions",
                    name=tool.instructions_filename,
                    relative_path=tool.instructions_filename,
                    source=inst_src,
                )
            )
        for agent in agents:
            agent_name: str = agent["name"]
            items.append(
                InstallableItem(
                    tool_id=tool.tool_id,
                    tool_name=tool.tool_name,
                    category="agent",
                    name=agent_name,
                    relative_path=f"agents/{agent_name}.md",
                    source=agent["source_path"],
                )
            )
    return items


# ---------------------------------------------------------------------------
# State detection
# ---------------------------------------------------------------------------


def _item_installed(item: InstallableItem) -> bool:
    tool = _tool_by_id(item.tool_id)
    if tool is None:
        return False
    return (tool.get_config_path() / item.relative_path).exists()


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


def _setup_item(item: InstallableItem) -> None:
    tool = _tool_by_id(item.tool_id)
    if tool is None or not tool.is_installed():
        return
    target = tool.get_config_path() / item.relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(item.source.read_text(encoding="utf-8"), encoding="utf-8")


def _cleanup_item(item: InstallableItem) -> None:
    tool = _tool_by_id(item.tool_id)
    if tool is None:
        return
    target = tool.get_config_path() / item.relative_path
    if target.exists():
        target.unlink()


# ---------------------------------------------------------------------------
# Picker helpers
# ---------------------------------------------------------------------------

PICKER_INSTRUCTIONS_LABEL = "{tool_name} — {name} (instructions)"
PICKER_AGENT_LABEL = "{tool_name} — agent: {name}"


def _item_label(item: InstallableItem) -> str:
    if item.category == "instructions":
        return PICKER_INSTRUCTIONS_LABEL.format(tool_name=item.tool_name, name=item.name)
    return PICKER_AGENT_LABEL.format(tool_name=item.tool_name, name=item.name)


def make_picker(
    items: list[InstallableItem],
) -> tuple[list[str], list[bool], set[int]]:
    """Build (labels, preselected, disabled_indices) for select_many."""
    labels: list[str] = []
    preselected: list[bool] = []
    disabled: set[int] = set()
    for i, item in enumerate(items):
        tool = _tool_by_id(item.tool_id)
        installed = tool is not None and tool.is_installed()
        exists = _item_installed(item)
        labels.append(_item_label(item))
        preselected.append(exists)
        if not installed:
            disabled.add(i)
    return labels, preselected, disabled
