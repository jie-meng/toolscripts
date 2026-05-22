"""``markdown`` - generate small markdown snippets (tables / task lists / mermaid)."""

from __future__ import annotations

import argparse

from toolscripts.core.clipboard import copy_to_clipboard
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.ui_curses import select_one

log = get_logger(__name__)


def _generate_table(rows: int, cols: int) -> str:
    header = "| " + " | ".join(f"Header{i + 1}" for i in range(cols)) + " |"
    separator = "| " + " | ".join("---" for _ in range(cols)) + " |"
    body = "\n".join(
        "| " + " | ".join(f"Cell{i + 1}{j + 1}" for j in range(cols)) + " |" for i in range(rows)
    )
    return "\n".join([header, separator, body])


_TASK_LIST = "- [x] Write the press release\n- [ ] Update the website\n- [ ] Contact the media"

_MERMAID = [
    """```mermaid
graph TD;
    A-->B;
    A-->C;
    B-->D;
    C-->D;
```""",
    """```mermaid
sequenceDiagram
    participant Alice
    participant Bob
    Alice->>John: Hello John, how are you?
    loop HealthCheck
        John->>John: Fight against hypochondria
    end
    Note right of John: Rational thoughts <br/>prevail!
    John-->>Alice: Great!
    John->>Bob: How about you?
    Bob-->>John: Jolly good!
```""",
    """```mermaid
gantt
dateFormat  YYYY-MM-DD
title Adding GANTT diagram to mermaid
excludes weekdays 2014-01-10

section A section
Completed task            :done,    des1, 2014-01-06,2014-01-08
Active task               :active,  des2, 2014-01-09, 3d
Future task               :         des3, after des2, 5d
Future task2              :         des4, after des3, 5d
```""",
    """```mermaid
classDiagram
Class01 <|-- AveryLongClass : Cool
Class03 *-- Class04
Class05 o-- Class06
Class07 .. Class08
Class09 --> C2 : Where am i?
Class09 --* C3
Class09 --|> Class07
Class07 : equals()
Class07 : Object[] elementData
Class01 : size()
Class01 : int chimp
Class01 : int gorilla
Class08 <--> C2: Cool label
```""",
]


def _emit(content: str) -> None:
    print(content)
    if copy_to_clipboard(content):
        log.success("copied to clipboard")
    else:
        log.warning("could not copy to clipboard")


def _table_flow() -> None:
    try:
        raw = input("Enter table dimensions (e.g. 3x5): ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    try:
        rows, cols = (int(p) for p in raw.split("x"))
    except ValueError:
        log.error("invalid format - use NxM (e.g. 3x5)")
        return
    _emit(_generate_table(rows, cols))


def _task_list_flow() -> None:
    _emit(_TASK_LIST)


def _mermaid_flow() -> None:
    items = ["Flowchart", "Sequence", "Gantt", "Class"]
    idx = select_one("Select mermaid diagram type", items)
    if idx is None:
        return
    _emit(_MERMAID[idx])


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="markdown",
        description="Generate small markdown snippets and copy them to the clipboard.",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    items = ["Table", "Task List", "Mermaid Diagram", "Exit"]
    while True:
        idx = select_one("Select snippet type", items)
        if idx is None or idx == 3:
            log.info("bye")
            return
        if idx == 0:
            _table_flow()
        elif idx == 1:
            _task_list_flow()
        elif idx == 2:
            _mermaid_flow()


if __name__ == "__main__":
    main()
