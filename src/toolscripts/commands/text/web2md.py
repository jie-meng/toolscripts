"""``web2md`` - fetch a webpage and convert its main content to Markdown."""

from __future__ import annotations

import argparse
import sys

from toolscripts.core.clipboard import copy_to_clipboard
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)


def web2md(url: str) -> str:
    try:
        import requests  # type: ignore[import-not-found]
        from bs4 import BeautifulSoup  # type: ignore[import-not-found]
        from markdownify import markdownify as md  # type: ignore[import-not-found]
    except ImportError:
        log.error(
            "missing dependencies: install with `pip install requests beautifulsoup4 markdownify`"
        )
        sys.exit(1)

    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    content = soup.find("main") or soup.find("article") or soup.body or soup
    return md(str(content), heading_style="ATX")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="web2md",
        description="Fetch a webpage and convert its main content to Markdown.",
    )
    parser.add_argument("url", help="page URL")
    parser.add_argument("--no-copy", action="store_true", help="do not copy result to clipboard")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    markdown = web2md(args.url)
    if args.no_copy:
        sys.stdout.write(markdown)
        return
    if copy_to_clipboard(markdown):
        log.success("markdown copied to clipboard (%d chars)", len(markdown))
    else:
        log.warning("could not copy to clipboard - printing instead")
        sys.stdout.write(markdown)


if __name__ == "__main__":
    main()
