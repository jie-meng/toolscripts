"""``git-make-patches`` - run git format-patch on the last N commits and zip the result."""

from __future__ import annotations

import argparse
import contextlib
import shutil
import sys
import zipfile
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.prompts import ask
from toolscripts.core.shell import run

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="git-make-patches",
        description="Generate git patches for the last N commits and zip them as patches.zip.",
    )
    parser.add_argument(
        "-n", "--count", type=int, default=None, help="number of commits to patch (prompted if omitted)"
    )
    parser.add_argument(
        "-o", "--output", default="patches.zip", help="output zip file (default: patches.zip)"
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    count = args.count
    if count is None:
        raw = ask("How many commits to patch")
        if not raw:
            log.error("count required")
            sys.exit(1)
        try:
            count = int(raw)
        except ValueError:
            log.error("not a valid integer: %r", raw)
            sys.exit(1)

    output = Path(args.output)
    if output.exists():
        output.unlink()

    cwd = Path.cwd()
    for f in cwd.glob("*.patch"):
        f.unlink()

    log.info("running: git format-patch -%d", count)
    run(["git", "format-patch", f"-{count}"])

    patches = sorted(cwd.glob("*.patch"))
    if not patches:
        log.warning("no patches generated")
        return

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in patches:
            zf.write(p, arcname=p.name)
    for p in patches:
        with contextlib.suppress(OSError):
            p.unlink()

    log.success("created %s with %d patches", output, len(patches))
    if shutil.which("git") is None:
        log.warning("git not found on PATH; was the format-patch step skipped?")


if __name__ == "__main__":
    main()
