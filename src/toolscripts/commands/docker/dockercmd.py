"""``dockercmd`` - interactive front-end for common docker operations."""

from __future__ import annotations

import argparse
import subprocess
import sys

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import CommandNotFoundError, require

log = get_logger(__name__)


def _ask(prompt: str) -> str:
    try:
        return input(prompt + ": ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(130)


def _run(cmd: list[str]) -> None:
    log.info("executing: %s", " ".join(cmd))
    subprocess.run(cmd, check=False)


def _all_container_ids() -> list[str]:
    try:
        out = subprocess.check_output(
            ["docker", "container", "ls", "-a", "-q"], text=True
        )
    except subprocess.CalledProcessError:
        return []
    return [c.strip() for c in out.splitlines() if c.strip()]


def _all_image_ids() -> list[str]:
    try:
        out = subprocess.check_output(["docker", "image", "ls", "-q"], text=True)
    except subprocess.CalledProcessError:
        return []
    return [c.strip() for c in out.splitlines() if c.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="dockercmd",
        description="Interactive front-end for common docker operations.",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        require("docker")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)

    while True:
        print("\nSelect a Docker operation:")
        print("  1) List all containers")
        print("  2) Stop a specific container")
        print("  3) Stop all running containers")
        print("  4) Remove a specific container")
        print("  5) Remove all containers")
        print("  6) List all images")
        print("  7) Remove a specific image")
        print("  8) Remove all images")
        print("  9) Show logs of a container")
        print(" 10) Inspect host network")
        print(" 11) Exec bash into a container")
        print(" 12) Show docker disk usage")
        print(" 13) System prune (-a)")
        print(" 14) Volume prune")
        print("  0) Quit")
        try:
            choice = input("Your choice: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if choice == "0":
            return
        if choice == "1":
            _run(["docker", "container", "ls", "-a"])
        elif choice == "2":
            cid = _ask("container id/name to stop")
            if cid:
                _run(["docker", "container", "stop", cid])
        elif choice == "3":
            ids = _all_container_ids()
            if not ids:
                log.warning("no containers found")
            else:
                _run(["docker", "container", "stop", *ids])
        elif choice == "4":
            cid = _ask("container id/name to remove")
            if cid:
                _run(["docker", "container", "rm", cid])
        elif choice == "5":
            ids = _all_container_ids()
            if not ids:
                log.warning("no containers found")
            else:
                _run(["docker", "container", "rm", *ids])
        elif choice == "6":
            _run(["docker", "image", "ls"])
        elif choice == "7":
            iid = _ask("image id/name to remove")
            if iid:
                _run(["docker", "image", "rm", iid])
        elif choice == "8":
            ids = _all_image_ids()
            if not ids:
                log.warning("no images found")
            else:
                _run(["docker", "image", "rm", "-f", *ids])
        elif choice == "9":
            cid = _ask("container id/name for logs")
            if cid:
                _run(["docker", "logs", cid])
        elif choice == "10":
            _run(["docker", "network", "inspect", "host"])
        elif choice == "11":
            cid = _ask("container id/name to exec bash into")
            if cid:
                _run(["docker", "container", "exec", "-it", cid, "bash"])
        elif choice == "12":
            _run(["docker", "system", "df"])
        elif choice == "13":
            _run(["docker", "system", "prune", "-a"])
        elif choice == "14":
            _run(["docker", "volume", "prune"])
        else:
            log.warning("invalid choice")
        print("-" * 28)


if __name__ == "__main__":
    main()
