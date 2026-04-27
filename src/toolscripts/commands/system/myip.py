"""``myip`` - print local interface IPs and the public IP."""

from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import urllib.request

from toolscripts.core.clipboard import copy_to_clipboard
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.platform import is_windows

log = get_logger(__name__)


def _local_ips() -> list[str]:
    if is_windows():
        try:
            out = subprocess.check_output(["ipconfig"], text=True, encoding="utf-8", errors="ignore")
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []
        ips: list[str] = []
        for line in out.splitlines():
            stripped = line.strip()
            if stripped.startswith("IPv4 Address") or stripped.startswith("IP Address"):
                if ":" in stripped:
                    ips.append(stripped.split(":", 1)[1].strip())
        return ips

    try:
        out = subprocess.check_output(["ifconfig"], text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            out = subprocess.check_output(["ip", "-o", "-4", "addr", "show"], text=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []
    ips: list[str] = []
    for line in out.splitlines():
        stripped = line.strip()
        if stripped.startswith("inet ") and "127.0.0.1" not in stripped:
            ips.append(stripped.split()[1].split("/")[0])
    return ips


def _public_ip(timeout: float = 5.0) -> str | None:
    for url in ("https://ifconfig.me/ip", "https://api.ipify.org", "https://icanhazip.com"):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return resp.read().decode().strip()
        except Exception:  # noqa: BLE001
            continue
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="myip",
        description="Show local IPs (from ifconfig/ip/ipconfig) and the public IP.",
    )
    parser.add_argument(
        "--no-copy", action="store_true", help="do not copy public IP to clipboard"
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    print("Local IP:")
    locals_ = _local_ips()
    if not locals_:
        try:
            locals_ = [socket.gethostbyname(socket.gethostname())]
        except OSError:
            locals_ = []
    if locals_:
        for ip in locals_:
            print(f"  {ip}")
    else:
        log.warning("could not detect local IP")

    print("\nPublic IP:")
    public = _public_ip()
    if public:
        print(f"  {public}")
        if not args.no_copy and copy_to_clipboard(public):
            log.success("public IP copied to clipboard")
    else:
        log.warning("could not fetch public IP")
        sys.exit(1)


if __name__ == "__main__":
    main()
