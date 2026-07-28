"""``agents-setup`` - install or remove agent definitions for AI tools.

Item-level curses interface: each instructions file and each sub-agent is
independently selectable. Installed items are pre-selected; deselecting an
item removes it.  Confirming applies both setup and cleanup in one pass.
"""

from __future__ import annotations

import argparse
import sys

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.ui_curses import select_many

from .agents_common import (
    _build_items,
    _cleanup_item,
    _item_installed,
    _item_label,
    _setup_item,
    _tool_by_id,
    make_picker,
)
from .tools import AI_TOOLS

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agents-setup",
        description="Install or remove AI agent definitions via a unified curses interface.",
    )
    parser.add_argument(
        "--all", "-a", action="store_true", help="install all items for all installed tools"
    )
    parser.add_argument("--tool", "-t", help="install all items for a specific tool by id")
    parser.add_argument("--list", "-l", action="store_true", help="list available items and exit")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    items = _build_items()
    if not items and not args.list:
        log.error("no items bundled — rebuild the package after adding files in data/ai/")
        sys.exit(1)

    if args.list:
        log.info("Available installable items:")
        for item in items:
            installed = _item_installed(item)
            print(f"  {'[installed]' if installed else '[     ]'}  {_item_label(item)}")
        return

    if args.all:
        installed_tools = [t for t in AI_TOOLS if t.is_installed()]
        if not installed_tools:
            log.warning("no installed AI tools detected")
            return
        for item in items:
            if _tool_by_id(item.tool_id) in installed_tools:
                _setup_item(item)
        return

    if args.tool:
        tool = _tool_by_id(args.tool)
        if tool is None:
            log.error("unknown tool: %s (use --list to see tools)", args.tool)
            sys.exit(1)
        if not tool.is_installed():
            log.warning("%s is not installed locally, skipping", args.tool)
            return
        for item in items:
            if item.tool_id == args.tool:
                _setup_item(item)
        return

    labels, preselected, disabled = make_picker(items)
    indices = select_many(
        "Select items to install (deselect to remove):",
        labels,
        preselected=preselected,
        disabled=disabled or None,
    )
    if indices is None:
        log.warning("cancelled")
        return

    selected = set(indices)

    for idx, item in enumerate(items):
        if idx in selected:
            _setup_item(item)
            log.success("installed %s", _item_label(item))
        elif preselected[idx]:
            _cleanup_item(item)
            log.success("removed %s", _item_label(item))

    log.success("done")


if __name__ == "__main__":
    main()
