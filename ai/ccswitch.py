#!/usr/bin/env python3
"""Claude Code model switcher with curses UI.

Provides interactive selection to switch between:
- GLM Code Plan
- MiniMax Code Plan  
- DeepSeek
- Custom Endpoint/Model/API Key
"""

import os
import json
from pathlib import Path

import platform
import subprocess
import sys

IS_WINDOWS = platform.system() == "Windows"

SETTINGS_PATH = Path.home() / ".claude" / "settings.json"

GLM_ENV = {
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
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "glm-5.1"
}

MINIMAX_ENV = {
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
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "MiniMax-M2.7"
}

MIMO_ENV = {
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
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "mimo-v2.5-pro"
}

DEEPSEEK_ENV = {
    "ANTHROPIC_AUTH_TOKEN": None,
    "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
    "API_TIMEOUT_MS": "3000000",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": 1,
    "CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK": 1,
    "CLAUDE_CODE_EFFORT_LEVEL": "max",
    "CLAUDE_CODE_SUBAGENT_MODEL": "deepseek-v4-pro",
    "ANTHROPIC_MODEL": "deepseek-v4-pro",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "deepseek-v4-flash",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "deepseek-v4-pro",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "deepseek-v4-pro"
}

PROVIDERS = {
    "GLM": ("GLM Code Plan", "https://docs.bigmodel.cn/cn/coding-plan/quick-start", GLM_ENV),
    "MiniMax": ("MiniMax Code Plan", "https://platform.minimax.io/docs/guides/text-ai-coding-tools", MINIMAX_ENV),
    "MiMo": ("Xiaomi MiMo", "https://platform.xiaomimimo.com/docs/integration/claudecode", None),
    "DeepSeek": ("DeepSeek", "https://api-docs.deepseek.com/zh-cn/guides/coding_agents", DEEPSEEK_ENV),
    "Custom": ("Custom Endpoint", None, None),
}


def _enable_windows_ansi():
    if not IS_WINDOWS:
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        kernel32.SetConsoleMode(handle, mode.value | 4)
    except Exception:
        pass


def _ensure_curses():
    try:
        import curses as _
    except ImportError:
        if IS_WINDOWS:
            print("Installing windows-curses ...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "windows-curses"],
                stdout=subprocess.DEVNULL,
            )
        else:
            print("Error: curses module not available.")
            sys.exit(1)


def get_current_provider():
    """Detect currently active provider from settings.json."""
    if not SETTINGS_PATH.exists():
        return None
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            settings = json.load(f)
        env = settings.get("env", {})
        base_url = env.get("ANTHROPIC_BASE_URL", "")
        
        if base_url == "https://open.bigmodel.cn/api/anthropic":
            return "GLM"
        elif base_url == "https://api.minimax.io/anthropic":
            return "MiniMax"
        elif base_url == "https://api.xiaomimimo.com/anthropic":
            return "MiMo"
        elif base_url == "https://api.deepseek.com/anthropic":
            return "DeepSeek"
        elif base_url:
            return "Custom"
    except Exception:
        pass
    return None


def get_current_model():
    """Get current model name from settings.json."""
    if not SETTINGS_PATH.exists():
        return None
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            settings = json.load(f)
        return settings.get("env", {}).get("ANTHROPIC_MODEL")
    except Exception:
        pass
    return None


def get_env_or_input(env_var, prompt, allow_empty=False):
    value = os.environ.get(env_var)
    if value or (allow_empty and env_var in os.environ):
        print(f"Found {env_var} in environment. Using it.")
    else:
        value = input(f"{prompt}: ").strip()
    return value


def build_custom_env():
    endpoint = get_env_or_input("CC_CUSTOM_ENDPOINT", "Enter your CC_CUSTOM_ENDPOINT")
    model = get_env_or_input("CC_CUSTOM_MODEL", "Enter your CC_CUSTOM_MODEL")
    sonnet_model = get_env_or_input("CC_CUSTOM_DEFAULT_SONNET_MODEL", "Enter your CC_CUSTOM_DEFAULT_SONNET_MODEL")
    opus_model = get_env_or_input("CC_CUSTOM_DEFAULT_OPUS_MODEL", "Enter your CC_CUSTOM_DEFAULT_OPUS_MODEL")
    haiku_model = get_env_or_input("CC_CUSTOM_DEFAULT_HAIKU_MODEL", "Enter your CC_CUSTOM_DEFAULT_HAIKU_MODEL")
    subagent_model = get_env_or_input("CC_CUSTOM_SUBAGENT_MODEL", "Enter your CC_CUSTOM_SUBAGENT_MODEL (optional)", allow_empty=True)
    api_key = get_env_or_input("CC_CUSTOM_API_KEY", "Enter your CC_CUSTOM_API_KEY (can be empty)", allow_empty=True)
    env = {
        "ANTHROPIC_AUTH_TOKEN": api_key,
        "ANTHROPIC_BASE_URL": endpoint,
        "API_TIMEOUT_MS": "3000000",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": 1,
        "CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK": 1,
        "CLAUDE_CODE_EFFORT_LEVEL": "max",
        "ANTHROPIC_MODEL": model,
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": haiku_model,
        "ANTHROPIC_DEFAULT_SONNET_MODEL": sonnet_model,
        "ANTHROPIC_DEFAULT_OPUS_MODEL": opus_model
    }
    if subagent_model:
        env["CLAUDE_CODE_SUBAGENT_MODEL"] = subagent_model
    return env


def update_settings_env(new_env):
    if not SETTINGS_PATH.exists():
        print(f"Settings file not found: {SETTINGS_PATH}")
        return
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        settings = json.load(f)
    settings.setdefault("env", {})
    for k, v in new_env.items():
        settings["env"][k] = v
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
    print("Settings updated successfully.")


def curses_select(stdscr, items, current_idx, title):
    """Interactive single-select UI."""
    import curses
    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_WHITE, -1)

    cursor = current_idx
    n = len(items)

    def draw():
        stdscr.clear()
        stdscr.addstr(0, 0, title, curses.A_BOLD | curses.color_pair(1))
        stdscr.addstr(1, 0, "Up/Down move | Enter confirm | q quit", curses.color_pair(3))
        stdscr.addstr(2, 0, "-" * 50, curses.color_pair(1))

        for i, (label, detail) in enumerate(items):
            marker = ">" if cursor == i else " "
            color = curses.color_pair(2) if cursor == i else curses.color_pair(4)
            attr = curses.A_REVERSE if cursor == i else 0
            try:
                stdscr.addstr(4 + i, 0, f"{marker} {label}", attr | color)
                if detail:
                    stdscr.addstr(4 + i, 25, detail, curses.A_DIM | curses.color_pair(3))
            except curses.error:
                pass

        stdscr.refresh()

    while True:
        draw()
        key = stdscr.getch()

        if key == curses.KEY_UP or key == ord("k"):
            cursor = (cursor - 1) % n
        elif key == curses.KEY_DOWN or key == ord("j"):
            cursor = (cursor + 1) % n
        elif key in (curses.KEY_ENTER, 10, 13):
            return cursor
        elif key in (ord("q"), 27):
            return None


def run_curses_select(items, current_idx, title):
    import curses
    return curses.wrapper(curses_select, items, current_idx, title)


def main():
    current_provider = get_current_provider()
    current_model = get_current_model()

    items = []
    for key, (label, url, _) in PROVIDERS.items():
        detail = f"({url})" if url else ""
        items.append((label, detail))

    if current_provider and current_provider in PROVIDERS:
        current_idx = list(PROVIDERS.keys()).index(current_provider)
    else:
        current_idx = 0

    title = f"Select Claude Code Model (current: {current_model or 'unknown'})"
    result = run_curses_select(items, current_idx, title)

    if result is None:
        print("Cancelled.")
        return

    selected_key = list(PROVIDERS.keys())[result]
    label, _, env = PROVIDERS[selected_key]

    if selected_key == "GLM":
        api_key = get_env_or_input("GLM_API_KEY", "Enter your GLM_API_KEY")
        env = GLM_ENV.copy()
        env["ANTHROPIC_AUTH_TOKEN"] = api_key
        update_settings_env(env)
    elif selected_key == "MiniMax":
        api_key = get_env_or_input("MINIMAX_API_KEY", "Enter your MINIMAX_API_KEY")
        env = MINIMAX_ENV.copy()
        env["ANTHROPIC_AUTH_TOKEN"] = api_key
        update_settings_env(env)
    elif selected_key == "MiMo":
        api_key = get_env_or_input("MIMO_API_KEY", "Enter your MIMO_API_KEY")
        env = MIMO_ENV.copy()
        env["ANTHROPIC_AUTH_TOKEN"] = api_key
        update_settings_env(env)
    elif selected_key == "DeepSeek":
        api_key = get_env_or_input("DEEPSEEK_API_KEY", "Enter your DEEPSEEK_API_KEY")
        env = DEEPSEEK_ENV.copy()
        env["ANTHROPIC_AUTH_TOKEN"] = api_key
        update_settings_env(env)
    elif selected_key == "Custom":
        env = build_custom_env()
        update_settings_env(env)


if __name__ == "__main__":
    _enable_windows_ansi()
    _ensure_curses()
    main()