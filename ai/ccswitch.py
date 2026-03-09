import os
import json
from pathlib import Path

# Path to Claude settings file
SETTINGS_PATH = Path.home() / ".claude" / "settings.json"

# GLM and MiniMax configuration templates
GLM_ENV = {
    "ANTHROPIC_AUTH_TOKEN": None,  # To be filled
    "ANTHROPIC_BASE_URL": "https://open.bigmodel.cn/api/anthropic",
    "API_TIMEOUT_MS": "3000000",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": 1,
    "ANTHROPIC_MODEL": "glm-4.7",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "glm-4.5-air",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "glm-4.7",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "glm-5"
}
MINIMAX_ENV = {
    "ANTHROPIC_AUTH_TOKEN": None,  # To be filled
    "ANTHROPIC_BASE_URL": "https://api.minimax.io/anthropic",
    "API_TIMEOUT_MS": "3000000",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": 1,
    "ANTHROPIC_MODEL": "MiniMax-M2.5",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "MiniMax-M2.5",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "MiniMax-M2.5",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "MiniMax-M2.5"
}

def get_env_or_input(env_var, prompt, allow_empty=False):
    """
    Get value from environment variable or prompt user for input.
    """
    value = os.environ.get(env_var)
    if value or (allow_empty and env_var in os.environ):
        print(f"Found {env_var} in environment. Using it.")
    else:
        value = input(f"{prompt}: ").strip()
    return value

def build_custom_env():
    """
    Build custom provider env settings from env vars or interactive input.
    """
    endpoint = get_env_or_input("CC_CUSTOM_ENDPOINT", "Enter your CC_CUSTOM_ENDPOINT")
    model = get_env_or_input("CC_CUSTOM_MODEL", "Enter your CC_CUSTOM_MODEL")
    sonnet_model = get_env_or_input(
        "CC_CUSTOM_DEFAULT_SONNET_MODEL",
        "Enter your CC_CUSTOM_DEFAULT_SONNET_MODEL"
    )
    opus_model = get_env_or_input(
        "CC_CUSTOM_DEFAULT_OPUS_MODEL",
        "Enter your CC_CUSTOM_DEFAULT_OPUS_MODEL"
    )
    haiku_model = get_env_or_input(
        "CC_CUSTOM_DEFAULT_HAIKU_MODEL",
        "Enter your CC_CUSTOM_DEFAULT_HAIKU_MODEL"
    )
    api_key = get_env_or_input(
        "CC_CUSTOM_API_KEY",
        "Enter your CC_CUSTOM_API_KEY (can be empty)",
        allow_empty=True
    )
    return {
        "ANTHROPIC_AUTH_TOKEN": api_key,
        "ANTHROPIC_BASE_URL": endpoint,
        "API_TIMEOUT_MS": "3000000",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": 1,
        "ANTHROPIC_MODEL": model,
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": haiku_model,
        "ANTHROPIC_DEFAULT_SONNET_MODEL": sonnet_model,
        "ANTHROPIC_DEFAULT_OPUS_MODEL": opus_model
    }

def update_settings_env(new_env):
    """
    Update only the relevant env fields in settings.json.
    """
    if not SETTINGS_PATH.exists():
        print(f"Settings file not found: {SETTINGS_PATH}")
        return
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        settings = json.load(f)
    # Ensure 'env' exists
    settings.setdefault("env", {})
    # Update only the relevant fields
    for k, v in new_env.items():
        settings["env"][k] = v
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
    print("Settings updated successfully.")

def main():
    print("Select Claude Code Model:")
    print("1. GLM Code Plan")
    print("2. MiniMax Code Plan")
    print("3. Custom Endpoint/Model/API Key")
    choice = input("Enter 1, 2 or 3: ").strip()
    if choice == "1":
        # GLM Code Plan
        api_key = get_env_or_input("GLM_API_KEY", "Enter your GLM_API_KEY")
        env = GLM_ENV.copy()
        env["ANTHROPIC_AUTH_TOKEN"] = api_key
        update_settings_env(env)
    elif choice == "2":
        # MiniMax M2
        api_key = get_env_or_input("MINIMAX_API_KEY", "Enter your MINIMAX_API_KEY")
        env = MINIMAX_ENV.copy()
        env["ANTHROPIC_AUTH_TOKEN"] = api_key
        update_settings_env(env)
    elif choice == "3":
        # Custom provider
        env = build_custom_env()
        update_settings_env(env)
    else:
        print("Invalid choice. Please run the script again.")

if __name__ == "__main__":
    main()
