"""``android-cp-drawable`` - copy a drawable asset into the standard res/drawable-* tree."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.prompts import ask

log = get_logger(__name__)

_DENSITIES = ("hdpi", "mdpi", "xhdpi", "xxhdpi", "xxxhdpi")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="android-cp-drawable",
        description=(
            "Copy a drawable asset bundle (under ~/Downloads/<name>/drawable-*/) "
            "into ./app/src/main/res/drawable-*/."
        ),
    )
    parser.add_argument("name", nargs="?", help="folder name under ~/Downloads (prompted if omitted)")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    name = args.name or ask("Please input folder name under ~/Downloads")
    if not name:
        log.error("name required")
        sys.exit(1)

    source_root = Path.home() / "Downloads" / name
    if not source_root.is_dir():
        log.error("not a directory: %s", source_root)
        sys.exit(1)

    target_root = Path.cwd() / "app" / "src" / "main" / "res"
    if not target_root.is_dir():
        log.error("expected ./app/src/main/res to exist (run from project root)")
        sys.exit(1)

    for density in _DENSITIES:
        src_dir = source_root / f"drawable-{density}"
        if not src_dir.is_dir():
            continue
        targets = [p for p in src_dir.iterdir() if p.suffix == ".png"]
        if not targets:
            continue
        target_dir = target_root / f"drawable-{density}"
        target_dir.mkdir(parents=True, exist_ok=True)
        dst = target_dir / f"{name}.png"
        shutil.copy2(targets[0], dst)
        log.success("%s -> %s", targets[0], dst)

    log.success("done")


if __name__ == "__main__":
    main()
