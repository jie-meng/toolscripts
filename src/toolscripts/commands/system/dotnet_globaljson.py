"""``dotnet-globaljson`` - generate a global.json to pin the .NET SDK version."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)

_MULTI_SDK_HELP = """\
To install multiple SDK versions side-by-side in a single dotnet installation:

  # Download the official installer script
  curl -L https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh
  chmod +x /tmp/dotnet-install.sh

  # Install specific SDK versions (they share the same dotnet binary)
  /tmp/dotnet-install.sh --channel 8.0
  /tmp/dotnet-install.sh --channel 9.0

  # Add to your shell rc (~/.zshrc / ~/.bashrc):
  export DOTNET_ROOT="$HOME/.dotnet"
  export PATH="$DOTNET_ROOT:$PATH"

  # Now `dotnet --list-sdks` shows all versions, and global.json pins one."""


def _parse_sdk_line(line: str) -> str:
    return line.split()[0]


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="dotnet-globaljson",
        description="Generate a global.json to pin the .NET SDK version.",
    )
    parser.add_argument(
        "--sdk-version",
        help="SDK version to pin (e.g. 8.0.200 or 9.0.100). "
        "If omitted, lists installed SDKs and shows multi-SDK install help.",
    )
    parser.add_argument(
        "--roll-forward",
        default="latestMajor",
        choices=[
            "patch",
            "feature",
            "minor",
            "latestMinor",
            "major",
            "latestMajor",
        ],
        help="Roll-forward policy (default: latestMajor)",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    path = Path.cwd() / "global.json"
    content = {
        "sdk": {
            "version": args.sdk_version,
            "rollForward": args.roll_forward,
        }
    }

    if args.sdk_version:
        if path.exists():
            log.warning("%s already exists, overwriting", path)

        path.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")
        log.success("Created %s", path)
        print(f"  SDK version:  {args.sdk_version}")
        print(f"  Roll-forward: {args.roll_forward}")
        print()

        try:
            from toolscripts.core.shell import capture

            sdks = capture(["dotnet", "--list-sdks"])
            versions = [_parse_sdk_line(line) for line in sdks.splitlines()]
            if args.sdk_version not in versions:
                log.warning(
                    "SDK %s not found in the current dotnet installation. "
                    "Use dotnet-install.sh to add it (see below).",
                    args.sdk_version,
                )
                print()
                print(_MULTI_SDK_HELP)
        except Exception:
            pass
        return

    # No --sdk-version: show available SDKs and multi-SDK help
    try:
        from toolscripts.core.shell import capture, require

        require("dotnet")
        sdks = capture(["dotnet", "--list-sdks"])
        print("Available SDKs from the current dotnet:")
        for line in sdks.splitlines():
            print(f"  {line}")
    except Exception:
        print("dotnet is not on PATH or no SDKs found.")

    print()
    print(_MULTI_SDK_HELP)
