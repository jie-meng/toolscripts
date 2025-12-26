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
    "ANTHROPIC_SMALL_FAST_MODEL": "glm-4.5-air",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "glm-4.5-air",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "glm-4.7",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "glm-4.7"
}
MINIMAX_ENV = {
    "ANTHROPIC_AUTH_TOKEN": None,  # To be filled
    "ANTHROPIC_BASE_URL": "https://api.minimax.io/anthropic",
    "API_TIMEOUT_MS": "3000000",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": 1,
    "ANTHROPIC_MODEL": "MiniMax-M2.1",
    "ANTHROPIC_SMALL_FAST_MODEL": "MiniMax-M2.1",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "MiniMax-M2.1",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "MiniMax-M2.1",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "MiniMax-M2.1"
}

def get_api_key(env_var, prompt):
    """
    Get API key from environment variable or prompt user for input.
    """
    key = os.environ.get(env_var)
    if key:
        print(f"Found {env_var} in environment. Using it.")
    else:
        key = input(f"{prompt}: ")
    return key

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
    print("2. MiniMax M2")
    choice = input("Enter 1 or 2: ").strip()
    if choice == "1":
        # GLM Code Plan
        api_key = get_api_key("GLM_API_KEY", "Enter your GLM_API_KEY")
        env = GLM_ENV.copy()
        env["ANTHROPIC_AUTH_TOKEN"] = api_key
        update_settings_env(env)
    elif choice == "2":
        # MiniMax M2
        api_key = get_api_key("MINIMAX_API_KEY", "Enter your MINIMAX_API_KEY")
        env = MINIMAX_ENV.copy()
        env["ANTHROPIC_AUTH_TOKEN"] = api_key
        update_settings_env(env)
    else:
        print("Invalid choice. Please run the script again.")

if __name__ == "__main__":
    main()

