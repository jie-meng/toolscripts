"""``android-rename-project`` - rename an Android project's package across files and directories."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.prompts import ask

log = get_logger(__name__)

_TEMP_FOLDER = ".temp"


def _is_binary(path: Path) -> bool:
    try:
        from binaryornot.check import is_binary  # type: ignore[import-not-found]
    except ImportError:
        with path.open("rb") as fh:
            chunk = fh.read(8192)
        return b"\x00" in chunk
    return is_binary(str(path))


def _rreplace(s: str, old: str, new: str, count: int) -> str:
    parts = s.rsplit(old, count)
    return new.join(parts)


def _is_ignored(path: str) -> bool:
    return ".git" in path


def _walk_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for current_root, _dirs, files in os.walk(root):
        if _is_ignored(current_root):
            continue
        for fname in files:
            fpath = Path(current_root) / fname
            if not _is_ignored(str(fpath)):
                out.append(fpath)
    return out


def _walk_dirs(root: Path) -> list[Path]:
    out: list[Path] = []
    for current_root, dirs, _files in os.walk(root):
        if _is_ignored(current_root):
            continue
        for dname in dirs:
            dpath = Path(current_root) / dname
            if not _is_ignored(str(dpath)):
                out.append(dpath)
    return out


def _update_dir_tree(target: Path, src_part: str, dst_part: str) -> None:
    base = Path(_rreplace(str(target), os.sep + src_part, "", 1))
    src_prefix = src_part.split(os.sep)[0]
    temp = Path.cwd() / _TEMP_FOLDER
    shutil.rmtree(temp, ignore_errors=True)
    shutil.move(str(target), temp)
    shutil.rmtree(base / src_prefix, ignore_errors=True)
    shutil.move(str(temp), base / dst_part)
    shutil.rmtree(temp, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="android-rename-project",
        description="Replace an Android package name everywhere (text and directory tree).",
    )
    parser.add_argument("--old-package", help="old package name (prompted if omitted)")
    parser.add_argument("--new-package", help="new package name (prompted if omitted)")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    old_package = args.old_package or ask("old package")
    new_package = args.new_package or ask("new package")
    if not old_package or not new_package:
        log.error("both old-package and new-package are required")
        sys.exit(1)

    old_path = old_package.replace(".", os.sep)
    new_path = new_package.replace(".", os.sep)
    cwd = Path.cwd()

    files = _walk_files(cwd)
    log.info("scanning %d files", len(files))
    for file_path in files:
        try:
            if _is_binary(file_path):
                continue
            text = file_path.read_text(encoding="utf-8", errors="replace")
            updated = text.replace(old_package, new_package).replace(old_path, new_path)
            if updated != text:
                file_path.write_text(updated, encoding="utf-8")
        except OSError as exc:
            log.warning("could not update %s: %s", file_path, exc)

    for d in _walk_dirs(cwd):
        if str(d).endswith(old_path):
            _update_dir_tree(d, old_path, new_path)

    log.success("done")


if __name__ == "__main__":
    main()
