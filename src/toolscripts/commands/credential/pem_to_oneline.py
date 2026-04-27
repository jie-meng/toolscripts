"""``pem-to-oneline`` - extract a PEM key body and copy it to the clipboard."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from toolscripts.core.clipboard import copy_to_clipboard
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)

_PEM_RE = re.compile(
    r"-----BEGIN\s+(?:RSA\s+)?(PUBLIC|PRIVATE)\s+KEY-----"
    r"([A-Za-z0-9+/=]+)"
    r"-----END\s+(?:RSA\s+)?\1\s+KEY-----"
)


def extract_key(content: str) -> tuple[str, str]:
    flat = content.replace("\n", "").replace("\r", "")
    matches = _PEM_RE.findall(flat)
    if not matches:
        raise ValueError("no valid PEM key found in file")
    key_type, key_data = matches[0]
    return key_type, key_data.replace(" ", "")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pem-to-oneline",
        description="Read a PEM file and emit just the base64 key body on a single line.",
    )
    parser.add_argument("file", help="path to the PEM file")
    parser.add_argument(
        "--no-copy", action="store_true", help="print only; do not touch clipboard"
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    path = Path(args.file).expanduser()
    if not path.is_file():
        log.error("file not found: %s", path)
        sys.exit(1)

    try:
        _, body = extract_key(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        log.error("%s", exc)
        sys.exit(1)

    print(body)
    if args.no_copy:
        return
    if copy_to_clipboard(body):
        log.success("copied to clipboard")
    else:
        log.warning("could not copy to clipboard")


if __name__ == "__main__":
    main()
