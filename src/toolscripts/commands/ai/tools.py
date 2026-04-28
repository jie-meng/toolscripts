"""Shared registry of AI coding-tool integrations.

Single source of truth for every ``commands/ai/`` command that needs to know
where each AI tool keeps its config, what filename it reads at the repo
root, and how it discovers skills. When a vendor changes a path, you update
this file once and all of ``agents-setup``, ``agents-cleanup``, ``ai-links``
pick up the new behavior.

Layout: each tool is one ``AITool`` row in ``AI_TOOLS``. The fields split
cleanly into two scopes:

* **User-home scope** (``~/<config_dir_name>/...``) — used by
  ``agents-setup`` / ``agents-cleanup`` to install/remove the user-level
  ``AGENTS.md``-equivalent file and the per-tool ``agents/`` directory.
* **Repository scope** (project root + ``.<tool>/`` inside the repo) — used
  by ``ai-links`` to symlink the project's ``AGENTS.md`` and
  ``.agents/skills/`` into each tool's expected locations.

Both scopes live in the same row so we don't drift two parallel tables.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AITool:
    tool_id: str
    tool_name: str

    # ----- user-home scope (used by agents-setup / agents-cleanup) -----
    config_dir_name: str
    """Directory under ``~`` (e.g. ``.claude``, ``.config/opencode``)."""

    instructions_filename: str = "AGENTS.md"
    """Filename inside ``~/<config_dir_name>/`` that ``agents-setup`` writes
    the user-level instructions to. Most tools accept ``AGENTS.md``; Claude
    wants ``CLAUDE.md``, Gemini wants ``GEMINI.md``, etc."""

    # ----- repository scope (used by ai-links) -----
    repo_instructions_filename: str | None = None
    """Filename the tool looks for at the *repository root* in addition to,
    or instead of, ``AGENTS.md``. ``None`` means the tool already reads
    ``AGENTS.md`` natively, so ``ai-links`` doesn't create a root symlink.
    Set to e.g. ``CLAUDE.md`` for tools that *only* recognize their own
    filename."""

    repo_umbrella_dir: str | None = None
    """Path (relative to the repo root) that ``ai-links`` symlinks *whole*
    to the project's ``.agents/`` directory. Set this when the tool's
    config dir at the repo root is dedicated to that single tool — then
    one symlink (``.cursor -> .agents``, ``.claude -> .agents``, ...)
    exposes every shared resource (``agents/``, ``skills/``, ...) at once.

    When ``repo_umbrella_dir`` is set, ``repo_agents_dir`` and
    ``repo_skills_dir`` are ignored — the umbrella covers them. Leave it
    None for tools whose agents/skills directories live under a directory
    that the project may also use for other purposes (e.g. copilot's
    agents go under ``.github/``, which also holds GitHub Actions and
    issue templates — we can't shadow it)."""

    repo_agents_dir: str | None = None
    """Used only when ``repo_umbrella_dir`` is None. Path (relative to the
    repo root) where ``ai-links`` symlinks ``.agents/agents/`` to."""

    repo_skills_dir: str | None = None
    """Used only when ``repo_umbrella_dir`` is None. Path (relative to the
    repo root) where ``ai-links`` symlinks ``.agents/skills/`` to."""

    # ----- convenience accessors used by agents-setup / agents-cleanup -----
    def get_config_path(self) -> Path:
        return Path.home() / self.config_dir_name

    def is_installed(self) -> bool:
        return self.get_config_path().exists()

    def get_agents_dir(self) -> Path:
        return self.get_config_path() / "agents"

    def get_instructions_path(self) -> Path:
        return self.get_config_path() / self.instructions_filename


# Keep this list alphabetical by tool_id so diffs stay readable.
AI_TOOLS: list[AITool] = [
    AITool(
        "claude-code",
        "Claude Code",
        ".claude",
        "CLAUDE.md",
        repo_instructions_filename="CLAUDE.md",
        repo_umbrella_dir=".claude",
    ),
    AITool(
        "codex",
        "Codex",
        ".codex",
        repo_umbrella_dir=".codex",
    ),
    AITool(
        "copilot",
        "GitHub Copilot",
        ".copilot",
        # Copilot CLI uses ``$HOME/.copilot/copilot-instructions.md`` for
        # user-level instructions (NOT ``AGENTS.md`` — confirmed against
        # docs.github.com 2026 docs). At the repo root it reads ``AGENTS.md``
        # directly and discovers ``.agents/skills/`` natively, so ai-links
        # only needs to wire up the agents directory.
        "copilot-instructions.md",
        # NOTE: copilot's repo-level agents live in ``.github/agents``, NOT
        # ``.copilot/agents``. Since ``.github/`` also holds GitHub Actions
        # workflows, issue templates, etc., we *cannot* umbrella-link it —
        # use a per-subdir link instead.
        repo_agents_dir=".github/agents",
    ),
    AITool(
        "cursor",
        "Cursor",
        ".cursor",
        repo_umbrella_dir=".cursor",
    ),
    AITool(
        "gemini",
        "Gemini CLI",
        ".gemini",
        "GEMINI.md",
        repo_instructions_filename="GEMINI.md",
        repo_umbrella_dir=".gemini",
    ),
    AITool(
        "grok",
        "Grok CLI",
        ".grok",
        # Grok stores subagents inline in ``~/.grok/user-settings.json`` and
        # has no file-based skills system, so ai-links has nothing to link
        # for it. Listed here for completeness / agents-setup discoverability.
    ),
    AITool(
        "opencode",
        "OpenCode",
        ".config/opencode",
        # OpenCode reads ``AGENTS.md`` directly at the repo root and natively
        # discovers ``.agents/skills/``. Treating ``.agents/`` as its
        # standard layout means ai-links has nothing to link for it — no
        # need to fabricate ``.opencode/`` directories.
    ),
    AITool(
        "qwen",
        "Qwen",
        ".qwen",
        "QWEN.md",
        repo_instructions_filename="QWEN.md",
        repo_umbrella_dir=".qwen",
    ),
]
