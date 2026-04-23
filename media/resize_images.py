#!/usr/bin/env python3
"""Resize images to target dimensions with suffix in filename."""
import argparse
import curses
import subprocess
import sys
from pathlib import Path

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"}

PRESETS = {
    "1": ("iPhone 14/15 Pro", 1242, 2688),
    "2": ("iPhone 14/15 Pro Max", 1290, 2796),
    "3": ("iPhone SE/8", 750, 1334),
    "4": ("iPad Pro 12.9", 2048, 2732),
    "5": ("iPad mini", 1488, 2266),
}


def find_images(directory: Path) -> list[Path]:
    images = []
    for ext in SUPPORTED_EXTENSIONS:
        images.extend(directory.glob(f"*{ext}"))
        images.extend(directory.glob(f"*{ext.upper()}"))
    return sorted(images)


def get_dimensions_from_directory(ref_dir: Path) -> tuple[int, int] | None:
    images = find_images(ref_dir)
    if not images:
        return None
    result = subprocess.run(
        ["magick", "identify", "-format", "%wx%h", str(images[0])],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    w, h = result.stdout.strip().split("x")
    return int(w), int(h)


def curses_single_select(
    stdscr,
    title: str,
    items: list[str],
) -> tuple[int, ...] | None:
    """Single-select curses UI. Returns selected index or None if cancelled."""
    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)

    cursor = 0
    total = len(items)

    def draw() -> None:
        try:
            stdscr.clear()
            stdscr.addstr(0, 0, title, curses.A_BOLD)
            stdscr.addstr(1, 0, "Up/Down move | Enter confirm | q quit", curses.color_pair(3))
            for i, item in enumerate(items):
                is_cursor = i == cursor
                marker = ">" if is_cursor else " "
                attr = curses.A_REVERSE if is_cursor else 0
                color = curses.color_pair(2) if is_cursor else 0
                stdscr.addstr(3 + i, 0, f"{marker} {item}", attr | color)
            stdscr.refresh()
        except curses.error:
            pass

    while True:
        draw()
        key = stdscr.getch()
        if key in (curses.KEY_UP, ord("k")):
            cursor = (cursor - 1) % total
        elif key in (curses.KEY_DOWN, ord("j")):
            cursor = (cursor + 1) % total
        elif key in (curses.KEY_ENTER, 10, 13):
            return (cursor,)
        elif key in (ord("q"), 27):
            return None


def interactive_select() -> tuple[int, int] | None:
    items = []
    for key, (name, w, h) in PRESETS.items():
        items.append(f"{name} ({w}x{h})")
    items.append("[c] Custom dimensions (e.g., 1233x999)")
    items.append("[r] Use reference directory")

    selected = curses.wrapper(curses_single_select, "Select target size:", items)
    if selected is None:
        return None

    idx = selected[0]
    if idx < len(PRESETS):
        name, w, h = list(PRESETS.values())[idx]
        return w, h
    elif idx == len(PRESETS):
        try:
            curses.curs_set(1)
            stdscr = curses.initscr()
            curses.echo()
            try:
                stdscr.addstr(0, 0, "Enter dimensions (WIDTHxHEIGHT): ")
                dims_input = stdscr.getstr(1, 0).decode("utf-8").strip()
            finally:
                curses.noecho()
                curses.endwin()
            parts = dims_input.split("x")
            if len(parts) != 2:
                return None
            w, h = int(parts[0]), int(parts[1])
            if w <= 0 or h <= 0:
                return None
            return w, h
        except Exception:
            return None
    else:
        ref_dir = input("Enter reference directory path: ").strip()
        ref_path = Path(ref_dir)
        if not ref_path.is_dir():
            print(f"Error: {ref_dir} is not a directory")
            return None
        dims = get_dimensions_from_directory(ref_path)
        if dims is None:
            print(f"Error: No images found in {ref_dir}")
            return None
        print(f"Using reference dimensions: {dims[0]}x{dims[1]}")
        return dims


def get_image_dimensions(image_path: Path) -> tuple[int, int] | None:
    result = subprocess.run(
        ["magick", "identify", "-format", "%wx%h", str(image_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    w, h = result.stdout.strip().split("x")
    return int(w), int(h)


def parse_stem_dims(stem: str) -> tuple[int, int] | None:
    """Parse WIDTHxHEIGHT from stem like 'photo_1920x1080'."""
    import re
    m = re.search(r"_(\d+)x(\d+)$", stem)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def resize_image(
    image_path: Path,
    target_dir: Path,
    width: int,
    height: int,
    add_suffix: bool = True,
    overwrite: bool = False,
) -> Path | None:
    current_dims = get_image_dimensions(image_path)
    if current_dims == (width, height):
        return None

    stem = image_path.stem
    dims_in_name = parse_stem_dims(stem)
    if dims_in_name == (width, height):
        return None

    if add_suffix:
        new_stem = f"{stem}_{width}x{height}"
    else:
        new_stem = stem

    output_path = target_dir / f"{new_stem}{image_path.suffix}"

    subprocess.run(
        [
            "magick",
            str(image_path),
            "-resize",
            f"{width}x{height}",
            "-background",
            "black",
            "-gravity",
            "center",
            "-extent",
            f"{width}x{height}",
            str(output_path),
        ],
        check=True,
    )

    if overwrite and output_path != image_path:
        image_path.unlink()

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Resize images to target dimensions")
    parser.add_argument(
        "input_dir",
        type=Path,
        nargs="?",
        help="Input directory (default: current directory)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        help="Output directory (default: same as input)",
    )
    parser.add_argument(
        "-r",
        "--reference",
        type=Path,
        help="Reference directory to get target dimensions from",
    )
    parser.add_argument(
        "-d",
        "--dimensions",
        help="Target dimensions in WIDTHxHEIGHT format (e.g., 1242x2688)",
    )
    parser.add_argument(
        "--no-suffix",
        action="store_true",
        help="Do not add dimensions suffix to output filename",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Interactive mode: show preset list",
    )
    parser.add_argument(
        "-w",
        "--overwrite",
        action="store_true",
        help="Overwrite source files",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress output",
    )

    args = parser.parse_args()

    if not args.input_dir and not args.interactive:
        parser.print_help()
        return

    input_dir = args.input_dir or Path(".")
    target_width, target_height = None, None

    if args.interactive:
        result = interactive_select()
        if result is None:
            print("Cancelled.")
            return
        target_width, target_height = result

    if not input_dir.is_dir():
        print(f"Error: {input_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    images = find_images(input_dir)
    if not images:
        print(f"No images found in {input_dir}", file=sys.stderr)
        sys.exit(1)

    if target_width is None:
        if args.dimensions:
            try:
                parts = args.dimensions.split("x")
                if len(parts) != 2:
                    raise ValueError()
                target_width, target_height = int(parts[0]), int(parts[1])
            except ValueError:
                print(
                    f"Error: Invalid dimensions format '{args.dimensions}'. Use WIDTHxHEIGHT",
                    file=sys.stderr,
                )
                sys.exit(1)
        elif args.reference:
            dims = get_dimensions_from_directory(args.reference)
            if dims is None:
                print(
                    f"Error: No images found in reference directory {args.reference}",
                    file=sys.stderr,
                )
                sys.exit(1)
            target_width, target_height = dims
        else:
            print("Error: Must specify --dimensions or --reference", file=sys.stderr)
            sys.exit(1)

    output_dir = args.output_dir or input_dir
    if not output_dir.exists():
        output_dir.mkdir(parents=True)

    for img in images:
        output_path = resize_image(
            img,
            output_dir,
            target_width,
            target_height,
            add_suffix=not args.no_suffix,
            overwrite=args.overwrite,
        )
        if output_path is None:
            continue
        if not args.quiet:
            action = "Overwrote" if args.overwrite else "Created"
            print(f"{action}: {output_path.name}")


if __name__ == "__main__":
    main()