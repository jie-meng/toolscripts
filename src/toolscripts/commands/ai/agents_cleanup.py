"""``agents-cleanup`` - remove installed AI agent definitions.

Item-level curses interface: currently-installed items are shown pre-selected.
Deselecting an item removes it. Nothing is installed — this command only
removes items the user explicitly deselects.
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
    make_picker,
)

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agents-cleanup",
        description="Remove installed AI agent definitions via a curses interface.",
    )
    parser.add_argument("--all", "-a", action="store_true", help="remove everything")
    parser.add_argument("--tool", "-t", help="remove all items for a specific tool by id")
    parser.add_argument("--list", "-l", action="store_true", help="list installed items and exit")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    items = _build_items()
    if not items:
        log.info("nothing to clean up")
        return

    if args.list:
        log.info("Currently installed items:")
        found = False
        for item in items:
            if _item_installed(item):
                print(f"  {_item_label(item)}")
                found = True
        if not found:
            print("  (none)")
        return

    if args.all:
        removed = 0
        for item in items:
            if _item_installed(item):
                _cleanup_item(item)
                log.success("removed %s", _item_label(item))
                removed += 1
        if removed:
            log.success("removed %d item(s)", removed)
        else:
            log.info("nothing to clean up")
        return

    if args.tool:
        from .tools import AI_TOOLS

        tool = None
        for t in AI_TOOLS:
            if t.tool_id == args.tool:
                tool = t
                break
        if tool is None:
            log.error("unknown tool: %s", args.tool)
            sys.exit(1)
        removed = 0
        for item in items:
            if item.tool_id == args.tool and _item_installed(item):
                _cleanup_item(item)
                log.success("removed %s", _item_label(item))
                removed += 1
        if removed:
            log.success("removed %d item(s) for %s", removed, args.tool)
        else:
            log.info("nothing installed for %s", args.tool)
        return

    _, preselected, disabled = make_picker(items)
    installed_indices = [i for i in range(len(items)) if preselected[i]]
    if not installed_indices:
        log.info("nothing installed to clean up")
        return

    installed_items = [items[i] for i in installed_indices]
    installed_labels = [_item_label(item) for item in installed_items]

    indices = select_many(
        "Select items to REMOVE (checked = keep, unchecked = remove):",
        installed_labels,
        preselected=[True] * len(installed_items),
    )
    if indices is None:
        log.warning("cancelled")
        return

    to_keep = set(indices)
    for idx, item in enumerate(installed_items):
        if idx not in to_keep:
            _cleanup_item(item)
            log.success("removed %s", _item_label(item))

    log.success("done")


if __name__ == "__main__":
    main()
