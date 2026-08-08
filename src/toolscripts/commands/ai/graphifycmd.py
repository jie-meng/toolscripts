"""``graphifycmd`` - interactive browser for common ``graphify`` commands."""

from __future__ import annotations

import argparse
import contextlib
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from toolscripts.core.clipboard import copy_to_clipboard
from toolscripts.core.colors import GREEN, YELLOW, colored
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.platform import is_linux, is_macos, is_windows
from toolscripts.core.prompts import yes_no
from toolscripts.core.shell import run, which
from toolscripts.core.ui_curses import select_many, select_one

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
    """Bare CLI version (e.g. ``0.9.36``), matching the skill's ``.graphify_version``."""
    try:
        out = subprocess.check_output(
            ["graphify", "--version"], text=True, stderr=subprocess.DEVNULL
        )
        raw = out.strip()
        return raw.split()[-1] if raw else None
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
            return (PROJECT_ROOT / self.project_marker).exists()
        return False


_HOME = Path.home()

GRAPHIFY_PLATFORMS: list[_GraphifyPlatform] = [
    _GraphifyPlatform("claude-code", "claude", _HOME / ".claude" / "skills" / "graphify"),
    _GraphifyPlatform("cline", "cline", None, project_marker=".cline/rules/graphify.mdc"),
    _GraphifyPlatform("codebuddy", "codebuddy", _HOME / ".codebuddy" / "skills" / "graphify"),
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
    if plat.tool_id == "cline":
        # graphify has no native cline platform; the rule file is the integration
        _register_cline()
        return
    if _run_graphify("install", "--platform", plat.subcommand):
        log.success("graphify integration installed for %s", plat.subcommand)


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


# ── graphify-out gitignore policy (moved from ai-links) ─────────────────


GITIGNORE_FILE = ".gitignore"
GRAPHIFY_GITIGNORE_HEADER = "# graphify-out"

# Official graphify docs recommend committing graphify-out/ so the team
# shares the knowledge graph; the only per-user noise is the cost ledger and
# (optionally) the rebuild cache. Some repos (e.g. corporate) must not track
# generated output at all — that's the "ignore the whole dir" alternative,
# which is also the default when no policy is configured yet.
GRAPHIFY_ENTRY_IGNORE_ALL = "**/graphify-out/"
GRAPHIFY_IGNORE_DATES = "**/graphify-out/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]/"
# Canonical committed artifacts that are .json — a repo-wide `*.json` catch-all
# (common for config-heavy projects) would otherwise silently keep them out of
# git, defeating the commit policy. Negations are inert when no catch-all exists.
GRAPHIFY_COMMIT_ALLOWS = (
    "!**/graphify-out/graph.json",
    "!**/graphify-out/manifest.json",
    "!**/graphify-out/.graphify_labels.json",
    "!**/graphify-out/.graphify_analysis.json",
)
# Build-scratch files: the graphify skill's Step 9 cleanup removes
# detect/extract/ast/semantic after a completed build; a --update or watch
# run can leave them behind. .graphify_python is a machine-specific
# interpreter path and .pending_changes is the incremental-change queue —
# both are runtime state that must never reach git.
_GRAPHIFY_SCRATCH_ENTRIES = (
    "**/graphify-out/.graphify_detect.json",
    "**/graphify-out/.graphify_extract.json",
    "**/graphify-out/.graphify_ast.json",
    "**/graphify-out/.graphify_semantic.json",
    "**/graphify-out/.graphify_python",
    "**/graphify-out/.pending_changes",
)
GRAPHIFY_COMMIT_IGNORES = (
    "**/graphify-out/cost.json",
    "**/graphify-out/cache/",
    # per-rebuild rollback snapshots (duplicate graph.json + report); the
    # current graph in git is the real artifact, so the dated archive stays out
    GRAPHIFY_IGNORE_DATES,
    # transient rebuild lock (post-commit hook / watch); never commit it
    "**/graphify-out/.rebuild.lock",
    *_GRAPHIFY_SCRATCH_ENTRIES,
)
GRAPHIFY_STATE_COMMIT = "commit"
GRAPHIFY_STATE_IGNORE_ALL = "ignore_all"
GRAPHIFY_STATE_UNKNOWN = "unknown"
_GRAPHIFY_STATE_LABELS = {
    GRAPHIFY_STATE_IGNORE_ALL: "fully ignored (not committed)",
    GRAPHIFY_STATE_COMMIT: "committed (only cost.json + cache/ + dated snapshots ignored)",
    GRAPHIFY_STATE_UNKNOWN: "not configured yet",
}

# Entries old ai-links versions could have left anywhere in .gitignore —
# this feature now lives here, so applying a policy also cleans those up.
_LEGACY_GRAPHIFY_ENTRIES = (
    GRAPHIFY_ENTRY_IGNORE_ALL,
    "graphify-out/",
    *GRAPHIFY_COMMIT_IGNORES,
)


def _detect_graphify_gitignore() -> str:
    """Return the current graphify-out gitignore policy.

    A whole-directory ignore (``**/graphify-out/`` or ``graphify-out/``)
    wins as "ignore_all". Otherwise any ``graphify-out/cost.json`` /
    ``graphify-out/cache/`` entry implies "commit". Neither -> "unknown".
    """
    gitignore = PROJECT_ROOT / GITIGNORE_FILE
    if not gitignore.exists():
        return GRAPHIFY_STATE_UNKNOWN
    ignore_all = False
    commit = False
    for raw in gitignore.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line in (GRAPHIFY_ENTRY_IGNORE_ALL, "graphify-out/"):
            ignore_all = True
        elif "graphify-out/" in line and ("cost.json" in line or "cache/" in line):
            commit = True
    if ignore_all:
        return GRAPHIFY_STATE_IGNORE_ALL
    if commit:
        return GRAPHIFY_STATE_COMMIT
    return GRAPHIFY_STATE_UNKNOWN


def _prompt_graphify_policy(state: str) -> bool | None:
    """Ask the user how ``graphify-out/`` should appear in ``.gitignore``.

    Returns True to ignore the whole directory, False to commit it (ignoring
    only cost.json + cache/), or None if the user cancels. The current policy
    is highlighted on entry; unknown state defaults to ignoring everything.
    """
    default_ignore_all = state != GRAPHIFY_STATE_COMMIT
    items = [
        "Ignore graphify-out/ entirely (don't commit its output)",
        "Commit graphify-out/ to git (ignore only cost.json + cache/ + dated snapshots)",
    ]
    idx = select_one(
        f"graphify-out handling in .gitignore (currently: {_GRAPHIFY_STATE_LABELS[state]}):",
        items,
        default_index=0 if default_ignore_all else 1,
    )
    if idx is None:
        return None
    return idx == 0


def _apply_gitignore_policy(ignore_all: bool) -> None:
    """Rewrite the graphify-out block in ``.gitignore`` to match the policy."""
    gitignore = PROJECT_ROOT / GITIGNORE_FILE
    if not gitignore.exists():
        log.warning("%s not found; nothing to update", gitignore)
        return

    content = gitignore.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"\n*{re.escape(GRAPHIFY_GITIGNORE_HEADER)}\n(?:[^\n]*\n)*?(?=\n*(?:# |\Z))",
        re.MULTILINE,
    )
    cleaned = pattern.sub("\n", content)
    # Drop stale graphify-out entries left behind by old ai-links versions
    # (their block is otherwise untouched; ai-links cleans its own up).
    lines = [line for line in cleaned.splitlines() if line.strip() not in _LEGACY_GRAPHIFY_ENTRIES]
    cleaned = "\n".join(lines).strip("\n")

    entries = [GRAPHIFY_ENTRY_IGNORE_ALL] if ignore_all else [*GRAPHIFY_COMMIT_IGNORES, *GRAPHIFY_COMMIT_ALLOWS]
    block = "\n".join([GRAPHIFY_GITIGNORE_HEADER, *entries])
    new = (cleaned + "\n\n" if cleaned else "") + block + "\n"

    if new != content:
        gitignore.write_text(new, encoding="utf-8")
        state = GRAPHIFY_STATE_IGNORE_ALL if ignore_all else GRAPHIFY_STATE_COMMIT
        log.success("updated %s — %s", gitignore, _GRAPHIFY_STATE_LABELS[state])
    else:
        log.info("%s already matches the chosen policy", gitignore)


def _handle_gitignore_policy() -> None:
    state = _detect_graphify_gitignore()
    ignore_all = _prompt_graphify_policy(state)
    if ignore_all is None:
        log.warning("cancelled")
        return
    _apply_gitignore_policy(ignore_all)


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
        "The CLI itself is the 'graphify' command; the PyPI package is 'graphifyy'. "
        "After this, run 'Register with AI tools' to wire graphify into your editor, "
        "then 'Build graph (code only)' to create your first knowledge graph. "
        "Optional extras (PDF text extraction, faster-whisper transcription, "
        "Office .docx/.xlsx parsing, MCP server mode, Neo4j/FalkorDB push, ...) "
        "are available via 'graphifyy[all]'.",
        samples=["uv tool install graphifyy", "uv tool install 'graphifyy[all]'"],
        handler="install",
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
        name="Register with AI tools",
        category="setup",
        command="(interactive multi-select)",
        description="Wire graphify into your AI coding tools — the first step after installing. "
        "Auto-detects which agents are installed on this machine: tools whose graphify "
        "skill is missing or out of date are pre-checked for install/update, tools already "
        "up to date are left unchecked, and uninstalled agents are greyed out. "
        "Checked tools get installed/updated; unchecked ones are left untouched. "
        "Supports Claude Code, Cursor, Codex, Gemini, GitHub Copilot CLI, CodeBuddy, Cline, OpenCode.",
        samples=[],
        handler="register",
        needs_graphify=True,
    ),
    Action(
        name="Set graphify-out gitignore policy",
        category="setup",
        command="(interactive .gitignore edit)",
        description="Decide how graphify-out/ should appear in .gitignore: "
        "commit it (the official recommendation — ignore only cost.json + "
        "cache/ + the dated rollback snapshots) or ignore the whole directory "
        "(for repos that must not track generated output). "
        "The current policy is detected and pre-selected; when nothing is "
        "configured it defaults to ignoring the whole directory. "
        "Stale graphify-out entries left by old ai-links versions are cleaned up.",
        samples=[],
        handler="gitignore_policy",
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
        name="Watch folder & auto-rebuild",
        category="build",
        command="graphify watch {project}",
        description="Watch the project folder and rebuild the graph automatically "
        "whenever a file changes. Runs in the foreground until you press Ctrl+C. "
        "Handy while actively refactoring — the graph stays current without "
        "running update manually or waiting for a commit hook.",
        samples=["graphify watch {project}"],
        handler="watch",
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
        name="Label communities (LLM)",
        category="build",
        command="graphify label {project}",
        description="Give every community a descriptive name using the configured "
        "LLM backend (needs an API key). Unlike re-clustering, this only renames "
        "existing communities and regenerates GRAPH_REPORT.md — no re-clustering. "
        "Use when you built with --no-label or want better community names.",
        samples=["graphify label {project}", "graphify label {project} --missing-only"],
        handler="label",
        needs_graphify=True,
        needs_graph=True,
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
    Action(
        name="Open graph.html in browser",
        category="query",
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
        category="query",
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
    Action(
        name="Uninstall graphify",
        category="status",
        command="graphify uninstall",
        description="Remove graphify from every detected AI coding tool at once "
        "(skill files, hooks, AGENTS.md sections). Add --purge to also delete "
        "graphify-out/. Use when you no longer want graphify in this environment.",
        samples=["graphify uninstall", "graphify uninstall --purge"],
        handler="uninstall",
        needs_graphify=True,
    ),
]

_CATEGORY_LABELS = {
    "setup": "Setup",
    "build": "Build / Update",
    "hooks": "Git Hooks",
    "query": "Query / View",
    "status": "Status",
}

_CATEGORY_ORDER = ["setup", "build", "hooks", "query", "status"]


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


def _register_cline() -> None:
    """Write the graphify .mdc rule into Cline's rules directory.

    graphify has no native cline platform. Cline (a VS Code extension) reads
    Cursor-style .mdc rule files from ``.cline/rules/``, so we reuse the same
    always-apply rule the Cursor integration relies on.
    """
    rule_path = PROJECT_ROOT / ".cline" / "rules" / "graphify.mdc"
    rule_path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "---\n"
        "description: graphify knowledge graph context\n"
        "alwaysApply: true\n"
        "---\n\n"
        "This project has a graphify knowledge graph at graphify-out/.\n\n"
        "**MANDATORY: Before using Read, Grep, Glob, or search to explore the codebase, "
        "you MUST run graphify first:**\n"
        '- `graphify query "<question>"` — scoped subgraph for any codebase or architecture question\n'
        '- `graphify path "<A>" "<B>"` — dependency path between two symbols\n'
        '- `graphify explain "<concept>"` — all nodes related to a concept\n\n'
        "Only use Read/Grep/Glob directly when graphify has already oriented you and you "
        "need to modify or debug specific lines, or when graphify-out/graph.json does not exist yet.\n"
        "- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files.\n"
        "- After modifying code files, run `graphify update .` to keep the graph current "
        "(AST-only, no API cost).\n"
    )
    rule_path.write_text(content)
    log.success("graphify rule written for Cline: %s", rule_path)


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
        print("  To wire graphify into your assistant, paste this prompt into your")
        print("  AI coding tool (Claude Code, Cursor, Copilot, OpenCode, ...):")
        print()

        rule_prompt = (
            "Add a section to AGENTS.md / CLAUDE.md documenting the graphify "
            "knowledge graph for this project. It lives at graphify-out/graph.json "
            "(and graph.html). When answering code questions, query it first with "
            '`graphify query "..."`, `graphify path "A" "B"`, and '
            '`graphify explain "Concept"` instead of grepping files or reading '
            "code blindly. Run `graphify update .` after modifying code to keep the "
            "graph current (AST-only, no API cost). Explain the rules so future "
            "sessions auto-use the graph."
        )
        print(f"    {colored(rule_prompt, '', bold=True)}")
        print()

        try:
            if yes_no("Copy this prompt to the clipboard?", default=True):
                if copy_to_clipboard(rule_prompt):
                    log.success("prompt copied to clipboard")
                else:
                    log.error("could not copy to clipboard; copy it manually above")
        except (EOFError, KeyboardInterrupt):
            print()
    print()
    print(sep)
    print()


def _installed_skill_version(plat: _GraphifyPlatform) -> str | None:
    """Version of the installed graphify skill for ``plat``, if recorded.

    ``graphify install`` writes a ``.graphify_version`` file next to the
    skill; comparing it with the CLI version tells us whether the
    integration is stale. Project-rule platforms (cursor, cline) have no
    version file — they are either configured or not.
    """
    if plat.skill_path is None:
        return None
    vf = Path(plat.skill_path) / ".graphify_version"
    if not vf.is_file():
        return None
    try:
        return vf.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _handle_register() -> None:
    """Multi-select install/update of graphify integrations.

    Semantics: checked = act, unchecked = leave alone. The picker
    pre-checks tools that need action (not registered yet, or skill version
    behind the CLI) and leaves up-to-date ones unchecked, so re-running
    register never uninstalls anything by accident. Tools whose agent isn't
    installed on this machine are greyed out.
    """
    cli_version = _graphify_version()
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
            items.append(f"{integ.tool_name} (agent not installed)")
            preselected.append(False)
            disabled.add(len(items) - 1)
            continue
        if plat.tool_id == "cline":
            # Cline's integration is the project rule file — no version concept.
            rule_file = PROJECT_ROOT / ".cline" / "rules" / "graphify.mdc"
            if rule_file.is_file():
                items.append(f"{integ.tool_name} [up to date]")
                preselected.append(False)
            else:
                items.append(f"{integ.tool_name}")
                preselected.append(True)
            continue
        if plat.is_installed():
            skill_ver = _installed_skill_version(plat)
            if skill_ver is None or (cli_version and skill_ver == cli_version):
                items.append(f"{integ.tool_name} [up to date]")
                preselected.append(False)
            else:
                items.append(
                    f"{integ.tool_name} [update available: {skill_ver} → {cli_version or '?'}]"
                )
                preselected.append(True)
        else:
            items.append(f"{integ.tool_name}")
            preselected.append(True)

    indices = select_many(
        "Register graphify with AI tools (checked = install/update, unchecked = leave as-is):",
        items,
        preselected=preselected,
        disabled=disabled,
    )
    if indices is None:
        log.warning("cancelled")
        return

    for picker_idx in indices:
        tool_idx = platform_indices[picker_idx]
        plat = _PLATFORM_BY_ID[AI_TOOLS[tool_idx].tool_id]
        if plat.tool_id == "cline":
            _register_cline()
        else:
            _install_one(plat)


def _run_action(action: Action) -> None:
    h = action.handler
    if h == "install":
        run(["uv", "tool", "install", "graphifyy"])
    elif h == "upgrade":
        run(["uv", "tool", "upgrade", "graphifyy"])
    elif h == "register":
        _handle_register()
    elif h == "gitignore_policy":
        _handle_gitignore_policy()
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
    elif h == "watch":
        run(["graphify", "watch", str(PROJECT_ROOT)])
    elif h == "cluster_only":
        run(["graphify", "cluster-only", str(PROJECT_ROOT)])
    elif h == "label":
        run(["graphify", "label", str(PROJECT_ROOT)])
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
    elif h == "uninstall":
        run(["graphify", "uninstall"])


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

    # Cache CLI status — re-running the version subprocess on every keystroke
    # (the old behavior) made up/down navigation feel laggy.
    cli_state = {"version": _graphify_version(), "installed": _graphify_installed()}

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
        ver = cli_state["version"]
        if ver:
            status_parts.append(f"[{ver}]")
        if cli_state["installed"]:
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
                cli_state["version"] = _graphify_version()
                cli_state["installed"] = _graphify_installed()
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
        if args.upgrade or args.all or args.tool:
            log.error(
                "graphify CLI not found. Install it first:\n"
                "  uv tool install graphifyy\n"
                "  # or: pipx install graphifyy"
            )
            sys.exit(1)
        # The browser can still be useful without the CLI (Setup has the
        # install action; actions that need graphify are blocked on Enter).
        log.warning(
            "graphify CLI not found — install it from the Setup section (status bar shows [cli: X])"
        )

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
