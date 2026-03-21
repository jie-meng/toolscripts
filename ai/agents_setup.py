#!/usr/bin/env python3
"""
Setup AI agents integration with AI tools (Claude Code, Cursor, etc.).

This script installs agent definitions from the agents/ directory
to various AI tool configuration directories.

Usage:
    python agents_setup.py           # Interactive mode
    python agents_setup.py --all     # Auto-setup all detected tools
    python agents_setup.py --tool claude-code  # Setup specific tool
    python agents_setup.py --list    # List available tools and agents
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def color_text(text: str, color: str) -> str:
    """Apply color to text."""
    return f"{color}{text}{RESET}"


def get_script_dir() -> Path:
    """Get the directory where this script is located."""
    return Path(__file__).parent.resolve()


def get_agents_dir() -> Path:
    """Get the agents directory path."""
    return get_script_dir() / "agents"


def get_instructions_source() -> Optional[Path]:
    """Get the source AGENTS.md (user-level coding principles) path."""
    path = get_script_dir() / "AGENTS.md"
    return path if path.exists() else None


def load_agent_definition(agent_path: Path) -> Optional[Dict]:
    """
    Load agent definition from a markdown file.

    The file should have YAML frontmatter with 'name' and 'description' fields.
    """
    if not agent_path.exists():
        return None

    content = agent_path.read_text(encoding="utf-8")

    # Parse YAML frontmatter
    if not content.startswith("---"):
        return None

    # Find the closing ---
    end_idx = content.find("\n---", 3)
    if end_idx == -1:
        return None

    frontmatter = content[3:end_idx].strip()
    body = content[end_idx + 4 :].strip()

    # Parse frontmatter into dict
    metadata = {}
    for line in frontmatter.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip().strip('"').strip("'")

    if "name" not in metadata:
        return None

    return {
        "name": metadata.get("name"),
        "description": metadata.get("description", ""),
        "model": metadata.get("model", "inherit"),
        "content": body,
        "source_path": agent_path,
    }


def discover_agents() -> List[Dict]:
    """Discover all agent definitions in the agents directory."""
    agents_dir = get_agents_dir()
    if not agents_dir.exists():
        return []

    agents = []
    for agent_file in agents_dir.glob("*.md"):
        agent = load_agent_definition(agent_file)
        if agent:
            agents.append(agent)

    return agents


class AIToolIntegration:
    """Base class for AI tool integrations."""

    tool_id: str = ""
    tool_name: str = ""
    config_dir_name: str = ""

    def get_config_path(self) -> Path:
        """Get the configuration directory path for this tool."""
        raise NotImplementedError

    def is_installed(self) -> bool:
        """Check if the AI tool is installed."""
        return self.get_config_path().exists()

    def get_tool_info(self) -> Tuple[str, str]:
        """Get tool ID and name."""
        return (self.tool_id, self.tool_name)

    def setup_agents(self, agents: List[Dict]) -> Tuple[bool, str]:
        """Setup agents for this tool. Returns (success, message)."""
        raise NotImplementedError


class BaseAgentsIntegration(AIToolIntegration):
    """Base class for tools that use ~/.<tool>/agents/ directory structure."""

    agents_subdir = "agents"
    instructions_filename = "AGENTS.md"

    def get_config_path(self) -> Path:
        return Path.home() / self.config_dir_name

    def get_instructions_path(self) -> Path:
        return self.get_config_path() / self.instructions_filename

    def setup_agents(self, agents: List[Dict]) -> Tuple[bool, str]:
        config_path = self.get_config_path()
        agents_dir = config_path / self.agents_subdir

        try:
            agents_dir.mkdir(parents=True, exist_ok=True)

            installed = []
            for agent in agents:
                agent_file = agents_dir / f"{agent['name']}.md"

                # Read original source file content
                source_content = agent["source_path"].read_text(encoding="utf-8")

                agent_file.write_text(source_content, encoding="utf-8")
                installed.append(agent["name"])

            return (True, f"{len(installed)} agents installed: {', '.join(installed)}")

        except Exception as e:
            return (False, f"Failed to setup: {str(e)}")

    def setup_instructions(self, source_path: Path) -> Tuple[bool, str]:
        """Deploy user-level instructions file (AGENTS.md / CLAUDE.md / etc.)."""
        config_path = self.get_config_path()
        target = self.get_instructions_path()

        try:
            config_path.mkdir(parents=True, exist_ok=True)
            content = source_path.read_text(encoding="utf-8")
            target.write_text(content, encoding="utf-8")
            return (True, f"Installed {self.instructions_filename} -> {target}")
        except Exception as e:
            return (False, f"Failed to install {self.instructions_filename}: {e}")


class ClaudeCodeIntegration(BaseAgentsIntegration):
    """Integration for Claude Code CLI."""

    tool_id = "claude-code"
    tool_name = "Claude Code"
    config_dir_name = ".claude"
    instructions_filename = "CLAUDE.md"


class CursorIntegration(BaseAgentsIntegration):
    """Integration for Cursor IDE."""

    tool_id = "cursor"
    tool_name = "Cursor"
    config_dir_name = ".cursor"
    instructions_filename = "AGENTS.md"


class QwenIntegration(BaseAgentsIntegration):
    """Integration for Qwen."""

    tool_id = "qwen"
    tool_name = "Qwen"
    config_dir_name = ".qwen"
    instructions_filename = "QWEN.md"


class OpencodeIntegration(BaseAgentsIntegration):
    """Integration for opencode."""

    tool_id = "opencode"
    tool_name = "OpenCode"
    config_dir_name = ".config/opencode"
    instructions_filename = "AGENTS.md"


class CopilotIntegration(BaseAgentsIntegration):
    """Integration for GitHub Copilot."""

    tool_id = "copilot"
    tool_name = "GitHub Copilot"
    config_dir_name = ".copilot"
    instructions_filename = "copilot-instructions.md"


# Registry of all integrations
INTEGRATIONS: List[AIToolIntegration] = [
    ClaudeCodeIntegration(),
    CursorIntegration(),
    QwenIntegration(),
    CopilotIntegration(),
    OpencodeIntegration(),
]


def print_header():
    """Print script header."""
    print(color_text("\n=== AI Agents Setup ===\n", BOLD))


def print_menu():
    """Print the tool selection menu."""
    print(color_text("Select AI tool to setup:", BOLD))

    for i, integration in enumerate(INTEGRATIONS, 1):
        tool_id, tool_name = integration.get_tool_info()
        if integration.is_installed():
            status = color_text("[Detected]", GREEN)
        else:
            status = color_text("[Not Detected]", YELLOW)
        print(f"  {i}. {tool_name} {status}")

    print(f"  0. {color_text('All (auto-detect installed tools)', BOLD)}")
    print()


def run_setup(integration: AIToolIntegration, agents: List[Dict]) -> None:
    """Run setup for a single integration."""
    tool_id, tool_name = integration.get_tool_info()
    config_path = integration.get_config_path()
    agents_dir = config_path / "agents"

    print(f"\n{color_text('Setting up', BOLD)} {tool_name}...")
    print(f"  Target directory: {agents_dir}")

    if not integration.is_installed():
        print(color_text(f"  {tool_name} not detected, skipping...", YELLOW))
        return

    success, message = integration.setup_agents(agents)

    if success:
        print(color_text(f"  ✓ {message}", GREEN))
        print(f"  Installed to: {agents_dir}")
    else:
        print(color_text(f"  ✗ {message}", RED))

    instructions_src = get_instructions_source()
    if instructions_src:
        ok, msg = integration.setup_instructions(instructions_src)
        if ok:
            print(color_text(f"  ✓ {msg}", GREEN))
        else:
            print(color_text(f"  ✗ {msg}", RED))


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Setup AI agents integration with AI tools"
    )
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Auto-setup all detected tools (non-interactive)",
    )
    parser.add_argument(
        "--tool",
        "-t",
        type=str,
        help="Setup specific tool by ID (e.g., claude-code, cursor)",
    )
    parser.add_argument(
        "--list", "-l", action="store_true", help="List available tools and agents"
    )
    return parser.parse_args()


def list_info(agents: List[Dict]) -> None:
    """List available tools and agents."""
    print(color_text("\nAvailable AI Tools:", BOLD))
    for integration in INTEGRATIONS:
        tool_id, tool_name = integration.get_tool_info()
        status = (
            color_text("[Detected]", GREEN)
            if integration.is_installed()
            else color_text("[Not Detected]", YELLOW)
        )
        print(f"  {tool_id}: {tool_name} {status}")

    print(color_text("\nAvailable Agents:", BOLD))
    for agent in agents:
        print(f"  - {agent['name']}: {agent['description']}")


def run_non_interactive(agents: List[Dict]) -> None:
    """Run setup in non-interactive mode (all detected tools)."""
    installed = [i for i in INTEGRATIONS if i.is_installed()]

    if not installed:
        print(color_text("No installed AI tools detected", RED))
        print("Please install one of the following tools first:")
        for integration in INTEGRATIONS:
            _, tool_name = integration.get_tool_info()
            print(f"  - {tool_name}")
        sys.exit(0)

    print(color_text(f"Detected {len(installed)} installed tool(s)", YELLOW))
    print("-" * 50)

    for integration in installed:
        run_setup(integration, agents)

    print("-" * 50)
    print(color_text("\n✓ Setup complete!", GREEN))


def run_interactive(agents: List[Dict]) -> None:
    """Run setup in interactive mode."""
    print_menu()

    try:
        user_input = input("Enter option (0-{}): ".format(len(INTEGRATIONS))).strip()

        if not user_input:
            print("Cancelled")
            sys.exit(0)

        option = int(user_input)

        if option == 0:
            run_non_interactive(agents)
        elif 1 <= option <= len(INTEGRATIONS):
            selected = INTEGRATIONS[option - 1]
            run_setup(selected, agents)
        else:
            print(
                color_text(f"Invalid option, please enter 0-{len(INTEGRATIONS)}", RED)
            )
            sys.exit(1)

    except ValueError:
        print(color_text("Please enter a valid number", RED))
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCancelled")
        sys.exit(0)


def main():
    """Main entry point."""
    args = parse_args()
    print_header()

    # Discover agents
    agents = discover_agents()

    if not agents:
        print(color_text("No agents found in agents/ directory", RED))
        sys.exit(1)

    print(f"Found {len(agents)} agent(s):")
    for agent in agents:
        desc = (
            agent["description"][:50] + "..."
            if len(agent["description"]) > 50
            else agent["description"]
        )
        print(f"  - {agent['name']}: {desc}")
    print()

    if args.list:
        list_info(agents)
        sys.exit(0)

    if args.all:
        run_non_interactive(agents)
        sys.exit(0)

    if args.tool:
        # Find tool by ID
        for integration in INTEGRATIONS:
            tool_id, _ = integration.get_tool_info()
            if tool_id == args.tool:
                run_setup(integration, agents)
                sys.exit(0)
        print(color_text(f"Unknown tool: {args.tool}", RED))
        print("Use --list to see available tools")
        sys.exit(1)

    # Interactive mode
    run_interactive(agents)


if __name__ == "__main__":
    main()
