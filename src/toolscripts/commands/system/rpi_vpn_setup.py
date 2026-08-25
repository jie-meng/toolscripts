"""``rpi-vpn-setup`` - install, inspect, or update a mihomo (Clash.Meta) VPN on a Raspberry Pi.

The command runs on the operator machine (macOS/Linux) and drives the Pi over
SSH. mihomo and its geo databases are fetched from GitHub on the operator side
(the Pi itself cannot reach GitHub) and pushed to the Pi.

Interactive flow (no action): install if missing, otherwise show status and ask
whether to refresh the subscription. ``--status`` only reports; ``--update``
prompts for a new subscription URL.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.prompts import ask, yes_no
from toolscripts.core.shell import (
    CommandNotFoundError,
    capture,
    require,
    run,
    try_run,
)

log = get_logger(__name__)

DEFAULT_HOST = "jiemeng@pi-home.local"
PI_HOME = "/home/jiemeng"

MH_REL = "https://github.com/MetaCubeX/mihomo/releases"
GEO_REPO = "https://github.com/MetaCubeX/meta-rules-dat/releases/latest/download"

CONFIG_TEMPLATE = """\
mixed-port: 7890
mode: rule
log-level: info
external-controller: 127.0.0.1:9090
dns:
  enable: true
  ipv6: false
  enhanced-mode: fake-ip
  fake-ip-range: 198.18.0.1/16
  use-hosts: true
  default-nameserver:
    - ___DEFAULT_DNS___
  nameserver:
    - https://doh.pub/dns-query
    - https://dns.alidns.com/dns-query
  fallback:
    - https://doh.pub/dns-query
  fallback-filter:
    geoip: true
    geoip-code: CN
    ipcidr:
      - 240.0.0.0/4
      - 0.0.0.0/32
proxies: []
proxy-providers:
  sub:
    type: http
    url: "__SUB_URL__"
    path: /etc/mihomo/subscription.yaml
    interval: 3600
    health-check:
      enable: true
      url: https://www.gstatic.com/generate_204
      interval: 300
proxy-groups:
  - name: Auto
    type: url-test
    url: https://www.gstatic.com/generate_204
    interval: 300
    proxies:
      - sub
  - name: PROXY
    type: select
    proxies:
      - Auto
      - sub
rules:
  - GEOIP,CN,DIRECT
  - DOMAIN-SUFFIX,cn,DIRECT
  - MATCH,PROXY
"""

SUB_SCRIPT = """\
#!/usr/bin/env bash
set -e
if [ -z "${1:-}" ]; then echo "usage: sudo mihomo-sub <subscription-url>"; exit 1; fi
SUB_URL="$1"
TEMPLATE=/etc/mihomo/config.template.yaml
CONFIG=/etc/mihomo/config.yaml
[ -f "$TEMPLATE" ] || { echo "error: template missing $TEMPLATE"; exit 1; }
python3 - "$TEMPLATE" "$CONFIG" "$SUB_URL" <<'PY'
import sys
tpl, cfg, url = sys.argv[1], sys.argv[2], sys.argv[3]
data = open(tpl, encoding="utf-8").read().replace("__SUB_URL__", url)
open(cfg, "w", encoding="utf-8").write(data)
print("written", cfg)
PY
systemctl restart mihomo
echo "subscription updated, mihomo restarted"
"""

SERVICE_UNIT = """\
[Unit]
Description=mihomo (Clash.Meta) proxy
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStartPre=/bin/sh -c 'test -f /etc/mihomo/config.yaml && ! grep -q "__SUB_URL__" /etc/mihomo/config.yaml'
ExecStart=/usr/local/bin/mihomo -d /etc/mihomo
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
"""

BASHRC_BLOCK = r"""
# ===== mihomo proxy (automatic on boot, no manual -x needed) =====
export http_proxy="http://127.0.0.1:7890"
export https_proxy="http://127.0.0.1:7890"
export all_proxy="http://127.0.0.1:7890"
export no_proxy="localhost,127.0.0.1,::1,192.168.0.0/16,10.0.0.0/8,172.16.0.0/12,.local"
export NO_PROXY="$no_proxy"
proxy_on(){ export http_proxy="http://127.0.0.1:7890" https_proxy="http://127.0.0.1:7890" all_proxy="http://127.0.0.1:7890"; echo "proxy ON"; }
proxy_off(){ unset http_proxy https_proxy all_proxy; echo "proxy OFF"; }
gping(){ curl -s -o /dev/null -w "%{http_code}  (%{time_total}s)\n" --connect-timeout 10 "https://${1:-google.com}"; }
"""

APT_BLOCK = """\
Acquire::http::Proxy "http://127.0.0.1:7890";
Acquire::https::Proxy "http://127.0.0.1:7890";
"""

PIP_BLOCK = """\
[global]
proxy = http://127.0.0.1:7890
"""


def ssh_run(host: str, cmd: str, *, check: bool = True, input: str | None = None):
    return run(["ssh", host, cmd], check=check, input=input)


def ssh_capture(host: str, cmd: str) -> str:
    return capture(["ssh", host, cmd], check=False)


def ssh_push(host: str, local: Path, remote: str) -> None:
    run(["scp", str(local), f"{host}:{remote}"])


def download(url: str, dest: Path) -> None:
    run(["curl", "-fsSL", "-o", str(dest), url])


def resolve_mihomo_tag() -> str:
    url = capture(["curl", "-sL", "-o", "/dev/null", "-w", "%{redirect_url}", f"{MH_REL}/latest"])
    return url.rsplit("/tag/", 1)[-1]


def detect_arch(host: str) -> str:
    mapping = {
        "aarch64": "linux-arm64",
        "arm64": "linux-arm64",
        "armv7l": "linux-armv7",
        "x86_64": "linux-amd64",
    }
    return mapping.get(ssh_capture(host, "uname -m").strip(), "linux-arm64")


def mihomo_installed(host: str) -> bool:
    return try_run(["ssh", host, "test -x /usr/local/bin/mihomo"])


def service_installed(host: str) -> bool:
    return try_run(["ssh", host, "test -f /etc/systemd/system/mihomo.service"])


def bootstrap_dns(host: str) -> str:
    out = ssh_capture(host, "grep -m1 ^nameserver /etc/resolv.conf | awk '{print $2}'")
    return out.strip() or "192.168.1.3"


def configure_shell_proxy(host: str) -> None:
    log.info("configuring terminal auto-proxy (bashrc / apt / pip)...")
    if try_run(["ssh", host, f"grep -q 'mihomo proxy' {PI_HOME}/.bashrc"]):
        log.info("bashrc already has proxy config, skipping")
    else:
        ssh_run(host, f"cat >> {PI_HOME}/.bashrc", input=BASHRC_BLOCK)
    ssh_run(host, "sudo tee /etc/apt/apt.conf.d/95mihomo >/dev/null", input=APT_BLOCK)
    ssh_run(
        host,
        f"mkdir -p {PI_HOME}/.config/pip && tee {PI_HOME}/.config/pip/pip.conf >/dev/null",
        input=PIP_BLOCK,
    )


def install_all(host: str) -> None:
    arch = detect_arch(host)
    log.info("architecture: %s", arch)

    resolv = bootstrap_dns(host)
    log.info("Pi bootstrap DNS: %s", resolv)

    if mihomo_installed(host):
        version = ssh_capture(host, "/usr/local/bin/mihomo -v").splitlines()[0]
        log.info("mihomo already present: %s", version)
    else:
        tag = resolve_mihomo_tag()
        log.info("latest mihomo: %s", tag)
        with tempfile.TemporaryDirectory() as tmp:
            bin_gz = Path(tmp) / "mihomo.gz"
            download(f"{MH_REL}/download/{tag}/mihomo-{arch}-{tag}.gz", bin_gz)
            run(["gunzip", "-f", str(bin_gz)])
            ssh_push(host, Path(tmp) / "mihomo", "/tmp/mihomo")
            ssh_run(
                host,
                "sudo install -m 0755 /tmp/mihomo /usr/local/bin/mihomo && sudo rm -f /tmp/mihomo",
            )

    with tempfile.TemporaryDirectory() as tmp:
        for name in ("geoip.dat", "geosite.dat", "geoip.metadb", "GeoLite2-ASN.mmdb"):
            local = Path(tmp) / name
            download(f"{GEO_REPO}/{name}", local)
            ssh_push(host, local, f"/tmp/{name}")
            ssh_run(host, f"sudo mv -f /tmp/{name} /etc/mihomo/{name}")
        ssh_run(host, "sudo mkdir -p /etc/mihomo")

        template = Path(tmp) / "config.template.yaml"
        template.write_text(CONFIG_TEMPLATE.replace("___DEFAULT_DNS___", resolv), encoding="utf-8")
        (Path(tmp) / "mihomo-sub").write_text(SUB_SCRIPT, encoding="utf-8")
        (Path(tmp) / "mihomo.service").write_text(SERVICE_UNIT, encoding="utf-8")
        ssh_push(host, template, "/tmp/config.template.yaml")
        ssh_push(host, Path(tmp) / "mihomo-sub", "/tmp/mihomo-sub")
        ssh_push(host, Path(tmp) / "mihomo.service", "/tmp/mihomo.service")
        ssh_run(host, "sudo mv -f /tmp/config.template.yaml /etc/mihomo/config.template.yaml")
        ssh_run(host, "sudo install -m 0755 /tmp/mihomo-sub /usr/local/bin/mihomo-sub")
        ssh_run(host, "sudo mv -f /tmp/mihomo.service /etc/systemd/system/mihomo.service")
        ssh_run(host, "sudo systemctl daemon-reload")
        ssh_run(host, "sudo systemctl enable mihomo")

    configure_shell_proxy(host)

    url = ask("enter subscription URL")
    if not url:
        log.error("subscription URL required")
        sys.exit(1)
    ssh_run(host, f"sudo mihomo-sub '{url}'")

    time.sleep(5)
    verify(host)
    show_status(host)


def current_subscription(host: str) -> str:
    return ssh_capture(
        host,
        "grep -m1 'url:' /etc/mihomo/config.yaml | sed 's/.*url: *//; s/\"//g'",
    ).strip()


def show_status(host: str) -> None:
    log.info("==== mihomo status ====")
    if mihomo_installed(host):
        version = ssh_capture(host, "/usr/local/bin/mihomo -v").splitlines()[0]
        log.info("binary: %s", version)
    else:
        log.warning("mihomo not installed")
    if service_installed(host):
        log.info("enabled: %s", ssh_capture(host, "systemctl is-enabled mihomo"))
        log.info("active:  %s", ssh_capture(host, "systemctl is-active mihomo"))
    else:
        log.warning("systemd service not installed")
    sub = current_subscription(host)
    if sub:
        log.info("subscription: %s", sub)
    else:
        log.warning("no subscription detected")
    ip = ssh_capture(host, "curl -s -x http://127.0.0.1:7890 https://api.ipify.org")
    if ip:
        log.info("exit IP: %s", ip)
    node = ssh_capture(
        host,
        'curl -s http://127.0.0.1:9090/proxies/PROXY | grep -o \'"now":"[^"]*"\'',
    )
    if node:
        log.info("node: %s", node)
    log.info("=======================")


def verify(host: str) -> None:
    log.info("verifying proxy connectivity...")
    code = ssh_capture(
        host,
        "curl -s -x http://127.0.0.1:7890 -o /dev/null -w '%{http_code}' --connect-timeout 12 https://www.google.com",
    )
    if code == "200":
        log.success("Google reachable via proxy (HTTP 200)")
    else:
        log.warning("Google test returned: %r (not 200)", code)


def update_sub(host: str) -> None:
    url = ask(
        "enter new subscription URL (empty = keep current)", default=current_subscription(host)
    )
    if not url:
        log.error("no subscription URL available")
        sys.exit(1)
    ssh_run(host, f"sudo mihomo-sub '{url}'")
    time.sleep(5)
    verify(host)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="rpi-vpn-setup",
        description="Install, inspect, or update a mihomo VPN on a Raspberry Pi.",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="report the current state only (no changes)",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="prompt for a new subscription URL and apply it",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Pi ssh destination (default: {DEFAULT_HOST}; env PI_HOST overrides)",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        require("ssh")
        require("scp")
        require("curl")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)

    host = args.host
    if args.status:
        show_status(host)
        return
    if args.update:
        update_sub(host)
        return

    if not mihomo_installed(host) or not service_installed(host):
        log.info("not fully installed, starting one-shot install...")
        install_all(host)
        return

    show_status(host)
    if yes_no("subscription exists, update it?", default=False):
        update_sub(host)
    else:
        log.info("kept existing config, no changes")


if __name__ == "__main__":
    main()
