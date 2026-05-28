"""``docs-pick`` - browse bundled documents in a curses tree and copy content to clipboard."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from toolscripts.core.clipboard import copy_to_clipboard
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

if TYPE_CHECKING:
    from toolscripts.core.ui_curses import DocNode

log = get_logger(__name__)


def _build_tree(root_path: Path) -> DocNode | None:
    """Build a DocNode tree from a directory on disk."""
    from toolscripts.core.ui_curses import DocNode

    if not root_path.is_dir():
        return None

    root = DocNode(root_path.name, is_dir=True)

    def _populate(parent: DocNode, dir_path: Path) -> None:
        entries = sorted(dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        for entry in entries:
            if entry.name.startswith("."):
                continue
            if entry.is_dir():
                child = DocNode(entry.name, is_dir=True, parent=parent)
                parent.children.append(child)
                _populate(child, entry)
            elif entry.suffix.lower() in (".md", ".txt", ".rst", ".org"):
                try:
                    content = entry.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    content = "(could not read file)"
                child = DocNode(entry.name, parent=parent, content=content)
                parent.children.append(child)

    _populate(root, root_path)
    return root if root.children else None


def _get_docs_dir() -> Path:
    """Return the bundled docs directory."""
    try:
        import importlib.resources as pkg_resources

        ref = pkg_resources.files("toolscripts.data").joinpath("docs")
        with pkg_resources.as_file(ref) as path:
            return Path(path)
    except (TypeError, FileNotFoundError):
        pass

    fallback = Path(__file__).resolve().parents[3] / "data" / "docs"
    if fallback.is_dir():
        return fallback

    return Path(__file__).resolve().parents[2] / "data" / "docs"


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="docs-pick",
        description=(
            "Browse bundled documents in an interactive curses tree viewer. "
            "Navigate with j/k, scroll preview with J/K, press Enter to copy "
            "the selected document to the clipboard."
        ),
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    docs_dir = _get_docs_dir()
    if not docs_dir.is_dir():
        log.error("docs directory not found at %s", docs_dir)
        sys.exit(1)

    root = _build_tree(docs_dir)
    if root is None:
        log.error("no documents found in %s", docs_dir)
        sys.exit(1)

    from toolscripts.core.ui_curses import browse_docs

    picked = browse_docs(
        title="docs",
        root=root,
        copy_to_clipboard=copy_to_clipboard,
    )

    if picked is None:
        return

    print(f"Copied: {picked.name}")


if __name__ == "__main__":
    main()
