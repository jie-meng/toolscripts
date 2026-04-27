"""``docker-registry`` - manage a private docker registry (start, query, push)."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from importlib import resources
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import CommandNotFoundError, require, run

log = get_logger(__name__)

CONFIG_DIR = Path.home() / ".config" / "toolscripts" / "docker-registry"
CONFIG_FILE = CONFIG_DIR / "default_config.json"


def _bundled_config() -> Path | None:
    try:
        ref = resources.files("toolscripts.data.docker_registry").joinpath("config.yml")
    except (ModuleNotFoundError, AttributeError):
        return None
    try:
        with resources.as_file(ref) as path:
            return Path(path)
    except Exception:  # noqa: BLE001
        return None


def _load_config() -> dict:
    if not CONFIG_FILE.is_file():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.error("could not read %s: %s", CONFIG_FILE, exc)
        return {}


def _save_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    log.success("saved %s", CONFIG_FILE)


def _prompt(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    try:
        raw = input(f"{prompt}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(130)
    return raw or (default or "")


def _registry_url(config: dict) -> tuple[str, str]:
    prefix = config.get("prefix") or _prompt("scheme (http/https)", "https")
    host = config.get("host") or _prompt("registry host:port")
    return prefix, host


def _set_default_config() -> dict:
    config = {
        "prefix": _prompt("scheme (http/https)", "https"),
        "host": _prompt("registry host:port"),
        "port": int(_prompt("port for `docker run -p`", "5000")),
    }
    _save_config(config)
    return config


def _start_registry() -> None:
    try:
        require("docker")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        return
    cfg_path = _bundled_config()
    if cfg_path is None:
        log.error("bundled registry config not found - re-install the package")
        return
    port = _prompt("port", "5000")
    log.info("running 'docker run -d -p %s:%s registry:latest' (with mapped storage)", port, port)
    run(
        [
            "docker",
            "run",
            "-d",
            "-p",
            f"{port}:{port}",
            "-v",
            "/opt/data/registry:/var/lib/registry",
            "-v",
            f"{cfg_path}:/etc/docker/registry/config.yml",
            "--restart=always",
            "--name",
            "registry",
            "registry:latest",
        ]
    )


def _http_get(url: str) -> str | None:
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except urllib.error.URLError as exc:
        log.error("HTTP request failed: %s", exc)
        return None


def _check_catalog(config: dict) -> None:
    prefix, host = _registry_url(config)
    body = _http_get(f"{prefix}://{host}/v2/_catalog")
    if body:
        print(body)


def _check_image_tag_list(config: dict) -> None:
    prefix, host = _registry_url(config)
    image = _prompt("image name")
    body = _http_get(f"{prefix}://{host}/v2/{image}/tags/list")
    if body:
        print(body)


def _tag_and_push(config: dict) -> None:
    try:
        require("docker")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        return
    _, host = _registry_url(config)
    image_tag = _prompt("image:tag to push")
    if not image_tag:
        return
    run(["docker", "tag", image_tag, f"{host}/{image_tag}"])
    run(["docker", "push", f"{host}/{image_tag}"])


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="docker-registry",
        description="Manage a private docker registry (start, query catalog/tags, tag and push).",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    config = _load_config()

    while True:
        print("\nSelect an action:")
        print("  1) Start registry container")
        print("  2) Set default config")
        print("  3) Check catalog")
        print("  4) Check image tag list")
        print("  5) Tag and push image")
        print("  0) Quit")
        try:
            choice = input("Your choice: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if choice == "0":
            return
        if choice == "1":
            _start_registry()
        elif choice == "2":
            config = _set_default_config()
        elif choice == "3":
            _check_catalog(config)
        elif choice == "4":
            _check_image_tag_list(config)
        elif choice == "5":
            _tag_and_push(config)
        else:
            log.warning("invalid choice")


if __name__ == "__main__":
    main()
