"""``aido`` and ``aido-models`` - run prompts via opencode + a saved free model."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import CommandNotFoundError, capture, require, run

log = get_logger(__name__)

CONFIG_DIR = Path.home() / ".config" / "toolscripts"
CONFIG_FILE = CONFIG_DIR / "config.json"
CONFIG_KEY = "aido_model"


def _load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_config(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _fetch_free_models() -> list[str]:
    try:
        require("opencode")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)
    try:
        out = capture(["opencode", "models"])
    except Exception as exc:  # noqa: BLE001
        log.error("opencode models failed: %s", exc)
        sys.exit(1)
    return [line for line in out.splitlines() if "free" in line.lower()]


def models_main() -> None:
    parser = argparse.ArgumentParser(
        prog="aido-models",
        description="Pick a free opencode model to use with `aido`.",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    models = _fetch_free_models()
    if not models:
        log.warning("no free models found")
        sys.exit(1)

    config = _load_config()
    saved = config.get(CONFIG_KEY, "")

    print("Select a free model for aido:")
    for i, m in enumerate(models, 1):
        marker = "*" if m == saved else " "
        print(f"  {marker} {i}. {m}")
    try:
        raw = input(f"Choice [1-{len(models)}]: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    if not raw or not raw.isdigit():
        log.warning("cancelled")
        return
    idx = int(raw) - 1
    if not 0 <= idx < len(models):
        log.error("invalid selection")
        sys.exit(1)
    chosen = models[idx]
    config[CONFIG_KEY] = chosen
    _save_config(config)
    log.success("model saved: %s", chosen)


def run_main() -> None:
    parser = argparse.ArgumentParser(
        prog="aido",
        description="Run a prompt via `opencode run` using the saved free model.",
        add_help=False,
    )
    parser.add_argument("prompt", nargs=argparse.REMAINDER, help="prompt to send")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    if not args.prompt:
        log.error("usage: aido <prompt> [...]")
        sys.exit(1)

    config = _load_config()
    model = config.get(CONFIG_KEY)
    if not model:
        log.error("no model configured. Run `aido-models` to select one.")
        sys.exit(1)

    try:
        require("opencode")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)

    prompt = " ".join(args.prompt)
    cmd = ["opencode", "run", prompt, "-m", model]
    log.debug("running: %s", " ".join(cmd))
    run(cmd)


if __name__ == "__main__":
    run_main()
