"""``extract-games`` - extract retro ROMs from zip archives into folders by extension."""

from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)

DIRECTORY_MAPPING = {
    ".nes": "nes",
    ".sfc": "snes",
    ".smc": "snes",
    ".n64": "n64",
    ".z64": "n64",
    ".gba": "gba",
    ".gbc": "gbc",
}
TARGET_EXTENSIONS = set(DIRECTORY_MAPPING.keys())


def _clean_filename(name: str) -> str:
    paren_en = name.find("(")
    paren_cn = name.find("（")
    pos = -1
    if paren_en != -1 and paren_cn != -1:
        pos = min(paren_en, paren_cn)
    elif paren_en != -1:
        pos = paren_en
    elif paren_cn != -1:
        pos = paren_cn
    if pos != -1:
        name = name[:pos]
    return name.rstrip().replace(" ", "_")


def _extract(zip_files: list[Path], cwd: Path) -> tuple[int, int]:
    for target_dir in DIRECTORY_MAPPING.values():
        (cwd / target_dir).mkdir(exist_ok=True)
    archives_processed = 0
    files_extracted = 0
    for zip_file in zip_files:
        log.info("processing %s", zip_file.name)
        zip_basename = zip_file.stem
        cleaned = _clean_filename(zip_basename)
        from_archive = 0
        try:
            with zipfile.ZipFile(zip_file, "r") as zf:
                for info in zf.filelist:
                    ext = Path(info.filename).suffix.lower()
                    if ext not in TARGET_EXTENSIONS:
                        continue
                    target_dir = cwd / DIRECTORY_MAPPING[ext]
                    target_path = target_dir / f"{cleaned}{ext}"
                    if target_path.exists():
                        log.warning(
                            "skipped: %s -> %s/%s (file exists)",
                            info.filename,
                            target_dir.name,
                            target_path.name,
                        )
                        continue
                    with zf.open(info) as src, target_path.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
                    log.success(
                        "extracted: %s -> %s/%s",
                        info.filename,
                        target_dir.name,
                        target_path.name,
                    )
                    from_archive += 1
        except (zipfile.BadZipFile, OSError) as exc:
            log.error("could not process %s: %s", zip_file, exc)
            continue
        if from_archive:
            archives_processed += 1
            files_extracted += from_archive
    return archives_processed, files_extracted


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="extract-games",
        description=(
            "Scan zip files in a directory, extract ROMs (.nes/.sfc/.gba/...) and "
            "categorize by file extension."
        ),
    )
    parser.add_argument(
        "directory", nargs="?", default=".", help="directory containing zip files"
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    cwd = Path(args.directory).expanduser().resolve()
    if not cwd.is_dir():
        log.error("not a directory: %s", cwd)
        sys.exit(1)

    zip_files = sorted(cwd.glob("*.zip"))
    if not zip_files:
        log.warning("no .zip files found in %s", cwd)
        return

    archives, files = _extract(zip_files, cwd)
    log.success(
        "done: %d archive(s) processed, %d file(s) extracted", archives, files
    )


if __name__ == "__main__":
    main()
