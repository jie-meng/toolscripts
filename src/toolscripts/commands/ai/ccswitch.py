"""``ccswitch`` - switch Claude Code's ~/.claude/settings.json between provider presets."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)

SETTINGS_PATH = Path.home() / ".claude" / "settings.json"

_GLM_ENV = {
    "ANTHROPIC_AUTH_TOKEN": None,
    "ANTHROPIC_BASE_URL": "https://open.bigmodel.cn/api/anthropic",
    "API_TIMEOUT_MS": "3000000",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": 1,
    "CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK": 1,
    "CLAUDE_CODE_EFFORT_LEVEL": "max",
    "CLAUDE_CODE_SUBAGENT_MODEL": "glm-4.7",
    "ANTHROPIC_MODEL": "glm-4.7",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "glm-4.5-air",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "glm-4.7",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "glm-5.1",
}

_MINIMAX_ENV = {
    "ANTHROPIC_AUTH_TOKEN": None,
    "ANTHROPIC_BASE_URL": "https://api.minimax.io/anthropic",
    "API_TIMEOUT_MS": "3000000",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": 1,
    "CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK": 1,
    "CLAUDE_CODE_EFFORT_LEVEL": "max",
    "CLAUDE_CODE_SUBAGENT_MODEL": "MiniMax-M2.7",
    "ANTHROPIC_MODEL": "MiniMax-M2.7",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "MiniMax-M2.7",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "MiniMax-M2.7",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "MiniMax-M2.7",
}

_MIMO_ENV = {
    "ANTHROPIC_AUTH_TOKEN": None,
    "ANTHROPIC_BASE_URL": "https://api.xiaomimimo.com/anthropic",
    "API_TIMEOUT_MS": "3000000",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": 1,
    "CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK": 1,
    "CLAUDE_CODE_EFFORT_LEVEL": "max",
    "CLAUDE_CODE_SUBAGENT_MODEL": "mimo-v2.5-pro",
    "ANTHROPIC_MODEL": "mimo-v2.5-pro",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "mimo-v2.5-pro",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "mimo-v2.5-pro",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "mimo-v2.5-pro",
}

_DEEPSEEK_ENV = {
    "ANTHROPIC_AUTH_TOKEN": None,
    "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
    "API_TIMEOUT_MS": "3000000",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": 1,
    "CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK": 1,
    "CLAUDE_CODE_EFFORT_LEVEL": "max",
    "CLAUDE_CODE_SUBAGENT_MODEL": "deepseek-v4-pro[1m]",
    "ANTHROPIC_MODEL": "deepseek-v4-pro[1m]",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "deepseek-v4-flash",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "deepseek-v4-pro[1m]",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "deepseek-v4-pro[1m]",
}

PROVIDERS: dict[str, tuple[str, str | None, dict | None, str | None]] = {
    "GLM": ("GLM Code Plan", "https://docs.bigmodel.cn/cn/coding-plan/quick-start", _GLM_ENV, "GLM_API_KEY"),
    "MiniMax": ("MiniMax Code Plan", "https://platform.minimax.io/docs/guides/text-ai-coding-tools", _MINIMAX_ENV, "MINIMAX_API_KEY"),
    "MiMo": ("Xiaomi MiMo", "https://platform.xiaomimimo.com/docs/integration/claudecode", _MIMO_ENV, "MIMO_API_KEY"),
    "DeepSeek": ("DeepSeek", "https://api-docs.deepseek.com/zh-cn/guides/coding_agents", _DEEPSEEK_ENV, "DEEPSEEK_API_KEY"),
    "Custom": ("Custom Endpoint", None, None, None),
}


def _detect_current() -> tuple[str | None, str | None]:
    if not SETTINGS_PATH.exists():
        return None, None
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None, None
    env = data.get("env", {})
    base = env.get("ANTHROPIC_BASE_URL", "")
    model = env.get("ANTHROPIC_MODEL")
    for key, (_, _, preset, _) in PROVIDERS.items():
        if preset and preset.get("ANTHROPIC_BASE_URL") == base:
            return key, model
    if base:
        return "Custom", model
    return None, model


def _get_or_input(env_var: str, prompt: str, *, allow_empty: bool = False) -> str:
    value = os.environ.get(env_var, "")
    if value or (allow_empty and env_var in os.environ):
        log.info("Using %s from environment.", env_var)
        return value
    try:
        return input(f"{prompt}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(130)


def _build_custom_env() -> dict:
    endpoint = _get_or_input("CC_CUSTOM_ENDPOINT", "Enter CC_CUSTOM_ENDPOINT")
    model = _get_or_input("CC_CUSTOM_MODEL", "Enter CC_CUSTOM_MODEL")
    sonnet = _get_or_input("CC_CUSTOM_DEFAULT_SONNET_MODEL", "Enter CC_CUSTOM_DEFAULT_SONNET_MODEL")
    opus = _get_or_input("CC_CUSTOM_DEFAULT_OPUS_MODEL", "Enter CC_CUSTOM_DEFAULT_OPUS_MODEL")
    haiku = _get_or_input("CC_CUSTOM_DEFAULT_HAIKU_MODEL", "Enter CC_CUSTOM_DEFAULT_HAIKU_MODEL")
    subagent = _get_or_input(
        "CC_CUSTOM_SUBAGENT_MODEL",
        "Enter CC_CUSTOM_SUBAGENT_MODEL (optional)",
        allow_empty=True,
    )
    api_key = _get_or_input(
        "CC_CUSTOM_API_KEY", "Enter CC_CUSTOM_API_KEY (can be empty)", allow_empty=True
    )
    env = {
        "ANTHROPIC_AUTH_TOKEN": api_key,
        "ANTHROPIC_BASE_URL": endpoint,
        "API_TIMEOUT_MS": "3000000",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": 1,
        "CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK": 1,
        "CLAUDE_CODE_EFFORT_LEVEL": "max",
        "ANTHROPIC_MODEL": model,
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": haiku,
        "ANTHROPIC_DEFAULT_SONNET_MODEL": sonnet,
        "ANTHROPIC_DEFAULT_OPUS_MODEL": opus,
    }
    if subagent:
        env["CLAUDE_CODE_SUBAGENT_MODEL"] = subagent
    return env


def _update_settings(new_env: dict) -> None:
    if not SETTINGS_PATH.exists():
        log.error("settings file not found: %s", SETTINGS_PATH)
        sys.exit(1)
    data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    data.setdefault("env", {})
    data["env"].update(new_env)
    SETTINGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    log.success("settings updated.")


def _select_provider(default_idx: int) -> str | None:
    keys = list(PROVIDERS.keys())
    print("Select Claude Code provider:")
    for i, k in enumerate(keys, 1):
        marker = "*" if i - 1 == default_idx else " "
        label, url, _, _ = PROVIDERS[k]
        suffix = f" ({url})" if url else ""
        print(f"  {marker} {i}. {label}{suffix}")
    try:
        raw = input(f"Choice [1-{len(keys)}] (default: {default_idx + 1}): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    if not raw:
        return keys[default_idx]
    if not raw.isdigit():
        return None
    idx = int(raw) - 1
    if not 0 <= idx < len(keys):
        return None
    return keys[idx]


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ccswitch",
        description="Switch Claude Code's ~/.claude/settings.json between provider presets.",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    current, model = _detect_current()
    if current:
        log.info("current: %s (model=%s)", current, model)
    keys = list(PROVIDERS.keys())
    default_idx = keys.index(current) if current in keys else 0

    selected = _select_provider(default_idx)
    if selected is None:
        log.warning("cancelled")
        return

    label, _, preset, env_key = PROVIDERS[selected]
    if selected == "Custom":
        env = _build_custom_env()
    else:
        if env_key is None or preset is None:
            log.error("invalid preset for %s", selected)
            sys.exit(1)
        api_key = _get_or_input(env_key, f"Enter your {env_key}")
        env = {**preset, "ANTHROPIC_AUTH_TOKEN": api_key}

    _update_settings(env)
    log.success("switched to: %s", label)


if __name__ == "__main__":
    main()
