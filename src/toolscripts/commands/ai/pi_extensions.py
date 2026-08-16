"""``pi-extensions-setup`` - one-shot installer/remover for Pi extensions.

Detects which Pi extensions and MCP servers are already installed and shows
one curses picker per group. Installed items are pre-checked and tagged;
everything stays toggleable — checking an item installs it, unchecking an
installed item removes it. Each item's help text is shown at the bottom of
the picker as the cursor moves over it.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import run
from toolscripts.core.ui_curses import select_many_help

log = get_logger(__name__)

INSTALLED_TAG = "installed"
CONFIGURED_TAG = "configured"


@dataclass(frozen=True)
class Entry:
    """One installable item shown in the picker."""

    source: str  # npm spec, e.g. "npm:pi-subagents"
    package: str  # short display name
    help: str  # description shown in the picker footer


# The canonical set this script manages. Order is deliberate: infrastructure
# first, then UX helpers, then context/token optimizers, then power tools.
PI_EXTENSIONS: tuple[Entry, ...] = (
    Entry(
        "npm:pi-mcp-adapter",
        "pi-mcp-adapter",
        "MCP gateway: connects external MCP servers and exposes their tools to Pi (mcp/mcpScript).",
    ),
    Entry(
        "npm:pi-subagents",
        "pi-subagents",
        "Run child agents: single or parallel workflows for review, research, and implementation.",
    ),
    Entry(
        "npm:pi-web-access",
        "pi-web-access",
        "Web search, URL fetching, GitHub repo cloning, PDF extraction, and video analysis.",
    ),
    Entry(
        "npm:@ff-labs/pi-fff",
        "@ff-labs/pi-fff",
        "Fuzzy file & content search (fffind/ffgrep): fast, typo-tolerant lookup across the workspace.",
    ),
    Entry(
        "npm:@juicesharp/rpiv-ask-user-question",
        "@juicesharp/rpiv-ask-user-question",
        "Structured questionnaires the model can ask the user instead of guessing.",
    ),
    Entry(
        "npm:@juicesharp/rpiv-todo",
        "@juicesharp/rpiv-todo",
        "Live todo list overlay that survives /reload and conversation compaction.",
    ),
    Entry(
        "npm:context-mode",
        "context-mode",
        "Context-window saver: sandboxed execution, FTS5 knowledge base, intent-driven search (ctx_*).",
    ),
    Entry(
        "npm:@rohaquinlop/pi-deepseek-cache",
        "@rohaquinlop/pi-deepseek-cache",
        "DeepSeek prefix-cache optimization: date/CWD freeze, cache-friendly compaction, hit-rate stats.",
    ),
    Entry(
        "npm:pi-rtk-optimizer",
        "pi-rtk-optimizer",
        "Rewrites bash calls to the faster rtk command and compacts noisy tool output to save tokens.",
    ),
    Entry(
        "npm:@cortexkit/aft-pi",
        "@cortexkit/aft-pi",
        "Replaces read/write/edit/grep with a Rust backend: trigram/semantic search, LSP diagnostics.",
    ),
    Entry(
        "npm:@piotr-oles/pi-cwd",
        "@piotr-oles/pi-cwd",
        "Forces relative paths: blocks absolute paths under the working directory to save tokens.",
    ),
)


@dataclass(frozen=True)
class McpServer:
    """One MCP server entry written to the user-global mcp.json."""

    name: str
    help: str
    config: dict


MCP_SERVERS: tuple[McpServer, ...] = (
    McpServer(
        "context7",
        "Up-to-date docs for popular libraries, fetched on demand - no stale offline docs.",
        {
            "type": "local",
            "command": ["npx", "-y", "@upstash/context7-mcp@latest"],
            "enabled": True,
        },
    ),
    McpServer(
        "playwright",
        "Browser automation: navigate, click, fill forms, and screenshot pages for testing.",
        {"type": "local", "command": ["npx", "@playwright/mcp@latest"], "enabled": True},
    ),
    McpServer(
        "chrome-devtools",
        "Chrome DevTools protocol: inspect DOM, network, console, and debug pages.",
        {"type": "local", "command": ["npx", "-y", "chrome-devtools-mcp@latest"], "enabled": True},
    ),
)


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def _agent_dir() -> Path:
    """Return Pi's agent directory (~/.pi/agent, or $PI_CODING_AGENT_DIR)."""
    override = __import__("os").environ.get("PI_CODING_AGENT_DIR")
    if override:
        return Path(override)
    return Path.home() / ".pi" / "agent"


def _read_settings_packages(agent_dir: Path) -> set[str]:
    """Return the ``packages`` list from Pi's settings.json (empty if absent)."""
    path = agent_dir / "settings.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    packages = data.get("packages") if isinstance(data, dict) else None
    if not isinstance(packages, list):
        return set()
    return {str(p) for p in packages}


def _pkg_installed(agent_dir: Path, entry: Entry, settings_sources: set[str]) -> bool:
    """An extension counts as installed when Pi loads it or npm has it on disk."""
    if entry.source in settings_sources:
        return True
    return (agent_dir / "npm" / "node_modules" / entry.package / "package.json").is_file()


def _mcp_config_paths() -> list[Path]:
    """User-global shared config, then Pi's agent-dir override."""
    return [Path.home() / ".config" / "mcp" / "mcp.json", _agent_dir() / "mcp.json"]


def _mcp_target() -> Path:
    """Where this script writes MCP servers (the user-global shared config)."""
    return Path.home() / ".config" / "mcp" / "mcp.json"


def _mcp_configured(name: str) -> bool:
    for path in _mcp_config_paths():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        servers = data.get("mcpServers") if isinstance(data, dict) else None
        if isinstance(servers, dict) and name in servers:
            return True
    return False


# ---------------------------------------------------------------------------
# Picker inputs
# ---------------------------------------------------------------------------


def _picker_inputs(
    names: list[str], installed: set[int]
) -> tuple[list[str], list[bool], list[str | None]]:
    """Build select_many_help inputs: installed items pre-checked and tagged.

    Everything stays toggleable: unchecking an installed item means "remove",
    checking an uninstalled item means "install".
    """
    preselected = [i in installed for i in range(len(names))]
    tags = [INSTALLED_TAG if i in installed else None for i in range(len(names))]
    return names, preselected, tags


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------


def _install_extension(entry: Entry) -> bool:
    pi = shutil.which("pi")
    if not pi:
        log.error("pi not found on PATH - cannot install %s", entry.source)
        return False
    try:
        run([pi, "install", entry.source])
    except subprocess.CalledProcessError as exc:
        log.error("failed to install %s (exit %s)", entry.source, exc.returncode)
        return False
    log.success("installed %s", entry.package)
    return True


def _remove_extension(entry: Entry) -> bool:
    pi = shutil.which("pi")
    if not pi:
        log.error("pi not found on PATH - cannot remove %s", entry.source)
        return False
    try:
        run([pi, "remove", entry.source])
    except subprocess.CalledProcessError as exc:
        log.error("failed to remove %s (exit %s)", entry.source, exc.returncode)
        return False
    log.success("removed %s", entry.package)
    return True


def _write_mcp_config(target: Path, servers: dict[str, dict]) -> Path:
    """Merge ``servers`` into ``target``, preserving any existing entries."""
    data: dict = {}
    if target.exists():
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
    servers_map = data.setdefault("mcpServers", {})
    servers_map.update(servers)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def _remove_mcp_servers(target: Path, names: list[str]) -> Path:
    """Remove the managed server names from ``target``; leave everything else."""
    if not target.exists():
        return target
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return target
    servers_map = data.get("mcpServers")
    if not isinstance(servers_map, dict):
        return target
    for name in names:
        servers_map.pop(name, None)
    if not servers_map:
        data.pop("mcpServers", None)
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print_list(agent_dir: Path, settings_sources: set[str]) -> None:
    print("Pi extensions:")
    for entry in PI_EXTENSIONS:
        installed = _pkg_installed(agent_dir, entry, settings_sources)
        mark = "[installed]" if installed else "[      ]"
        print(f"  {mark}  {entry.package}")
    print("MCP servers:")
    for server in MCP_SERVERS:
        mark = "[configured]" if _mcp_configured(server.name) else "[          ]"
        print(f"  {mark}  {server.name}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pi-extensions-setup",
        description="One-shot installer for Pi coding-agent extensions and MCP servers.",
    )
    parser.add_argument(
        "--all", "-a", action="store_true", help="install everything not yet installed, no UI"
    )
    parser.add_argument(
        "--list", "-l", action="store_true", help="list available items with install state and exit"
    )
    parser.add_argument(
        "--extensions-only", action="store_true", help="skip the MCP servers section"
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    agent_dir = _agent_dir()
    settings_sources = _read_settings_packages(agent_dir)

    if args.list:
        _print_list(agent_dir, settings_sources)
        return

    if not shutil.which("pi"):
        log.error(
            "pi not found on PATH - install the coding agent first, "
            "e.g. npm install -g @earendil-works/pi-coding-agent"
        )
        sys.exit(1)

    installed_ext = {
        i
        for i, entry in enumerate(PI_EXTENSIONS)
        if _pkg_installed(agent_dir, entry, settings_sources)
    }

    if args.all:
        for i, entry in enumerate(PI_EXTENSIONS):
            if i not in installed_ext:
                _install_extension(entry)
        if not args.extensions_only:
            missing = [s for s in MCP_SERVERS if not _mcp_configured(s.name)]
            if missing:
                target = _write_mcp_config(_mcp_target(), {s.name: s.config for s in missing})
                log.success("wrote %d MCP server(s) to %s", len(missing), target)
        log.success("done")
        return

    # Extension picker: checked = keep/install, unchecked = remove.
    names, preselected, tags = _picker_inputs([e.package for e in PI_EXTENSIONS], installed_ext)
    indices = select_many_help(
        "Pi extensions - Space toggles; Enter applies (checked=install, unchecked=remove):",
        names,
        [e.help for e in PI_EXTENSIONS],
        preselected=preselected,
        tags=tags,
    )
    if indices is None:
        log.warning("cancelled")
        return
    chosen = set(indices)
    for i, entry in enumerate(PI_EXTENSIONS):
        if i in chosen and i not in installed_ext:
            _install_extension(entry)
        elif i not in chosen and i in installed_ext:
            _remove_extension(entry)

    # MCP servers picker: checked = keep/add, unchecked = remove (managed only).
    if not args.extensions_only:
        mcp_configured = {i for i, s in enumerate(MCP_SERVERS) if _mcp_configured(s.name)}
        names, preselected, tags = _picker_inputs([s.name for s in MCP_SERVERS], mcp_configured)
        indices = select_many_help(
            "MCP servers (~/.config/mcp/mcp.json) - Space toggles; Enter applies:",
            names,
            [s.help for s in MCP_SERVERS],
            preselected=preselected,
            tags=tags,
        )
        if indices is not None:
            chosen = set(indices)
            target = _mcp_target()
            add = {MCP_SERVERS[i].name: MCP_SERVERS[i].config for i in chosen}
            if add:
                _write_mcp_config(target, add)
            remove = [
                MCP_SERVERS[i].name
                for i in range(len(MCP_SERVERS))
                if i in mcp_configured and i not in chosen
            ]
            if remove:
                _remove_mcp_servers(target, remove)
            if add or remove:
                log.success("updated MCP servers in %s", target)

    log.success("done")


if __name__ == "__main__":
    main()
