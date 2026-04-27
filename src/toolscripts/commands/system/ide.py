"""``intellij`` / ``pycharm`` / ``xcode`` - open the current directory in an IDE (macOS)."""

from __future__ import annotations

import argparse
import sys

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.platform import is_macos, require_platform
from toolscripts.core.shell import run

log = get_logger(__name__)


def _macos_open(*open_args: str) -> None:
    require_platform("macos")
    run(["open", *open_args])


def _open_path() -> str:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("path", nargs="?", default=".", help="path to open (default: .)")
    add_logging_flags(parser)
    args, _ = parser.parse_known_args()
    configure_from_args(args)
    return args.path


def intellij_main() -> None:
    parser = argparse.ArgumentParser(
        prog="intellij",
        description="Open the current directory in IntelliJ IDEA (macOS only).",
    )
    parser.add_argument("path", nargs="?", default=".", help="path to open (default: .)")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)
    if not is_macos():
        log.warning("intellij command currently only supports macOS")
        sys.exit(0)
    run(["open", "-b", "com.jetbrains.intellij", args.path])


def pycharm_main() -> None:
    parser = argparse.ArgumentParser(
        prog="pycharm",
        description="Open the current directory in PyCharm (macOS only).",
    )
    parser.add_argument("path", nargs="?", default=".", help="path to open (default: .)")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)
    if not is_macos():
        log.warning("pycharm command currently only supports macOS")
        sys.exit(0)
    run(["open", "-b", "com.jetbrains.pycharm", args.path])


def xcode_main() -> None:
    parser = argparse.ArgumentParser(
        prog="xcode",
        description="Open the current directory in Xcode (macOS only).",
    )
    parser.add_argument("path", nargs="?", default=".", help="path to open (default: .)")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)
    if not is_macos():
        log.warning("xcode command currently only supports macOS")
        sys.exit(0)
    run(["open", "-a", "Xcode", args.path])


if __name__ == "__main__":
    intellij_main()
