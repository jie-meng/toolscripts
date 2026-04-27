"""``imgcat`` - display images inline in iTerm2 via the OSC 1337 protocol.

Cross-platform note: iTerm2 only supports the OSC 1337 image protocol on
macOS. The command is portable Python, but the actual rendering only happens
inside iTerm2 (or a few other compatible terminals).
"""

from __future__ import annotations

import argparse
import base64
import os
import sys
import urllib.request
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)


def _osc_prefix() -> bytes:
    if os.environ.get("TERM", "").startswith("screen"):
        return b"\x1bPtmux;\x1b\x1b]"
    return b"\x1b]"


def _osc_suffix() -> bytes:
    if os.environ.get("TERM", "").startswith("screen"):
        return b"\x07\x1b\\"
    return b"\x07"


def _emit(name: str, payload: bytes, *, print_filename: bool = False) -> None:
    encoded = base64.b64encode(payload)
    sys.stdout.buffer.write(_osc_prefix())
    parts = [b"1337;File="]
    if name:
        parts.append(b"name=" + base64.b64encode(name.encode("utf-8")) + b";")
    parts.append(f"size={len(payload)}".encode())
    parts.append(b";inline=1:")
    parts.append(encoded)
    sys.stdout.buffer.write(b"".join(parts))
    sys.stdout.buffer.write(_osc_suffix())
    sys.stdout.buffer.write(b"\n")
    if print_filename and name:
        sys.stdout.write(name + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="imgcat",
        description="Display images inline in iTerm2 via the OSC 1337 protocol.",
    )
    parser.add_argument("files", nargs="*", help="image files (or stdin if omitted)")
    parser.add_argument(
        "-p", "--print-filename", action="store_true", help="print filename after image"
    )
    parser.add_argument("-u", "--url", help="fetch and display the given URL")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    if args.url:
        try:
            with urllib.request.urlopen(args.url) as resp:
                payload = resp.read()
        except (OSError, ValueError) as exc:
            log.error("could not fetch %s: %s", args.url, exc)
            sys.exit(2)
        _emit(args.url, payload, print_filename=args.print_filename)

    if args.files:
        for raw in args.files:
            path = Path(raw)
            if not path.is_file():
                log.error("imgcat: %s: no such file", raw)
                sys.exit(2)
            _emit(path.name, path.read_bytes(), print_filename=args.print_filename)
        return

    if args.url:
        return

    if sys.stdin.isatty():
        parser.print_help()
        return
    payload = sys.stdin.buffer.read()
    _emit("", payload)


if __name__ == "__main__":
    main()
