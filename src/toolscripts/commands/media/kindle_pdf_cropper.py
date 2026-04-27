"""``kindle-pdf-cropper`` - split a PDF into JPGs, crop them, and merge back to PDF."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.prompts import ask
from toolscripts.core.shell import CommandNotFoundError, require, run

log = get_logger(__name__)


def _split_pdf_to_jpg(image_path: Path, base_name: str, src_pdf: Path) -> None:
    density = ask("density (e.g. 200; higher = sharper but slower)") or "200"
    if image_path.exists():
        shutil.rmtree(image_path)
    image_path.mkdir(parents=True)
    run(
        [
            "magick", "-quality", "100", "-density", density,
            str(src_pdf), str(image_path / f"{base_name}-%06d.jpg"),
        ]
    )


def _open_image_size(path: Path) -> tuple[int, int]:
    try:
        from PIL import Image  # type: ignore[import-not-found]
    except ImportError as exc:
        log.error("missing dependency: install with `pip install pillow`")
        raise SystemExit(1) from exc
    with Image.open(path) as img:
        return img.size


def _parse_offsets(raw: str) -> list[int] | None:
    parts = [p.strip() for p in raw.split(",")]
    if len(parts) != 4:
        return None
    try:
        return [int(p) for p in parts]
    except ValueError:
        return None


def _test_crop(image_path: Path, base_name: str, src_path: Path) -> None:
    raw = ask("offsets to crop (top,right,bottom,left)") or ""
    crops = _parse_offsets(raw)
    if crops is None:
        log.error("invalid input")
        sys.exit(1)
    raw_idx = ask("which image (e.g. 12 means the 12th jpg)") or "0"
    try:
        idx = int(raw_idx)
    except ValueError:
        log.error("not a valid integer")
        sys.exit(1)
    formatted = f"{idx:06d}"

    base_image = image_path / f"{base_name}-000000.jpg"
    width, height = _open_image_size(base_image)

    target = image_path / f"{base_name}-{formatted}.jpg"
    out = src_path / "test.jpg"
    geom = (
        f"{width - crops[3] - crops[1]}x{height - crops[0] - crops[2]}+{crops[3]}+{crops[0]}"
    )
    run(["magick", "-crop", geom, str(target), str(out)])
    log.success("test crop saved at %s", out)


def _resize_all(image_path: Path, base_name: str) -> None:
    raw = ask("offsets to crop (top,right,bottom,left)") or ""
    crops = _parse_offsets(raw)
    if crops is None:
        log.error("invalid input")
        sys.exit(1)

    base_image = image_path / f"{base_name}-000000.jpg"
    width, height = _open_image_size(base_image)
    geom = (
        f"{width - crops[3] - crops[1]}x{height - crops[0] - crops[2]}+{crops[3]}+{crops[0]}"
    )

    for jpg in image_path.iterdir():
        if jpg.suffix.lower() != ".jpg":
            continue
        run(["magick", "-crop", geom, str(jpg), str(jpg)])


def _merge_jpg_to_pdf(image_path: Path, base_name: str, src_path: Path) -> None:
    pattern = str(image_path / f"{base_name}*")
    output = src_path / f"{base_name}-kindle.pdf"
    run(["magick", pattern, str(output)])
    log.success("created %s", output)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="kindle-pdf-cropper",
        description=(
            "Interactive helper: split a PDF into JPGs, crop them with shared offsets, "
            "and merge back to a single PDF."
        ),
    )
    parser.add_argument("pdf", help="source PDF file")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        require("magick")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)

    src_pdf = Path(args.pdf).expanduser().resolve()
    if not src_pdf.is_file():
        log.error("file not found: %s", src_pdf)
        sys.exit(1)

    src_path = src_pdf.parent
    base_name = src_pdf.stem
    image_path = src_path / base_name

    print("Please select an action:")
    print("  1. splitPdf2Jpg")
    print("  2. testImageSize")
    print("  3. resizeAllImages")
    print("  4. mergeJpg2Pdf")
    try:
        sel = int(input("Choice: ").strip())
    except (ValueError, EOFError, KeyboardInterrupt):
        log.error("invalid selection")
        sys.exit(1)

    if sel == 1:
        _split_pdf_to_jpg(image_path, base_name, src_pdf)
    elif sel == 2:
        _test_crop(image_path, base_name, src_path)
    elif sel == 3:
        _resize_all(image_path, base_name)
    elif sel == 4:
        _merge_jpg_to_pdf(image_path, base_name, src_path)
    else:
        log.error("unknown selection")
        sys.exit(1)
    log.success("done")


if __name__ == "__main__":
    main()
