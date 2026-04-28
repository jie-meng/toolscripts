"""Core: pure utilities with no business logic.

Modules:
    log        - unified colored logger
    colors     - ANSI color helpers with tty/NO_COLOR awareness
    platform   - OS detection and require_platform()
    shell      - subprocess wrappers
    clipboard  - cross-platform clipboard
    prompts    - interactive CLI prompts (yes/no, choice, ask)
    ui_curses  - curses pickers: ``select_one`` (single), ``select_many``
                 (multi), and ``browse_commands`` (two-pane drill-down)
"""
