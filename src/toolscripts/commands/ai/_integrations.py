"""Shared registry of AI tool integrations used by ``agents-setup`` / ``agents-cleanup``."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Integration:
    tool_id: str
    tool_name: str
    config_dir_name: str
    instructions_filename: str = "AGENTS.md"

    def get_config_path(self) -> Path:
        return Path.home() / self.config_dir_name

    def is_installed(self) -> bool:
        return self.get_config_path().exists()

    def get_agents_dir(self) -> Path:
        return self.get_config_path() / "agents"

    def get_instructions_path(self) -> Path:
        return self.get_config_path() / self.instructions_filename


INTEGRATIONS: list[Integration] = [
    Integration("claude-code", "Claude Code", ".claude", "CLAUDE.md"),
    Integration("cursor", "Cursor", ".cursor", "AGENTS.md"),
    Integration("qwen", "Qwen", ".qwen", "QWEN.md"),
    Integration("copilot", "GitHub Copilot", ".copilot", "copilot-instructions.md"),
    Integration("opencode", "OpenCode", ".config/opencode", "AGENTS.md"),
    Integration("codex", "Codex", ".codex", "AGENTS.md"),
    Integration("gemini", "Gemini CLI", ".gemini", "GEMINI.md"),
    Integration("grok", "Grok CLI", ".grok", "AGENTS.md"),
]
