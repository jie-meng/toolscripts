"""``android-logcat`` - run adb logcat filtered by application id and tags."""

from __future__ import annotations

import argparse

from toolscripts.adb.devices import select_device
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.prompts import ask
from toolscripts.core.shell import capture, run

log = get_logger(__name__)


def _select_pid(device: str, application_id: str) -> str:
    if not application_id:
        return ""
    output = capture(["adb", "-s", device, "shell", "ps"], check=False)
    for line in output.splitlines():
        items = line.split()
        if len(items) >= 9 and items[8] == application_id:
            log.info("pid = %s", items[1])
            return f"--pid={items[1]}"
    return ""


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="android-logcat",
        description="Run `adb logcat` filtered by an application id (pid) and tag spec.",
    )
    parser.add_argument(
        "--app", "-a", help="application id (e.g. com.example.app); prompted if omitted"
    )
    parser.add_argument(
        "--filter",
        "-f",
        dest="filter_args",
        help='logcat filter spec, e.g. "TAG1:I TAG2:D *:S"; prompted if omitted',
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    device = select_device()
    log.info("device %s selected", device)

    application_id = args.app or ask("please input applicationId") or ""
    pid_filter = _select_pid(device, application_id)

    if args.filter_args is None:
        filter_args = ask('please input args (e.g. "TAG1:I TAG2:D *:S")') or ""
    else:
        filter_args = args.filter_args

    run(["adb", "-s", device, "logcat", "-c"], check=False)
    cmd = ["adb", "-s", device, "logcat"]
    if pid_filter:
        cmd.append(pid_filter)
    if filter_args:
        cmd.extend(filter_args.split())
    log.info("running: %s", " ".join(cmd))
    try:
        run(cmd, check=False)
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
