"""``mermaid`` - friendly wrapper around the mermaid CLI (``mmdc``)."""

from __future__ import annotations

import argparse
import contextlib
import os
import sys
import uuid
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import CommandNotFoundError, require, run

log = get_logger(__name__)

_THEMES = {
    "1": ("default", "Default Theme"),
    "2": ("dark", "Dark Theme"),
    "3": ("forest", "Forest Theme"),
    "4": ("neutral", "Neutral Theme"),
}

_BACKGROUNDS = {
    "1": ("white", "White (default)"),
    "2": ("transparent", "Transparent"),
    "3": ("black", "Black"),
    "4": ("#F0F0F0", "Light Gray"),
    "5": ("red", "Red"),
}

_FORMATS = {
    "1": ("png", "PNG image"),
    "2": ("svg", "SVG vector"),
    "3": ("pdf", "PDF document"),
}


def _print_options(options: dict[str, tuple[str, str]], title: str) -> None:
    print(f"\n{title}:")
    for key, (value, desc) in options.items():
        print(f"  {key}. {desc} ({value})")


def _choose(options: dict[str, tuple[str, str]], default_key: str, prompt: str) -> str:
    while True:
        try:
            raw = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(130)
        if not raw:
            return options[default_key][0]
        if raw in options:
            return options[raw][0]
        log.warning("invalid choice. Use one of: %s", ", ".join(options.keys()))


def _run_mmdc(input_file: str, output_file: str, theme: str | None, background: str | None) -> bool:
    cmd = ["mmdc", "-i", input_file, "-o", output_file]
    if theme:
        cmd.extend(["-t", theme])
    if background:
        cmd.extend(["-b", background])
    log.info("running: %s", " ".join(cmd))
    try:
        run(cmd)
    except Exception as exc:  # noqa: BLE001
        log.error("mmdc failed: %s", exc)
        return False
    log.success("output: %s", output_file)
    return True


def _interactive(input_file: str) -> bool:
    path = Path(input_file)
    if not path.exists():
        log.error("input file not found: %s", input_file)
        return False
    output_name = input(f"\nOutput filename (default: {path.stem}): ").strip() or path.stem
    _print_options(_FORMATS, "Select output format")
    fmt = _choose(_FORMATS, "1", "Choose format (default: 1-PNG): ")
    output = f"{output_name}.{fmt}"
    _print_options(_THEMES, "Select theme")
    theme = _choose(_THEMES, "1", "Choose theme (default: 1-default): ")
    _print_options(_BACKGROUNDS, "Select background")
    background = _choose(_BACKGROUNDS, "1", "Choose background (default: 1-white): ")
    return _run_mmdc(input_file, output, theme, background)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mermaid",
        description="Interactive wrapper around the Mermaid CLI (`mmdc`).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input_file", nargs="?", help="input .mmd file")
    parser.add_argument("-o", "--output", help="output file with extension")
    parser.add_argument(
        "-t",
        "--theme",
        choices=("default", "dark", "forest", "neutral"),
        help="theme",
    )
    parser.add_argument("-b", "--background", help="background color")
    parser.add_argument(
        "-p",
        "--preview",
        action="store_true",
        help="quick preview using imgcat (then deletes the file)",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    if not args.input_file:
        parser.print_help()
        sys.exit(1)

    try:
        require("mmdc")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)

    input_path = Path(args.input_file)
    if not input_path.exists():
        log.error("input file not found: %s", args.input_file)
        sys.exit(1)

    if args.preview:
        output = f"{input_path.stem}_{uuid.uuid4()}.png"
        if not _run_mmdc(args.input_file, output, "default", "white"):
            sys.exit(1)
        try:
            run(["imgcat", output])
            log.success("displayed via imgcat")
        except Exception as exc:  # noqa: BLE001
            log.warning("imgcat failed: %s. Output kept at %s", exc, output)
            return
        with contextlib.suppress(OSError):
            os.remove(output)
        return

    if args.output and args.theme and args.background:
        if not _run_mmdc(args.input_file, args.output, args.theme, args.background):
            sys.exit(1)
        return

    if not _interactive(args.input_file):
        sys.exit(1)


if __name__ == "__main__":
    main()
