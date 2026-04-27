"""``agents-cleanup`` - remove agent definitions from AI tool config directories."""

from __future__ import annotations

import argparse
import shutil
import sys

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.ui_curses import multi_select

from ._integrations import INTEGRATIONS, Integration

log = get_logger(__name__)


def _has_agents(integ: Integration) -> int:
    d = integ.get_agents_dir()
    if not d.exists():
        return 0
    return sum(1 for _ in d.glob("*.md"))


def _has_instructions(integ: Integration) -> bool:
    return integ.get_instructions_path().exists()


def _has_anything(integ: Integration) -> bool:
    return _has_agents(integ) > 0 or _has_instructions(integ)


def _cleanup_one(integ: Integration) -> None:
    log.info("cleaning up %s ...", integ.tool_name)
    if not _has_anything(integ):
        log.info("nothing to clean")
        return

    parts: list[str] = []
    agents_dir = integ.get_agents_dir()
    if agents_dir.exists():
        count = _has_agents(integ)
        if count:
            shutil.rmtree(agents_dir)
            parts.append(f"removed {count} agent(s)")

    inst = integ.get_instructions_path()
    if inst.exists():
        inst.unlink()
        parts.append(f"removed {integ.instructions_filename}")

    if parts:
        log.success(", ".join(parts))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agents-cleanup",
        description="Remove installed AI agent definitions and instructions files.",
    )
    parser.add_argument("--all", "-a", action="store_true", help="cleanup all tools")
    parser.add_argument("--tool", "-t", help="cleanup a single tool by id")
    parser.add_argument("--list", "-l", action="store_true", help="list status")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    if args.list:
        for integ in INTEGRATIONS:
            agents = _has_agents(integ)
            inst = _has_instructions(integ)
            tags = []
            if agents:
                tags.append(f"{agents} agents")
            if inst:
                tags.append(integ.instructions_filename)
            status = ", ".join(tags) if tags else (
                "nothing installed" if integ.is_installed() else "not installed"
            )
            print(f"  {integ.tool_id:<14} {integ.tool_name:<18} [{status}]")
        return

    if args.all:
        for integ in INTEGRATIONS:
            if _has_anything(integ):
                _cleanup_one(integ)
        return

    if args.tool:
        for integ in INTEGRATIONS:
            if integ.tool_id == args.tool:
                _cleanup_one(integ)
                return
        log.error("unknown tool: %s", args.tool)
        sys.exit(1)

    items: list[str] = []
    preselected: list[bool] = []
    for integ in INTEGRATIONS:
        agents = _has_agents(integ)
        inst = _has_instructions(integ)
        tags = []
        if agents:
            tags.append(f"{agents} agent(s)")
        if inst:
            tags.append(integ.instructions_filename)
        if tags:
            items.append(f"{integ.tool_name} [{', '.join(tags)}]")
        elif integ.is_installed():
            items.append(f"{integ.tool_name} [nothing installed]")
        else:
            items.append(f"{integ.tool_name} [not installed]")
        preselected.append(False)

    indices = multi_select("Select AI tools to cleanup:", items, preselected=preselected)
    if indices is None:
        log.warning("cancelled")
        return
    if not indices:
        log.info("no tools selected")
        return
    for idx in indices:
        _cleanup_one(INTEGRATIONS[idx])


if __name__ == "__main__":
    main()
