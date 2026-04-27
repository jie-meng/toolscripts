"""``json-format`` - read a JSON file, pretty-print it, save to ``*_format.<ext>``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.prompts import ask

log = get_logger(__name__)


def format_file(path: Path, *, indent: int = 4, sort_keys: bool = True) -> Path:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    formatted = json.dumps(data, indent=indent, sort_keys=sort_keys, ensure_ascii=False)
    out_path = path.with_name(f"{path.stem}_format{path.suffix}")
    out_path.write_text(formatted, encoding="utf-8")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="json-format",
        description="Format a JSON file with sorted keys and indentation.",
    )
    parser.add_argument("file", nargs="?", help="path to the JSON file (prompted if omitted)")
    parser.add_argument("--indent", type=int, default=4, help="indent level (default: 4)")
    parser.add_argument(
        "--no-sort", action="store_true", help="keep original key order instead of sorting"
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    raw = args.file or ask("Please enter the full path of the file")
    if not raw:
        log.error("no file provided")
        sys.exit(1)

    path = Path(raw).expanduser()
    if not path.is_file():
        log.error("file not found: %s", path)
        sys.exit(1)

    try:
        out_path = format_file(path, indent=args.indent, sort_keys=not args.no_sort)
    except json.JSONDecodeError as exc:
        log.error("invalid JSON in %s: %s", path, exc)
        sys.exit(1)
    except OSError as exc:
        log.error("could not write output: %s", exc)
        sys.exit(1)

    log.success("formatted JSON saved to: %s", out_path)


if __name__ == "__main__":
    main()
