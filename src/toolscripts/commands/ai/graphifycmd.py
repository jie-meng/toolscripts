"""``graphifycmd`` - interactive browser for common ``graphify`` commands."""

from __future__ import annotations

import argparse
import contextlib
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from toolscripts.core.colors import GREEN, YELLOW, colored
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.platform import is_linux, is_macos, is_windows
from toolscripts.core.shell import run, which
from toolscripts.core.ui_curses import select_many

from .tools import AI_TOOLS

log = get_logger(__name__)

# Set at startup — the project directory where graphify-out/ lives (matches
# the path passed to ``graphify extract / graphify update``, default: cwd).
PROJECT_ROOT: Path = Path.cwd()


def _graphify_out() -> Path:
    return PROJECT_ROOT / "graphify-out"


def _graph_json_path() -> Path:
    return _graphify_out() / "graph.json"


def _graph_html_path() -> Path:
    return _graphify_out() / "graph.html"


# ── helpers ──────────────────────────────────────────────────────────────


def _is_project() -> bool:
    return (PROJECT_ROOT / "pyproject.toml").is_file()


def _graphify_installed() -> bool:
    return shutil.which("graphify") is not None


def _graphify_version() -> str | None:
    try:
        out = subprocess.check_output(
            ["graphify", "--version"], text=True, stderr=subprocess.DEVNULL
        )
        return out.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _graph_data() -> dict | None:
    p = _graph_json_path()
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _hooks_installed() -> bool:
    hook = PROJECT_ROOT / ".git/hooks/post-commit"
    if not hook.is_file():
        return False
    try:
        return "graphify" in hook.read_text()
    except OSError:
        return False


def _opencode_configured() -> bool:
    agents = PROJECT_ROOT / "AGENTS.md"
    if not agents.is_file():
        return False
    try:
        return "graphify" in agents.read_text().lower()
    except OSError:
        return False


def _project_name() -> str:
    try:
        if _is_project():
            import tomllib

            raw = (PROJECT_ROOT / "pyproject.toml").read_bytes()
            data = tomllib.load(raw)
            name: object = data.get("project", {}).get("name", "") or ""
            if name:
                return str(name)
        return PROJECT_ROOT.name
    except Exception:
        return PROJECT_ROOT.name


# ── platform management (port from graphify-setup) ───────────────────────


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
        if self.skill_path is not None:
            return self.skill_path.is_dir() or self.skill_path.is_file()
        if self.project_marker is not None:
            return Path(self.project_marker).exists()
        return False


_HOME = Path.home()

GRAPHIFY_PLATFORMS: list[_GraphifyPlatform] = [
    _GraphifyPlatform("claude-code", "claude", _HOME / ".claude" / "skills" / "graphify"),
    _GraphifyPlatform("codex", "codex", _HOME / ".agents" / "skills" / "graphify"),
    _GraphifyPlatform("copilot", "copilot", _HOME / ".copilot" / "skills" / "graphify"),
    _GraphifyPlatform("cursor", "cursor", project_marker=".cursor/rules/graphify.mdc"),
    _GraphifyPlatform("gemini", "gemini", _HOME / ".gemini" / "skills" / "graphify"),
    _GraphifyPlatform(
        "opencode", "opencode", _HOME / ".config" / "opencode" / "skills" / "graphify"
    ),
]

_PLATFORM_BY_ID: dict[str, _GraphifyPlatform] = {p.tool_id: p for p in GRAPHIFY_PLATFORMS}


def _run_graphify(*args: str) -> bool:
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
    if plat.skill_path is not None:
        if _run_graphify("install", "--platform", plat.subcommand):
            log.success("graphify skill installed for %s", plat.subcommand)
    else:
        log.warning("%s has no user-level skill path configured", plat.tool_id)


def _uninstall_one(plat: _GraphifyPlatform) -> None:
    target = plat.skill_path
    if target is not None:
        if target.is_dir():
            shutil.rmtree(target)
            log.success("removed graphify skill for %s: %s", plat.subcommand, target)
        elif target.is_file():
            target.unlink()
            log.success("removed graphify skill for %s: %s", plat.subcommand, target)
        else:
            log.info("graphify skill not found for %s (nothing to remove)", plat.subcommand)


def _list_platforms() -> None:
    log.info("Graphify platform status:")
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


# ── action definitions ──────────────────────────────────────────────────


@dataclass
class Action:
    """A browsable / executable graphify action."""

    name: str
    category: str
    command: str
    description: str
    samples: list[str]
    handler: str
    needs_graphify: bool = False
    needs_graph: bool = False


_ACTIONS: list[Action] = [
    # ── Setup ──
    Action(
        name="Install graphify (uv)",
        category="setup",
        command="uv tool install graphifyy",
        description="Install the graphify CLI tool using uv (recommended). "
        "After this, run 'Register with OpenCode' to wire graphify into your editor, "
        "then run 'Build graph' to create your first knowledge graph. "
        "The CLI itself is the 'graphify' command; the PyPI package is 'graphifyy'.",
        samples=["uv tool install graphifyy", "uv tool install 'graphifyy[all]'"],
        handler="install",
    ),
    Action(
        name="Install graphify (all extras)",
        category="setup",
        command="uv tool install 'graphifyy[all]'",
        description="Same as above but with all optional extras: PDF text extraction, "
        "video/audio transcription via faster-whisper, Office .docx/.xlsx parsing, "
        "MCP server mode, SVG export, Neo4j/FalkorDB database push, and more. "
        "Use this if you want everything in one shot.",
        samples=["uv tool install 'graphifyy[all]'"],
        handler="install_all",
    ),
    Action(
        name="Upgrade graphify",
        category="setup",
        command="uv tool upgrade graphifyy",
        description="Upgrade graphify to the latest version on PyPI. "
        "Run this periodically to get new features, bug fixes, and language grammar updates. "
        "If you installed via pipx instead of uv, use: pipx upgrade graphifyy",
        samples=["uv tool upgrade graphifyy"],
        handler="upgrade",
    ),
    Action(
        name="Register with OpenCode",
        category="setup",
        command="graphify install --platform opencode"
        " && graphify install --project --platform opencode",
        description="Wire graphify into OpenCode — both globally and for this project. "
        "Global: updates ~/.config/opencode/skills/graphify/SKILL.md "
        "(silences the version warning on every CLI run). "
        "Project: writes rules into AGENTS.md and installs a tool.execute.before plugin "
        "so the assistant queries the knowledge graph before grepping files or reading code. "
        "Run once after installing graphify.",
        samples=[
            "graphify install --platform opencode",
            "graphify install --project --platform opencode",
        ],
        handler="register_opencode",
        needs_graphify=True,
    ),
    Action(
        name="Register with Claude Code",
        category="setup",
        command="graphify install --platform claude" " && graphify claude install",
        description="Wire graphify into Claude Code — both globally and for this project. "
        "Global: updates ~/.claude/skills/graphify/SKILL.md. "
        "Project: writes rules into CLAUDE.md and installs a PreToolUse hook "
        "so Claude automatically queries the knowledge graph before reading files "
        "or running search commands. "
        "Run once after installing graphify.",
        samples=[
            "graphify install --platform claude",
            "graphify claude install",
        ],
        handler="register_claude",
        needs_graphify=True,
    ),
    Action(
        name="Register with Cursor",
        category="setup",
        command="graphify install --platform cursor"
        " && graphify install --project --platform cursor",
        description="Wire graphify into Cursor — both globally and for this project. "
        "Global: updates ~/.cursor/skills/graphify/ (if supported). "
        "Project: writes .cursor/rules/graphify.mdc so Cursor's AI assistant "
        "automatically queries the knowledge graph before reading files. "
        "Run once after installing graphify.",
        samples=[
            "graphify install --platform cursor",
            "graphify install --project --platform cursor",
        ],
        handler="register_cursor",
        needs_graphify=True,
    ),
    Action(
        name="Register with Copilot",
        category="setup",
        command="graphify install --platform copilot"
        " && graphify install --project --platform copilot",
        description="Wire graphify into GitHub Copilot CLI — both globally and for this project. "
        "Global: updates ~/.copilot/skills/graphify/SKILL.md. "
        "Project: writes rules into copilot-instructions.md so Copilot "
        "automatically queries the knowledge graph before reading files. "
        "Run once after installing graphify.",
        samples=[
            "graphify install --platform copilot",
            "graphify install --project --platform copilot",
        ],
        handler="register_copilot",
        needs_graphify=True,
    ),
    Action(
        name="Bulk manage all platforms",
        category="setup",
        command="(interactive multi-select)",
        description="Install or uninstall the graphify user-level skill for any AI coding tool. "
        "Select a tool to install graphify for it; deselect to uninstall. "
        "Tools without the underlying platform installed are greyed out. "
        "Supports: Claude Code, Cursor, Gemini CLI, Codex, GitHub Copilot CLI, OpenCode.",
        samples=[],
        handler="bulk_manage",
        needs_graphify=True,
    ),
    # ── Hooks ──
    Action(
        name="Install git hooks",
        category="hooks",
        command="graphify hook install",
        description="Set up automatic graph rebuilds on git commit. "
        "Installs a post-commit hook that runs 'graphify update' after every commit "
        "(AST-only, no API cost, takes a few seconds). "
        "Also sets up a post-checkout hook for branch switches, and a git merge driver "
        "that automatically union-merges graph.json when two devs commit in parallel. "
        "Run this once per project to keep the graph always up to date.",
        samples=["graphify hook install"],
        handler="hook_install",
        needs_graphify=True,
    ),
    Action(
        name="Uninstall git hooks",
        category="hooks",
        command="graphify hook uninstall",
        description="Remove the graphify git hooks and merge driver. "
        "The graph will no longer auto-rebuild on commit. "
        "Use this if you no longer want automatic updates, or before moving the project.",
        samples=["graphify hook uninstall"],
        handler="hook_uninstall",
        needs_graphify=True,
    ),
    Action(
        name="Check hook status",
        category="hooks",
        command="graphify hook status",
        description="Check whether graphify git hooks and merge driver "
        "are installed and working correctly. "
        "Shows which hooks are active and if the merge driver is configured. "
        "Use this to verify setup or debug hook issues.",
        samples=["graphify hook status"],
        handler="hook_status",
        needs_graphify=True,
    ),
    # ── Build / Update ──
    Action(
        name="Build graph (code only)",
        category="build",
        command="graphify extract {project} --code-only",
        description="Build a knowledge graph from your source code. "
        "Uses tree-sitter AST parsing — fully local, no API key needed, "
        "nothing leaves your machine. Scans all supported languages and extracts "
        "functions, classes, imports, calls, and inheritance relationships. "
        "Output: graphify-out/graph.json + graph.html. "
        "This is the first command to run after installing graphify.",
        samples=["graphify extract {project} --code-only"],
        handler="build_code_only",
        needs_graphify=True,
    ),
    Action(
        name="Build graph (full, needs API key)",
        category="build",
        command="graphify extract {project}",
        description="Full extraction including code, documentation (.md, .rst, .txt), "
        "PDFs, and images. Requires an API key for the semantic pass over non-code files. "
        "Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY before running. "
        "Use this when you want docs and images included in the knowledge graph.",
        samples=["ANTHROPIC_API_KEY=sk-... graphify extract {project}"],
        handler="build_full",
        needs_graphify=True,
    ),
    Action(
        name="Update graph (incremental)",
        category="build",
        command="graphify update {project}",
        description="Re-extract only files that changed since the last build. "
        "AST-only, no API cost. Use this after modifying code to refresh the graph "
        "without a full rebuild. Much faster than rebuilding from scratch. "
        "The git hooks run this automatically after every commit.",
        samples=["graphify update {project}"],
        handler="update",
        needs_graphify=True,
    ),
    Action(
        name="Re-cluster communities",
        category="build",
        command="graphify cluster-only {project}",
        description="Rerun community detection (Leiden algorithm) on the existing graph "
        "without re-extracting any files. Useful when you want to see different groupings: "
        "use --resolution 1.5 for finer-grained communities or 0.5 for coarser ones. "
        "Also regenerates GRAPH_REPORT.md with updated community labels.",
        samples=[
            "graphify cluster-only {project}",
            "graphify cluster-only {project} --resolution 1.5",
        ],
        handler="cluster_only",
        needs_graphify=True,
        needs_graph=True,
    ),
    Action(
        name="Global: register this project",
        category="global",
        command="graphify global add {graph_json} --as {project}",
        description="Register this project's graph.json into the global graph "
        "(~/.graphify/global-graph.json). "
        "The global graph lets you query across multiple repos at once. "
        "Use this after building the graph for each repo in your workspace.",
        samples=[
            "graphify global add ./graphify-out/graph.json --as my-project",
        ],
        handler="global_add",
        needs_graphify=True,
        needs_graph=True,
    ),
    Action(
        name="Global: list registered repos",
        category="global",
        command="graphify global list",
        description="Show all repos currently registered in the global graph. "
        "Lists repo tags, node counts, and when they were last updated.",
        samples=["graphify global list"],
        handler="global_list",
        needs_graphify=True,
    ),
    Action(
        name="Global: unregister a repo",
        category="global",
        command="graphify global remove <tag>",
        description="Remove a repo from the global graph by its tag. "
        "Use this when you no longer want a repo included in cross-repo queries.",
        samples=["graphify global remove my-project"],
        handler="global_remove",
        needs_graphify=True,
    ),
    # ── Query ──
    Action(
        name="Query the graph",
        category="query",
        command='graphify query "..."',
        description="Ask a natural-language question about your codebase. "
        "Returns a scoped subgraph of the most relevant nodes and edges. "
        "For example: 'how does auth connect to the database' or 'what modules depend on config'. "
        "Your assistant calls this automatically when you ask code questions — "
        "you only need to use it manually from the terminal.",
        samples=[
            'graphify query "how does auth connect to the database"',
            'graphify query "what depends on config"',
        ],
        handler="query",
        needs_graphify=True,
        needs_graph=True,
    ),
    Action(
        name="Find path between nodes",
        category="query",
        command='graphify path "A" "B"',
        description="Find the shortest connection path between two concepts in your codebase. "
        "Each hop shows how they relate and is tagged EXTRACTED (explicit in source, "
        "like an import or function call) or INFERRED (resolved by graphify, "
        "like a shared type or indirect reference). "
        "Useful for understanding unexpected dependencies or tracing data flow.",
        samples=['graphify path "Config" "Database"'],
        handler="path",
        needs_graphify=True,
        needs_graph=True,
    ),
    Action(
        name="Explain a node",
        category="query",
        command='graphify explain "Concept"',
        description="Show all connections for a single concept — degree count, "
        "source file location, which community it belongs to, and every edge "
        "with its confidence tag (EXTRACTED/INFERRED). "
        "Use this to quickly understand what a class, function, or module "
        "depends on and what depends on it.",
        samples=['graphify explain "RateLimiter"'],
        handler="explain",
        needs_graphify=True,
        needs_graph=True,
    ),
    # ── View / Serve ──
    Action(
        name="Open graph.html in browser",
        category="view",
        command="open {graph_html}",
        description="Open the interactive force-directed graph visualization "
        "in your default browser. You can click nodes to inspect them, filter "
        "by community color, search for specific symbols, and zoom/pan around "
        "the entire codebase map. Generated by 'Build graph' or 'Update graph'.",
        samples=[],
        handler="open_html",
        needs_graph=True,
    ),
    Action(
        name="Start MCP server",
        category="view",
        command="python -m graphify.serve {graph_json}",
        description="Expose the knowledge graph as an MCP (Model Context Protocol) "
        "server via stdio. Your editor/assistant can then query it through "
        "structured tool calls instead of text commands. "
        "The server runs until you press Ctrl+C. "
        "Also supports --transport http for team-wide access.",
        samples=["python -m graphify.serve {graph_json}"],
        handler="serve_mcp",
        needs_graphify=True,
        needs_graph=True,
    ),
    # ── Status ──
    Action(
        name="Check project status",
        category="status",
        command="(summary report)",
        description="Show a comprehensive overview of graphify setup for this project: "
        "whether the CLI is installed, whether graphify-out/ exists, how many "
        "nodes and edges the graph has, whether git hooks are active, and whether "
        "AGENTS.md has the graphify rules for your assistant.",
        samples=[],
        handler="status",
    ),
    Action(
        name="Benchmark token savings",
        category="status",
        command="graphify benchmark {graph_json}",
        description="Measure how much the knowledge graph reduces LLM context size "
        "compared to the naive approach (feeding raw source files). "
        "Shows: total tokens in codebase vs. subgraph tokens for typical queries, "
        "compression ratio, and estimated cost savings. "
        "Run this after building the graph to see concrete numbers.",
        samples=["graphify benchmark graphify-out/graph.json"],
        handler="benchmark",
        needs_graphify=True,
        needs_graph=True,
    ),
]

_CATEGORY_LABELS = {
    "setup": "Setup",
    "hooks": "Git Hooks",
    "build": "Build / Update",
    "global": "Global Graph",
    "query": "Query",
    "view": "View / Serve",
    "status": "Status",
}

_CATEGORY_ORDER = ["setup", "hooks", "build", "global", "query", "view", "status"]


def _display_items() -> list[tuple[str, int | None]]:
    """Flatten actions into a display list with non-selectable category headers."""
    items: list[tuple[str, int | None]] = []
    for cat in _CATEGORY_ORDER:
        items.append((_CATEGORY_LABELS[cat], None))
        for i, a in enumerate(_ACTIONS):
            if a.category == cat:
                items.append((f"  {a.name}", i))
    return items


def _fmt(s: str) -> str:
    """Interpolate ``{project}``, ``{graph_json}``, ``{graph_html}`` with resolved paths."""
    return (
        s.replace("{project}", str(PROJECT_ROOT))
        .replace("{graph_json}", str(_graph_json_path()))
        .replace("{graph_html}", str(_graph_html_path()))
    )


# ── text wrapping ───────────────────────────────────────────────────────


def _wrap(text: str, width: int) -> list[str]:
    if width <= 0:
        return []
    out: list[str] = []
    for raw_line in text.splitlines():
        if not raw_line.strip():
            out.append("")
            continue
        line = raw_line.rstrip()
        while len(line) > width:
            cut = line.rfind(" ", 0, width)
            if cut <= 0:
                cut = width
            out.append(line[:cut])
            line = line[cut:].lstrip()
        if line:
            out.append(line)
    return out


# ── interactive handlers ────────────────────────────────────────────────


def _handle_query() -> None:
    try:
        q = input("Enter your question: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    if not q:
        print("Cancelled.")
        return
    run(["graphify", "query", q])


def _handle_path() -> None:
    try:
        from_a = input("From (node A): ").strip()
        if not from_a:
            print("Cancelled.")
            return
        to_b = input("To (node B): ").strip()
        if not to_b:
            print("Cancelled.")
            return
    except (EOFError, KeyboardInterrupt):
        print()
        return
    run(["graphify", "path", from_a, to_b])


def _handle_explain() -> None:
    try:
        concept = input("Concept name: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    if not concept:
        print("Cancelled.")
        return
    run(["graphify", "explain", concept])


def _handle_open_html() -> None:
    html_path = _graph_html_path().resolve()
    if not html_path.is_file():
        print(f"No graph.html found at {_graph_html_path()}. Build the graph first.")
        return
    if is_macos():
        subprocess.run(["open", str(html_path)], check=True)
    elif is_linux():
        subprocess.run(["xdg-open", str(html_path)], check=True)
    elif is_windows():
        subprocess.run(["start", str(html_path)], shell=True, check=True)
    else:
        print(f"Open this in your browser:\n  file://{html_path}")


def _handle_status() -> None:
    print()
    sep = "=" * 52
    print(sep)
    print(f"  {colored('graphify - Project Status', '', bold=True)}")
    print(f"  {PROJECT_ROOT}")
    print(sep)
    print()

    ver = _graphify_version()
    if ver:
        print(f"  {colored(f'graphify CLI  {ver}', GREEN)}")
    else:
        print(f"  {colored('graphify CLI  not installed', YELLOW)}")
    print()

    gout = _graphify_out()
    if gout.is_dir():
        print(f"  {colored('graphify-out/', GREEN)}")
        gd = _graph_data()
        if gd is not None:
            nodes = len(gd.get("nodes", []))
            edges = len(gd.get("edges", []))
            print(f"  {colored(f'graph.json    {nodes} nodes, {edges} edges', GREEN)}")
        else:
            print(f"  {colored('graph.json    (unreadable)', YELLOW)}")
        if _graph_html_path().is_file():
            print(f"  {colored('graph.html', GREEN)}")
    else:
        print(f"  {colored('graphify-out/  not found', YELLOW)}")
    print()

    if _hooks_installed():
        print(f"  {colored('git hooks     post-commit', GREEN)}")
    else:
        print(f"  {colored('git hooks     not installed', YELLOW)}")
    print()

    if _opencode_configured():
        print(f"  {colored('AGENTS.md     graphify rules present', GREEN)}")
    else:
        print(f"  {colored('AGENTS.md     no graphify rules found', YELLOW)}")
    print()
    print(sep)
    print()


def _handle_bulk_manage() -> None:
    items: list[str] = []
    preselected: list[bool] = []
    disabled: set[int] = set()
    platform_indices: list[int] = []

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

    for picker_idx in selected:
        tool_idx = platform_indices[picker_idx]
        plat = _PLATFORM_BY_ID[AI_TOOLS[tool_idx].tool_id]
        _install_one(plat)

    for picker_idx, tool_idx in enumerate(platform_indices):
        if picker_idx not in selected:
            plat = _PLATFORM_BY_ID[AI_TOOLS[tool_idx].tool_id]
            if plat.is_installed():
                _uninstall_one(plat)


def _handle_global_add() -> None:
    graph_json = _graph_json_path()
    if not graph_json.is_file():
        print(f"No graph.json found at {graph_json}. Build the graph first.")
        return

    default_tag = _project_name()
    try:
        tag = input(f"Repo tag (default: {default_tag}): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    tag = tag or default_tag

    print(f"Registering {graph_json} as '{tag}' in global graph ...")
    run(["graphify", "global", "add", str(graph_json), "--as", tag], check=False)
    print()
    run(["graphify", "global", "list"], check=False)


def _handle_global_list() -> None:
    run(["graphify", "global", "list"], check=False)


def _handle_global_remove() -> None:
    try:
        result = subprocess.run(["graphify", "global", "list"], capture_output=True, text=True)
        print(result.stdout.strip() if result.stdout.strip() else "Global graph is empty.")
    except Exception:
        print("Could not list global graph.")

    try:
        tag = input("Repo tag to remove: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    if not tag:
        print("Cancelled.")
        return

    run(["graphify", "global", "remove", tag], check=False)


def _run_action(action: Action) -> None:
    h = action.handler
    if h == "install":
        run(["uv", "tool", "install", "graphifyy"])
    elif h == "install_all":
        run(["uv", "tool", "install", "graphifyy[all]"])
    elif h == "upgrade":
        run(["uv", "tool", "upgrade", "graphifyy"])
    elif h == "register_opencode":
        run(["graphify", "install", "--platform", "opencode"])
        run(["graphify", "install", "--project", "--platform", "opencode"], cwd=PROJECT_ROOT)
    elif h == "register_claude":
        run(["graphify", "install", "--platform", "claude"])
        run(["graphify", "claude", "install"], cwd=PROJECT_ROOT)
    elif h == "register_cursor":
        run(["graphify", "install", "--platform", "cursor"])
        run(["graphify", "install", "--project", "--platform", "cursor"], cwd=PROJECT_ROOT)
    elif h == "register_copilot":
        run(["graphify", "install", "--platform", "copilot"])
        run(["graphify", "install", "--project", "--platform", "copilot"], cwd=PROJECT_ROOT)
    elif h == "bulk_manage":
        _handle_bulk_manage()
    elif h == "hook_install":
        run(["graphify", "hook", "install"], cwd=PROJECT_ROOT)
    elif h == "hook_uninstall":
        run(["graphify", "hook", "uninstall"], cwd=PROJECT_ROOT)
    elif h == "hook_status":
        run(["graphify", "hook", "status"], cwd=PROJECT_ROOT)
    elif h == "build_code_only":
        run(["graphify", "extract", str(PROJECT_ROOT), "--code-only"])
    elif h == "build_full":
        run(["graphify", "extract", str(PROJECT_ROOT)])
    elif h == "update":
        run(["graphify", "update", str(PROJECT_ROOT)])
    elif h == "cluster_only":
        run(["graphify", "cluster-only", str(PROJECT_ROOT)])
    elif h == "global_add":
        _handle_global_add()
    elif h == "global_list":
        _handle_global_list()
    elif h == "global_remove":
        _handle_global_remove()
    elif h == "query":
        _handle_query()
    elif h == "path":
        _handle_path()
    elif h == "explain":
        _handle_explain()
    elif h == "open_html":
        _handle_open_html()
    elif h == "serve_mcp":
        run(["python", "-m", "graphify.serve", str(_graph_json_path())])
    elif h == "status":
        _handle_status()
    elif h == "benchmark":
        run(["graphify", "benchmark", str(_graph_json_path())])


# ── curses browser ──────────────────────────────────────────────────────


def _ensure_curses() -> None:
    try:
        import curses  # noqa: F401
    except ImportError:
        if sys.platform == "win32":
            log.error("curses not available on Windows; install: pip install windows-curses")
        else:
            log.error("curses not available on this Python build.")
        sys.exit(1)


def _run_curses(stdscr) -> None:
    import curses

    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_WHITE, -1)
    curses.init_pair(5, curses.COLOR_MAGENTA, -1)

    def cp(n: int) -> int:
        return curses.color_pair(n)

    items = _display_items()
    selectable = [i for i, (_, aidx) in enumerate(items) if aidx is not None]
    cursor_pos = 0
    top = 0

    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        if height < 16 or width < 60:
            stdscr.addstr(0, 0, "Terminal too small. Minimum: 60x16")
            stdscr.refresh()
            stdscr.getch()
            return

        preview_top = height - 13
        list_height = max(5, preview_top - 4)

        # title
        title = " graphifycmd - graphify command browser "
        stdscr.addstr(0, 0, title.center(width, " "), cp(1) | curses.A_BOLD)
        hint = "j/k: move  |  gg/G: top/bottom  |  Enter: execute  |  q: quit"
        stdscr.addstr(1, 0, hint[:width], cp(3))
        stdscr.hline(2, 0, curses.ACS_HLINE, width)

        current_display_idx = selectable[cursor_pos]
        current_action_idx = items[current_display_idx][1]
        action = _ACTIONS[current_action_idx]

        # scrolling
        visible_count = list_height
        if current_display_idx < top:
            top = current_display_idx
        elif current_display_idx >= top + visible_count:
            top = current_display_idx - visible_count + 1
        top = max(0, min(top, len(items) - visible_count))

        # render list with category headers
        for i in range(visible_count):
            idx = top + i
            if idx >= len(items):
                break
            text, act_idx = items[idx]
            is_selected = idx == current_display_idx

            if act_idx is None:
                with contextlib.suppress(curses.error):
                    stdscr.addstr(3 + i, 0, text[: width - 1], cp(5) | curses.A_BOLD)
            else:
                marker = ">" if is_selected else " "
                attr = curses.A_REVERSE if is_selected else 0
                color = cp(2) if is_selected else cp(4)
                with contextlib.suppress(curses.error):
                    stdscr.addstr(3 + i, 0, f" {marker} {text}"[: width - 1], attr | color)

        # preview pane
        stdscr.hline(preview_top - 1, 0, curses.ACS_HLINE, width)

        with contextlib.suppress(curses.error):
            stdscr.addstr(preview_top, 2, "Command:", cp(5) | curses.A_BOLD)
            cmd_text = _fmt(action.command)
            stdscr.addstr(preview_top + 1, 4, cmd_text[: width - 4], cp(2))

        desc_lines = _wrap(action.description, width - 8)
        with contextlib.suppress(curses.error):
            stdscr.addstr(preview_top + 3, 2, "Description:", cp(5) | curses.A_BOLD)
            for li, line in enumerate(desc_lines[:5]):
                stdscr.addstr(preview_top + 4 + li, 4, line[: width - 4], cp(4))

        sample_start = preview_top + 4 + min(len(desc_lines), 5) + 1
        if action.samples:
            with contextlib.suppress(curses.error):
                stdscr.addstr(sample_start, 2, "Examples:", cp(5) | curses.A_BOLD)
            for li, ex in enumerate(action.samples[:3]):
                with contextlib.suppress(curses.error):
                    stdscr.addstr(sample_start + 1 + li, 4, f"  $ {_fmt(ex)}"[: width - 4], cp(1))

        # status line
        status_parts = [f"  {cursor_pos + 1}/{len(selectable)}"]
        ver = _graphify_version()
        if ver:
            status_parts.append(f"[{ver}]")
        if _graphify_installed():
            status_parts.append("[cli: V]")
        else:
            status_parts.append("[cli: X]")
        if action.needs_graph:
            status_parts.append("[graph: V]" if _graph_json_path().is_file() else "[graph: X]")
        if _is_project():
            status_parts.append("[project]")
        # show project root if not cwd
        if Path.cwd() != PROJECT_ROOT:
            status_parts.append(str(PROJECT_ROOT))
        with contextlib.suppress(curses.error):
            stdscr.addstr(height - 1, 0, "  ".join(status_parts)[: width - 1], cp(3))

        stdscr.refresh()
        key = stdscr.getch()

        if key in (curses.KEY_UP, ord("k")):
            cursor_pos = max(0, cursor_pos - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            cursor_pos = min(len(selectable) - 1, cursor_pos + 1)
        elif key == ord("g"):
            k2 = stdscr.getch()
            if k2 == ord("g"):
                cursor_pos = 0
        elif key == ord("G"):
            cursor_pos = len(selectable) - 1
        elif key in (curses.KEY_ENTER, 10, 13):
            curses.endwin()
            sel_action = _ACTIONS[current_action_idx]
            if sel_action.needs_graphify and not _graphify_installed():
                print("graphify CLI not found. Install it first via the Setup section.")
            elif sel_action.needs_graph and not _graph_json_path().is_file():
                print(f"No graph found at {_graph_json_path()}. Build one first.")
            else:
                try:
                    _run_action(sel_action)
                except Exception as exc:
                    print(f"Error: {exc}")
            input("\nPress Enter to return...")
            curses.noecho()
            curses.cbreak()
            stdscr.keypad(True)
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_CYAN, -1)
            curses.init_pair(2, curses.COLOR_GREEN, -1)
            curses.init_pair(3, curses.COLOR_YELLOW, -1)
            curses.init_pair(4, curses.COLOR_WHITE, -1)
            curses.init_pair(5, curses.COLOR_MAGENTA, -1)
            stdscr.clearok(True)
            stdscr.refresh()
        elif key in (ord("q"), 27):
            break


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="graphifycmd",
        description="Interactive browser for common graphify commands with live preview.",
    )
    parser.add_argument(
        "dir",
        nargs="?",
        default=".",
        help="Project directory (where graphify-out/ lives or will be created). Default: cwd",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List graphify install status for all supported AI coding tools",
    )
    parser.add_argument(
        "--upgrade",
        "-u",
        action="store_true",
        help="Upgrade graphify to the latest version before entering the browser",
    )
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Install graphify for all detected AI coding tools",
    )
    parser.add_argument(
        "--tool",
        "-t",
        help="Install graphify for a single tool (e.g. claude-code, cursor, gemini, opencode)",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    if which("graphify") is None:
        log.error(
            "graphify CLI not found. Install it first:\n"
            "  uv tool install graphifyy && graphify install\n"
            "  # or: pipx install graphifyy && graphify install"
        )
        sys.exit(1)

    if args.upgrade:
        log.info("upgrading graphify via uv …")
        result = subprocess.run(
            ["uv", "tool", "upgrade", "graphifyy"], capture_output=True, text=True
        )
        if result.returncode == 0:
            output = (result.stdout + result.stderr).strip()
            if output:
                log.debug("%s", output)
            log.success("graphify upgraded")
        else:
            log.error(
                "uv tool upgrade failed (exit %d): %s",
                result.returncode,
                (result.stderr or result.stdout).strip(),
            )
            sys.exit(1)

    if args.list:
        _list_platforms()
        return

    if args.all:
        for integ in AI_TOOLS:
            plat = _PLATFORM_BY_ID.get(integ.tool_id)
            if plat is None:
                continue
            if integ.is_installed():
                _install_one(plat)
        return

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

    global PROJECT_ROOT
    PROJECT_ROOT = Path(args.dir).resolve()

    _ensure_curses()
    import curses

    def run(stdscr):
        _run_curses(stdscr)

    curses.wrapper(run)


if __name__ == "__main__":
    main()
