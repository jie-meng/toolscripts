"""``toolscripts-list`` - list every registered toolscripts command, grouped by domain."""

from __future__ import annotations

import argparse
import importlib
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from importlib.metadata import PackageNotFoundError, entry_points
from typing import NamedTuple

from toolscripts.core import colors
from toolscripts.core.colors import colors_enabled
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)

_PACKAGE_PREFIX = "toolscripts.commands."
_UNKNOWN_DOMAIN = "misc"


class CommandInfo(NamedTuple):
    name: str
    domain: str
    target: str
    summary: str


def _parse_target(value: str) -> tuple[str, str] | None:
    """Split ``module:func`` into ``(module, func)``; return ``None`` on garbage."""
    module, _, func = value.partition(":")
    if not module or not func:
        return None
    return module, func


def _domain_of(module: str) -> str:
    """Extract the domain segment from a ``toolscripts.commands.<domain>.<mod>`` path."""
    if not module.startswith(_PACKAGE_PREFIX):
        return _UNKNOWN_DOMAIN
    rest = module[len(_PACKAGE_PREFIX) :]
    domain, _, _ = rest.partition(".")
    return domain or _UNKNOWN_DOMAIN


_DOC_MARKER_RE = re.compile(r"^\s*``[^`]+``(?:\s*[/,]\s*``[^`]+``)*\s*[-–—:]\s*")


def _summary_from_doc(doc: str | None) -> str:
    """Pull a one-line summary from a module/function docstring.

    Modules in this repo follow the convention::

        \"\"\"``cmd-name`` - short summary.\"\"\"

    A few modules ship multiple commands and use ``\"``a`` / ``b`` / ``c`` - ...\"``.
    We strip whatever leading ``markers`` and dash/colon are present so the
    result is just the human-readable description.
    """
    if not doc:
        return ""
    first = doc.strip().splitlines()[0].strip()
    return _DOC_MARKER_RE.sub("", first)


def _load_summary(module_path: str, func_name: str) -> str:
    """Import the target module and return its one-line summary, or ``""``."""
    try:
        module = importlib.import_module(module_path)
    except Exception as exc:  # noqa: BLE001
        log.debug("could not import %s: %s", module_path, exc)
        return ""

    summary = _summary_from_doc(module.__doc__)
    if summary:
        return summary

    func = getattr(module, func_name, None)
    return _summary_from_doc(getattr(func, "__doc__", None))


def _discover(*, with_summary: bool) -> list[CommandInfo]:
    """Enumerate every console-script entry point that targets this package."""
    try:
        eps = entry_points(group="console_scripts")
    except PackageNotFoundError:
        return []

    found: list[CommandInfo] = []
    for ep in eps:
        parsed = _parse_target(ep.value)
        if parsed is None:
            continue
        module_path, func_name = parsed
        if not module_path.startswith(_PACKAGE_PREFIX):
            continue
        domain = _domain_of(module_path)
        summary = _load_summary(module_path, func_name) if with_summary else ""
        found.append(CommandInfo(name=ep.name, domain=domain, target=ep.value, summary=summary))

    found.sort(key=lambda c: (c.domain, c.name))
    return found


def _group_by_domain(commands: list[CommandInfo]) -> dict[str, list[CommandInfo]]:
    grouped: dict[str, list[CommandInfo]] = defaultdict(list)
    for cmd in commands:
        grouped[cmd.domain].append(cmd)
    return grouped


def _filter(
    commands: list[CommandInfo],
    *,
    domain: str | None,
    search: str | None,
) -> list[CommandInfo]:
    filtered = commands
    if domain:
        wanted = domain.lower()
        filtered = [c for c in filtered if c.domain == wanted]
    if search:
        needle = search.lower()
        filtered = [c for c in filtered if needle in c.name.lower() or needle in c.summary.lower()]
    return filtered


def _help_text(command: CommandInfo) -> str:
    """Return ``<cmd> --help`` output, falling back to ``python -m <module>``."""
    env = {**__import__("os").environ, "NO_COLOR": "1"}

    cmd_path = shutil.which(command.name)
    if cmd_path is not None:
        try:
            result = subprocess.run(
                [cmd_path, "--help"],
                capture_output=True,
                text=True,
                env=env,
                timeout=10,
            )
            text = (result.stdout or result.stderr).strip()
            if text:
                return text
        except (subprocess.SubprocessError, OSError) as exc:
            log.debug("running %s --help failed: %s", command.name, exc)

    module_path = command.target.split(":", 1)[0]
    try:
        result = subprocess.run(
            [sys.executable, "-m", module_path, "--help"],
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
        text = (result.stdout or result.stderr).strip()
        if text:
            return text
    except (subprocess.SubprocessError, OSError) as exc:
        log.debug("python -m %s --help failed: %s", module_path, exc)

    return "(could not retrieve --help; try running the command directly.)"


def _run_interactive(commands: list[CommandInfo]) -> None:
    """Drill-down browser; print the picked command + help to the terminal."""
    from toolscripts.core.ui_curses import BrowseEntry, browse_commands

    entries = [BrowseEntry(name=c.name, group=c.domain, summary=c.summary) for c in commands]

    picked = browse_commands(
        title="toolscripts",
        entries=entries,
        detail_provider=lambda e: _help_text(next(c for c in commands if c.name == e.name)),
    )
    if picked is None:
        return

    chosen = next(c for c in commands if c.name == picked.name)
    use_color = colors_enabled(sys.stdout)

    def paint(text: str, color: str, *, bold: bool = False) -> str:
        if not use_color:
            return text
        prefix = (colors.BOLD if bold else "") + color
        return f"{prefix}{text}{colors.RESET}"

    print(paint(chosen.name, colors.GREEN, bold=True))
    if chosen.summary:
        print(paint(chosen.summary, colors.GREY))
    print()
    print(_help_text(chosen))


def _print_grouped(commands: list[CommandInfo], *, show_summary: bool) -> None:
    grouped = _group_by_domain(commands)
    use_color = colors_enabled(sys.stdout)

    def paint(text: str, color: str, *, bold: bool = False) -> str:
        if not use_color:
            return text
        prefix = (colors.BOLD if bold else "") + color
        return f"{prefix}{text}{colors.RESET}"

    name_width = max((len(c.name) for c in commands), default=0)

    first = True
    for domain in sorted(grouped):
        if not first:
            print()
        first = False
        header = f"{domain}  ({len(grouped[domain])})"
        print(paint(header, colors.CYAN, bold=True))
        for cmd in grouped[domain]:
            name_str = paint(cmd.name.ljust(name_width), colors.GREEN)
            if show_summary and cmd.summary:
                summary_str = paint(cmd.summary, colors.GREY)
                print(f"  {name_str}  {summary_str}")
            else:
                print(f"  {name_str}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="toolscripts-list",
        description=(
            "List every command registered by the toolscripts package, grouped by "
            "domain. Discovered dynamically from entry points — no static list to "
            "maintain."
        ),
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="open a curses browser: pick a domain, then a command, then see its --help",
    )
    parser.add_argument(
        "-d",
        "--domain",
        help="only list commands in this domain (e.g. git, android, media)",
    )
    parser.add_argument(
        "-s",
        "--search",
        help="case-insensitive substring filter on name and summary",
    )
    parser.add_argument(
        "--names-only",
        action="store_true",
        help="print just the command names, one per line (pipe-friendly)",
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="skip importing modules to fetch summaries (faster)",
    )
    parser.add_argument(
        "--count",
        action="store_true",
        help="only print totals: <total> commands across <N> domains",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    want_summary = not args.no_summary and not args.names_only and not args.count
    commands = _discover(with_summary=want_summary)
    if not commands:
        log.error(
            "no toolscripts commands found. is the package installed? " "try: ./manage.py install"
        )
        sys.exit(1)

    commands = _filter(commands, domain=args.domain, search=args.search)
    if not commands:
        log.warning("no commands matched the given filters")
        sys.exit(0)

    if args.interactive:
        _run_interactive(commands)
        return

    if args.count:
        domains = {c.domain for c in commands}
        print(f"{len(commands)} commands across {len(domains)} domains")
        return

    if args.names_only:
        for cmd in commands:
            print(cmd.name)
        return

    _print_grouped(commands, show_summary=want_summary)


if __name__ == "__main__":
    main()
