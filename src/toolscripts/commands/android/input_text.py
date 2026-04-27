"""``android-input-text`` - send a text string to the focused field on an Android device."""

from __future__ import annotations

import argparse
import sys

from toolscripts.adb.devices import select_device
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.prompts import ask
from toolscripts.core.shell import run

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="android-input-text",
        description="Send text input to the connected Android device.",
    )
    parser.add_argument("text", nargs="?", help="text to send (prompted if omitted)")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    device = select_device()
    text = args.text or ask("Enter the text to send")
    if not text:
        log.error("text required")
        sys.exit(1)

    log.info("sending text to %s: %s", device, text)
    try:
        run(["adb", "-s", device, "shell", "input", "text", text])
        log.success("text sent")
    except Exception as exc:  # noqa: BLE001
        log.error("failed to send text: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
