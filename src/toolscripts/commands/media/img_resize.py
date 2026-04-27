"""``img-resize`` - resize all images in a directory to target dimensions via ImageMagick."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import CommandNotFoundError, capture, require, run

log = get_logger(__name__)

SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"}

PRESETS: dict[str, tuple[str, int, int]] = {
    "1": ("iPhone 14/15 Pro", 1242, 2688),
    "2": ("iPhone 14/15 Pro Max", 1290, 2796),
    "3": ("iPhone SE/8", 750, 1334),
    "4": ("iPad Pro 12.9", 2048, 2732),
    "5": ("iPad mini", 1488, 2266),
}


def _find_images(directory: Path) -> list[Path]:
    found: set[Path] = set()
    for ext in SUPPORTED_EXTS:
        found.update(directory.glob(f"*{ext}"))
        found.update(directory.glob(f"*{ext.upper()}"))
    return sorted(found)


def _identify_dims(image: Path) -> tuple[int, int] | None:
    try:
        out = capture(["magick", "identify", "-format", "%wx%h", str(image)])
    except Exception:  # noqa: BLE001
        return None
    try:
        w, h = out.split("x")
        return int(w), int(h)
    except ValueError:
        return None


def _ref_dims(ref_dir: Path) -> tuple[int, int] | None:
    images = _find_images(ref_dir)
    if not images:
        return None
    return _identify_dims(images[0])


def _parse_stem_dims(stem: str) -> tuple[int, int] | None:
    m = re.search(r"_(\d+)x(\d+)$", stem)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def _resize_one(
    image: Path,
    target_dir: Path,
    width: int,
    height: int,
    *,
    add_suffix: bool,
    overwrite: bool,
) -> Path | None:
    current = _identify_dims(image)
    if current == (width, height):
        return None
    if _parse_stem_dims(image.stem) == (width, height):
        return None
    new_stem = f"{image.stem}_{width}x{height}" if add_suffix else image.stem
    output = target_dir / f"{new_stem}{image.suffix}"
    run(
        [
            "magick", str(image),
            "-resize", f"{width}x{height}",
            "-background", "black",
            "-gravity", "center",
            "-extent", f"{width}x{height}",
            str(output),
        ]
    )
    if overwrite and output != image and image.exists():
        image.unlink()
    return output


def _interactive_select() -> tuple[int, int] | None:
    options = [f"{name} ({w}x{h})" for name, w, h in PRESETS.values()]
    options.append("Custom dimensions (e.g., 1233x999)")
    options.append("Use reference directory")

    print("Select target size:")
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    try:
        raw = input("Choice: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    if not raw or not raw.isdigit():
        return None
    idx = int(raw) - 1
    presets = list(PRESETS.values())
    if 0 <= idx < len(presets):
        _, w, h = presets[idx]
        return w, h
    if idx == len(presets):
        try:
            dims = input("Enter dimensions (WIDTHxHEIGHT): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        try:
            w_str, h_str = dims.split("x")
            return int(w_str), int(h_str)
        except ValueError:
            return None
    if idx == len(presets) + 1:
        try:
            ref = input("Enter reference directory: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        ref_path = Path(ref)
        if not ref_path.is_dir():
            log.error("not a directory: %s", ref)
            return None
        return _ref_dims(ref_path)
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="img-resize",
        description="Resize images in a directory to target dimensions via ImageMagick.",
    )
    parser.add_argument("input_dir", nargs="?", help="input directory (default: cwd)")
    parser.add_argument("-o", "--output-dir", help="output directory (default: same as input)")
    parser.add_argument("-r", "--reference", help="reference directory to derive dimensions from")
    parser.add_argument(
        "-d", "--dimensions", help="target dimensions WIDTHxHEIGHT (e.g. 1242x2688)"
    )
    parser.add_argument(
        "--no-suffix", action="store_true", help="do not add the dimensions suffix"
    )
    parser.add_argument(
        "-i", "--interactive", action="store_true", help="interactive preset selector"
    )
    parser.add_argument(
        "-w", "--overwrite", action="store_true", help="overwrite source files"
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        require("magick")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        log.warning("install ImageMagick: https://imagemagick.org")
        sys.exit(1)

    if args.input_dir is None and not args.interactive:
        parser.print_help()
        return

    input_dir = Path(args.input_dir) if args.input_dir else Path()
    if not input_dir.is_dir():
        log.error("not a directory: %s", input_dir)
        sys.exit(1)

    target: tuple[int, int] | None = None
    if args.interactive:
        target = _interactive_select()
        if target is None:
            log.warning("cancelled")
            return

    if target is None:
        if args.dimensions:
            try:
                w_str, h_str = args.dimensions.split("x")
                target = int(w_str), int(h_str)
            except ValueError:
                log.error("invalid --dimensions: %s (expected WIDTHxHEIGHT)", args.dimensions)
                sys.exit(1)
        elif args.reference:
            target = _ref_dims(Path(args.reference))
            if target is None:
                log.error("no images found in reference directory %s", args.reference)
                sys.exit(1)
        else:
            log.error("must specify --dimensions, --reference, or --interactive")
            sys.exit(1)

    output_dir = Path(args.output_dir) if args.output_dir else input_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    images = _find_images(input_dir)
    if not images:
        log.error("no images found in %s", input_dir)
        sys.exit(1)

    width, height = target
    for image in images:
        result = _resize_one(
            image, output_dir, width, height,
            add_suffix=not args.no_suffix,
            overwrite=args.overwrite,
        )
        if result is None:
            continue
        action = "overwrote" if args.overwrite else "created"
        log.info("%s: %s", action, result.name)


if __name__ == "__main__":
    main()
