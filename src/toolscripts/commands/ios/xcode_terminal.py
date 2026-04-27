"""``xcode-terminal`` - open the directory of the active Xcode project in iTerm.

Configured as an Xcode "Behavior -> Run -> Script" target. Reads the
``XcodeProjectPath`` / ``XcodeWorkspacePath`` environment variables Xcode
exports to its build scripts.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.platform import require_platform
from toolscripts.core.shell import run

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="xcode-terminal",
        description=(
            "Open the parent directory of the current Xcode project/workspace in iTerm. "
            "Reads $XcodeProjectPath / $XcodeWorkspacePath."
        ),
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    require_platform("macos")
    project = os.environ.get("XcodeProjectPath") or os.environ.get("XcodeWorkspacePath")
    if not project:
        log.error("neither XcodeProjectPath nor XcodeWorkspacePath is set")
        sys.exit(1)

    parent = Path(project).expanduser().parent
    log.info("opening %s in iTerm", parent)
    run(["open", "-a", "iTerm", str(parent)])


if __name__ == "__main__":
    main()
