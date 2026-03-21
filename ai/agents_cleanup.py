#!/usr/bin/env python3
"""
Cleanup AI agents from various AI tool configuration directories.

Usage:
    python agents_cleanup.py           # Interactive mode
    python agents_cleanup.py --all     # Clean all tools
    python agents_cleanup.py --tool claude-code  # Clean specific tool
    python agents_cleanup.py --list    # List tools with agents status
"""

import argparse
import shutil
import sys
from pathlib import Path
from typing import List, Tuple

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def color_text(text: str, color: str) -> str:
    return f"{color}{text}{RESET}"


class AIToolIntegration:
    tool_id: str = ""
    tool_name: str = ""
    config_dir_name: str = ""

    def get_config_path(self) -> Path:
        return Path.home() / self.config_dir_name

    def is_installed(self) -> bool:
        return self.get_config_path().exists()

    def get_agents_dir(self) -> Path:
        return self.get_config_path() / "agents"

    def has_agents(self) -> bool:
        agents_dir = self.get_agents_dir()
        return agents_dir.exists() and any(agents_dir.glob("*.md"))

    def get_agent_count(self) -> int:
        agents_dir = self.get_agents_dir()
        if agents_dir.exists():
            return len(list(agents_dir.glob("*.md")))
        return 0

    def get_tool_info(self) -> Tuple[str, str]:
        return (self.tool_id, self.tool_name)

    def cleanup(self) -> Tuple[bool, str]:
        agents_dir = self.get_agents_dir()
        if not agents_dir.exists():
            return (True, "No agents directory")
        try:
            count = self.get_agent_count()
            if count == 0:
                return (True, "No agents to clean")
            shutil.rmtree(agents_dir)
            return (True, f"Removed {count} agent(s)")
        except Exception as e:
            return (False, f"Failed: {str(e)}")


class ClaudeCodeIntegration(AIToolIntegration):
    tool_id = "claude-code"
    tool_name = "Claude Code"
    config_dir_name = ".claude"


class CursorIntegration(AIToolIntegration):
    tool_id = "cursor"
    tool_name = "Cursor"
    config_dir_name = ".cursor"


class QwenIntegration(AIToolIntegration):
    tool_id = "qwen"
    tool_name = "Qwen"
    config_dir_name = ".qwen"


class CopilotIntegration(AIToolIntegration):
    tool_id = "copilot"
    tool_name = "GitHub Copilot"
    config_dir_name = ".copilot"


class OpencodeIntegration(AIToolIntegration):
    tool_id = "opencode"
    tool_name = "OpenCode"
    config_dir_name = ".config/opencode"


INTEGRATIONS: List[AIToolIntegration] = [
    ClaudeCodeIntegration(),
    CursorIntegration(),
    QwenIntegration(),
    CopilotIntegration(),
    OpencodeIntegration(),
]


def print_header():
    print(color_text("\n=== AI Agents Cleanup ===\n", BOLD))


def print_menu():
    print(color_text("Select AI tool to cleanup:", BOLD))
    for i, integration in enumerate(INTEGRATIONS, 1):
        tool_id, tool_name = integration.get_tool_info()
        if integration.has_agents():
            count = integration.get_agent_count()
            status = color_text(f"[{count} agent(s)]", GREEN)
        elif integration.is_installed():
            status = color_text("[No agents]", YELLOW)
        else:
            status = color_text("[Not Installed]", RED)
        print(f"  {i}. {tool_name} {status}")
    print(f"  0. {color_text('All (cleanup all tools with agents)', BOLD)}")
    print()


def run_cleanup(integration: AIToolIntegration) -> None:
    tool_id, tool_name = integration.get_tool_info()
    agents_dir = integration.get_agents_dir()

    print(f"\n{color_text('Cleaning up', BOLD)} {tool_name}...")
    print(f"  Agents directory: {agents_dir}")

    if not integration.has_agents():
        print(color_text(f"  No agents to clean", YELLOW))
        return

    success, message = integration.cleanup()

    if success:
        print(color_text(f"  ✓ {message}", GREEN))
    else:
        print(color_text(f"  ✗ {message}", RED))


def parse_args():
    parser = argparse.ArgumentParser(description="Cleanup AI agents from AI tools")
    parser.add_argument("--all", "-a", action="store_true", help="Cleanup all tools")
    parser.add_argument("--tool", "-t", type=str, help="Cleanup specific tool")
    parser.add_argument("--list", "-l", action="store_true", help="List tools status")
    return parser.parse_args()


def list_status():
    print(color_text("\nTools with agents:", BOLD))
    for integration in INTEGRATIONS:
        tool_id, tool_name = integration.get_tool_info()
        if integration.has_agents():
            count = integration.get_agent_count()
            status = color_text(f"[{count} agent(s)]", GREEN)
        elif integration.is_installed():
            status = color_text("[No agents]", YELLOW)
        else:
            status = color_text("[Not Installed]", RED)
        print(f"  {tool_id}: {tool_name} {status}")


def run_all():
    cleaned = []
    for integration in INTEGRATIONS:
        if integration.has_agents():
            tool_id, tool_name = integration.get_tool_info()
            success, message = integration.cleanup()
            if success:
                cleaned.append(f"{tool_name}: {message}")
            else:
                print(color_text(f"  ✗ {tool_name}: {message}", RED))

    if cleaned:
        print(color_text("\n✓ Cleaned:", GREEN))
        for item in cleaned:
            print(f"  - {item}")
    else:
        print(color_text("No agents to clean", YELLOW))


def main():
    args = parse_args()
    print_header()

    if args.list:
        list_status()
        sys.exit(0)

    if args.all:
        run_all()
        sys.exit(0)

    if args.tool:
        for integration in INTEGRATIONS:
            if integration.tool_id == args.tool:
                run_cleanup(integration)
                sys.exit(0)
        print(color_text(f"Unknown tool: {args.tool}", RED))
        print("Use --list to see available tools")
        sys.exit(1)

    print_menu()
    try:
        user_input = input("Enter option (0-{}): ".format(len(INTEGRATIONS))).strip()
        if not user_input:
            print("Cancelled")
            sys.exit(0)
        option = int(user_input)
        if option == 0:
            run_all()
        elif 1 <= option <= len(INTEGRATIONS):
            run_cleanup(INTEGRATIONS[option - 1])
        else:
            print(color_text(f"Invalid option", RED))
            sys.exit(1)
    except ValueError:
        print(color_text("Please enter a valid number", RED))
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCancelled")
        sys.exit(0)


if __name__ == "__main__":
    main()
