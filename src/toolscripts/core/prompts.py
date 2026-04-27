"""Interactive CLI prompts.

Thin wrappers over ``input()`` that handle EOF/Ctrl-C gracefully and apply
consistent formatting via :mod:`toolscripts.core.colors`.
"""

from __future__ import annotations

from collections.abc import Sequence

from toolscripts.core import colors


def ask(question: str, *, default: str | None = None) -> str | None:
    """Prompt the user for free-form text.

    Returns ``default`` (or None) on empty input or Ctrl-C / Ctrl-D.
    """
    suffix = f" [{default}]" if default is not None else ""
    prompt = colors.colored(f"{question}{suffix}: ", colors.CYAN)
    try:
        value = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    return value or default


def yes_no(question: str, *, default: bool = False) -> bool:
    """Prompt for a yes/no answer. Accepts y/yes/n/no (case-insensitive)."""
    hint = "Y/n" if default else "y/N"
    prompt = colors.colored(f"{question} ({hint}): ", colors.CYAN)
    while True:
        try:
            raw = input(prompt).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return default
        if not raw:
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print(colors.colored("  please answer y or n", colors.YELLOW))


def choice(
    question: str,
    options: Sequence[str],
    *,
    default: int | None = None,
) -> int | None:
    """Prompt the user to pick one option by number.

    Returns the zero-based index of the chosen option, or ``default``
    (or None) on cancel.
    """
    if not options:
        return default

    print(colors.colored(question, colors.CYAN))
    for i, opt in enumerate(options, 1):
        print(f"  {i}) {opt}")

    suffix = f" [{default + 1}]" if default is not None else ""
    prompt = colors.colored(f"choose 1-{len(options)}{suffix}: ", colors.CYAN)
    while True:
        try:
            raw = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return default
        if not raw:
            return default
        try:
            idx = int(raw) - 1
        except ValueError:
            print(colors.colored("  please enter a number", colors.YELLOW))
            continue
        if 0 <= idx < len(options):
            return idx
        print(colors.colored(f"  out of range (1-{len(options)})", colors.YELLOW))
