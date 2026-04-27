"""``rm-meta`` - recursively delete Unity-style ``.meta`` files."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.prompts import yes_no

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="rm-meta",
        description="Recursively delete *.meta files (e.g. Unity).",
    )
    parser.add_argument("directory", nargs="?", default=".", help="directory (default: cwd)")
    parser.add_argument("-y", "--yes", action="store_true", help="delete without prompting")
    parser.add_argument(
        "-n", "--dry-run", action="store_true", help="only list found files"
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    root = Path(args.directory).expanduser()
    if not root.is_dir():
        log.error("not a directory: %s", root)
        sys.exit(1)

    files: list[Path] = []
    for dirpath, _dirs, names in os.walk(root):
        for name in names:
            if name.endswith(".meta"):
                files.append(Path(dirpath) / name)

    if not files:
        log.info("no .meta files found")
        return

    log.info("found %d .meta file(s)", len(files))
    if args.dry_run:
        for f in files:
            print(f"  {f}")
        return
    if not args.yes and not yes_no("delete these files?", default=False):
        log.info("cancelled")
        return

    for f in files:
        try:
            f.unlink()
        except OSError as exc:
            log.warning("could not delete %s: %s", f, exc)
    log.success("deleted %d file(s)", len(files))


if __name__ == "__main__":
    main()
