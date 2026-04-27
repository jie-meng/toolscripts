"""``cleanup`` - macOS housekeeping (caches, simulators, brew, npm, etc.).

Reimplemented in Python from ``shell/cleanup``. macOS only.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.platform import require_platform
from toolscripts.core.prompts import yes_no
from toolscripts.core.shell import which

log = get_logger(__name__)


def _try_size(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        if path.is_file():
            return path.stat().st_size
        total = 0
        for root, _dirs, files in os.walk(path):
            for fname in files:
                try:
                    total += (Path(root) / fname).stat().st_size
                except OSError:
                    continue
        return total
    except OSError:
        return 0


def _human(size: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{value} {units[-1]}"


def _delete(path: Path) -> int:
    size = _try_size(path)
    if size == 0:
        return 0
    log.info("removing %s (%s)", path, _human(size))
    if path.is_file() or path.is_symlink():
        try:
            path.unlink()
        except OSError as exc:
            log.warning("failed: %s", exc)
            return 0
    else:
        shutil.rmtree(path, ignore_errors=True)
    return size


def _glob_remove(pattern: str) -> int:
    total = 0
    for match in Path("/").glob(pattern.lstrip("/")):
        total += _delete(match)
    return total


def _disk_avail(target: str = "/") -> int | None:
    try:
        st = shutil.disk_usage(target)
        return st.free
    except OSError:
        return None


_TRASH_PATHS = [
    Path("/Volumes"),
    Path.home() / ".Trash",
]

_SYSTEM_LOGS = [
    Path("/private/var/log/asl"),
    Path("/Library/Logs/DiagnosticReports"),
    Path("/Library/Logs/Adobe"),
    Path.home() / "Library/Containers/com.apple.mail/Data/Library/Logs/Mail",
    Path.home() / "Library/Logs/CoreSimulator",
]

_XCODE_PATHS = [
    Path.home() / "Library/Developer/Xcode/DerivedData",
    Path.home() / "Library/Developer/Xcode/Archives",
    Path.home() / "Library/Developer/Xcode/iOS Device Logs",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="cleanup",
        description="macOS housekeeping: clear caches, derived data, simulators, brew, npm caches, etc.",
    )
    parser.add_argument(
        "-n",
        "--no-updates",
        action="store_true",
        help="skip Homebrew update/upgrade",
    )
    parser.add_argument(
        "--docker", action="store_true", help="also run `docker system prune -af`"
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    require_platform("macos")

    if not yes_no(
        "this will delete a lot of caches and trashed files - continue?", default=False
    ):
        log.info("cancelled")
        return

    log.info("attempting sudo keep-alive...")
    sudo_path = which("sudo")
    if sudo_path:
        subprocess.run([sudo_path, "-v"], check=False)

    before = _disk_avail()
    saved = 0

    log.info("emptying Trash...")
    for trash in _TRASH_PATHS:
        for entry in (trash.glob("*") if trash.is_dir() else []):
            saved += _delete(entry)

    log.info("clearing system logs...")
    for log_dir in _SYSTEM_LOGS:
        for entry in (log_dir.glob("*") if log_dir.is_dir() else []):
            saved += _delete(entry)

    log.info("clearing Xcode derived data and archives...")
    for path in _XCODE_PATHS:
        for entry in (path.glob("*") if path.is_dir() else []):
            saved += _delete(entry)

    if which("xcrun"):
        log.info("shutting down and erasing simulators...")
        subprocess.run(["xcrun", "simctl", "shutdown", "all"], check=False)
        subprocess.run(["xcrun", "simctl", "erase", "all"], check=False)

    cocoapods = Path.home() / "Library/Caches/CocoaPods"
    if cocoapods.is_dir():
        log.info("clearing CocoaPods cache...")
        saved += _delete(cocoapods)

    gradle = Path.home() / ".gradle/caches"
    if gradle.is_dir():
        log.info("clearing Gradle caches...")
        saved += _delete(gradle)

    if which("brew"):
        if not args.no_updates:
            log.info("running `brew update` and `brew upgrade`...")
            subprocess.run(["brew", "update"], check=False)
            subprocess.run(["brew", "upgrade"], check=False)
        log.info("running `brew cleanup -s`...")
        subprocess.run(["brew", "cleanup", "-s"], check=False)
        try:
            cache = subprocess.check_output(["brew", "--cache"], text=True).strip()
            saved += _delete(Path(cache))
        except subprocess.CalledProcessError:
            pass

    if which("gem"):
        log.info("running `gem cleanup`...")
        subprocess.run(["gem", "cleanup"], check=False)

    if args.docker and which("docker"):
        log.info("running `docker system prune -af`...")
        subprocess.run(["docker", "system", "prune", "-af"], check=False)

    pip_cache = Path.home() / "Library/Caches/pip"
    if pip_cache.is_dir():
        log.info("clearing pip cache...")
        saved += _delete(pip_cache)

    if which("npm"):
        log.info("running `npm cache clean --force`...")
        subprocess.run(["npm", "cache", "clean", "--force"], check=False)

    if which("yarn"):
        log.info("running `yarn cache clean --force`...")
        subprocess.run(["yarn", "cache", "clean", "--force"], check=False)

    if sudo_path:
        log.info("running `sudo purge` (this may take a moment)...")
        subprocess.run([sudo_path, "purge"], check=False)

    after = _disk_avail()
    if before is not None and after is not None:
        diff = after - before
        log.success("cleanup done. recovered ~%s on volume.", _human(max(0, diff)))
    else:
        log.success("cleanup done. recovered ~%s.", _human(saved))


if __name__ == "__main__":
    main()
