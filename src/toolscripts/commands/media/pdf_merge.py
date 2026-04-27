"""``pdf-merge`` - merge all PDF files in a directory into a single result.pdf."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pdf-merge",
        description="Merge all .pdf files in a directory into a single PDF (alphabetical order).",
    )
    parser.add_argument(
        "directory", nargs="?", default=".", help="directory of PDFs (default: cwd)"
    )
    parser.add_argument(
        "-o", "--output", default="result.pdf", help="output filename (default: result.pdf)"
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        from pypdf import PdfWriter  # type: ignore[import-not-found]
    except ImportError:
        try:
            from PyPDF2 import PdfMerger as PdfWriter  # type: ignore[import-not-found, no-redef]
        except ImportError:
            log.error("missing dependency: install with `pip install pypdf`")
            sys.exit(1)

    directory = Path(args.directory).expanduser().resolve()
    if not directory.is_dir():
        log.error("not a directory: %s", directory)
        sys.exit(1)

    pdfs = sorted(p for p in directory.iterdir() if p.suffix.lower() == ".pdf")
    if not pdfs:
        log.warning("no PDFs found in %s", directory)
        return

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = directory / output_path

    writer = PdfWriter()
    for pdf in pdfs:
        if pdf.resolve() == output_path.resolve():
            continue
        log.info("appending %s", pdf.name)
        writer.append(str(pdf))
    writer.write(str(output_path))
    if hasattr(writer, "close"):
        writer.close()

    log.success("created %s with %d pages source files", output_path, len(pdfs))


if __name__ == "__main__":
    main()
