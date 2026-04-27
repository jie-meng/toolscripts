"""``git-apply-patches`` - extract patches.zip and apply each .patch via git am."""

from __future__ import annotations

import argparse
import contextlib
import sys
import zipfile
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import run

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="git-apply-patches",
        description="Unzip patches.zip and apply each .patch with git am.",
    )
    parser.add_argument(
        "-i", "--input", default="patches.zip", help="patch zip file (default: patches.zip)"
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    archive = Path(args.input)
    if not archive.is_file():
        log.error("zip not found: %s", archive)
        sys.exit(1)

    cwd = Path.cwd()
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(cwd)

    patches = sorted(cwd.glob("*.patch"))
    if not patches:
        log.warning("no patches found in archive")
        return

    failed: list[Path] = []
    for p in patches:
        log.info("applying %s", p.name)
        try:
            with p.open("rb") as fh:
                run(["git", "am"], input=fh.read().decode("utf-8", errors="replace"))
        except Exception as exc:  # noqa: BLE001
            log.error("failed to apply %s: %s", p.name, exc)
            failed.append(p)

    for p in patches:
        with contextlib.suppress(OSError):
            p.unlink()
    with contextlib.suppress(OSError):
        archive.unlink()

    if failed:
        log.error("%d patch(es) failed to apply", len(failed))
        sys.exit(1)
    log.success("applied %d patches", len(patches))


if __name__ == "__main__":
    main()
