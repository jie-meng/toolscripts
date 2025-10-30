#!/usr/bin/env python3
import os
import subprocess
import json
from pathlib import Path
import sys
import shutil

# --- Configuration ---
TOOLS = [
    "@anthropic-ai/claude-code",
    "@github/copilot",
    "@google/gemini-cli",
    "opencode-ai",
    "@iflow-ai/iflow-cli",
    "@qwen-code/qwen-code",
]

# --- Colors ---
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'

# --- Logging ---
def log_info(msg): print(f"{Colors.BLUE}[INFO]{Colors.NC} {msg}")
def log_success(msg): print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {msg}")
def log_warning(msg): print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {msg}")
def log_error(msg): print(f"{Colors.RED}[ERROR]{Colors.NC} {msg}")

# --- Command Execution ---
def run_command(command, shell=False, check=False, stream=False):
    if stream:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=shell)
        output = []
        for line in iter(process.stdout.readline, ' '):
            if not line:
                break
            sys.stdout.write(line)
            output.append(line)
        process.wait()
        return process.returncode, "".join(output)

    try:
        process = subprocess.run(command, capture_output=True, text=True, shell=shell, check=check)
        return process.returncode, process.stdout.strip()
    except subprocess.CalledProcessError as e:
        return e.returncode, e.stdout.strip()

# --- Core Logic ---
_npm_root = None
def get_npm_root(reset=False):
    global _npm_root
    if _npm_root is None or reset:
        _, stdout = run_command(['npm', 'root', '-g'])
        _npm_root = stdout
    return _npm_root

def get_installed_tools(reset_cache=False):
    installed = {}
    npm_root = get_npm_root(reset=reset_cache)
    if not npm_root:
        log_error("Could not determine npm root directory.")
        return {}
    for tool in TOOLS:
        pkg_path = Path(npm_root) / tool / "package.json"
        if pkg_path.is_file():
            try:
                with pkg_path.open('r') as f:
                    data = json.load(f)
                    installed[tool] = data.get('version', 'unknown')
            except (json.JSONDecodeError, IOError):
                installed[tool] = 'error'
    return installed

def get_latest_version(package_name):
    _, stdout = run_command(['npm', 'view', package_name, 'version'])
    return stdout

def show_status(reset_cache=False):
    log_info("Checking tool status for current node version...")
    print()
    installed_tools = get_installed_tools(reset_cache=reset_cache)
    for tool in TOOLS:
        if tool in installed_tools:
            version = installed_tools[tool]
            print(f"  {Colors.GREEN}✓{Colors.NC} {tool}@{version}")
        else:
            print(f"  {Colors.RED}✗{Colors.NC} {tool} (not installed)")
    print()

def select_from_list(title, items):
    log_info(title)
    if not items:
        log_warning("No items to select from.")
        return None

    for i, item in enumerate(items, 1):
        print(f"{i}. {item}")
    print("0. Back to main menu")

    while True:
        try:
            choice = int(input("Enter your choice: "))
            if 0 <= choice <= len(items):
                return items[choice - 1] if choice > 0 else None
        except ValueError:
            pass
        log_error("Invalid selection.")

# --- Menu Actions ---
def install_missing_tools():
    installed = get_installed_tools()
    missing = [tool for tool in TOOLS if tool not in installed]
    if not missing:
        log_success("All tools are already installed.")
        return

    log_info(f"Installing {len(missing)} missing tool(s)...")
    for tool in missing:
        log_info(f"Installing {tool}...")
        run_command(['npm', 'install', '-g', f'{tool}@latest'], stream=True)

def install_specific_tool():
    installed = get_installed_tools()
    missing = [tool for tool in TOOLS if tool not in installed]
    if not missing:
        log_success("All tools are already installed.")
        return

    tool_to_install = select_from_list("Select a tool to install:", missing)
    if tool_to_install:
        log_info(f"Installing {tool_to_install}...")
        run_command(['npm', 'install', '-g', f'{tool_to_install}@latest'], stream=True)

def upgrade_all_tools():
    installed = get_installed_tools()
    if not installed:
        log_warning("No tools are installed. Nothing to upgrade.")
        return

    log_info(f"Checking for updates for {len(installed)} installed tool(s)...")
    for tool, current_version in installed.items():
        log_info(f"Checking {tool}...")
        latest_version = get_latest_version(tool)
        if not latest_version:
            log_error(f"Could not get latest version for {tool}")
            continue

        log_info(f"Installed version: {current_version}")
        log_info(f"Latest version: {latest_version}")

        if current_version == latest_version:
            log_success(f"{tool} is already up to date.")
        else:
            log_info(f"Updating {tool} from {current_version} to {latest_version}...")
            run_command(['npm', 'install', '-g', f'{tool}@latest'], stream=True)
        print()

def uninstall_specific_tool():
    installed = list(get_installed_tools().keys())
    if not installed:
        log_warning("No tools are installed.")
        return

    tool_to_uninstall = select_from_list("Select a tool to uninstall:", installed)
    if tool_to_uninstall:
        log_info(f"Uninstalling {tool_to_uninstall}...")
        run_command(['npm', 'uninstall', '-g', tool_to_uninstall], stream=True)

def uninstall_all_tools():
    installed = list(get_installed_tools().keys())
    if not installed:
        log_warning("No tools are installed.")
        return

    try:
        confirm = input(f"Are you sure you want to uninstall all {len(installed)} tools? (y/N) ")
        if confirm.lower() != 'y':
            log_info("Uninstallation cancelled.")
            return
    except (EOFError, KeyboardInterrupt):
        log_info("\nUninstallation cancelled.")
        return

    for tool in installed:
        log_info(f"Uninstalling {tool}...")
        run_command(['npm', 'uninstall', '-g', tool], stream=True)

# --- Node Version Management ---
def manage_versions_with_fnm():
    log_info("Using fnm to manage Node.js versions.")

    ret_code, stdout = run_command(['fnm', 'list'])

    if ret_code != 0 or not stdout:
        log_warning("No Node.js versions found by fnm.")
        log_info("You can install a Node.js version using a command like: 'fnm install lts'")
        return

    versions = [line.replace('*', '').replace('(default)', '').strip().split()[0] for line in stdout.splitlines() if line.strip()]

    if not versions:
        log_warning("No Node.js versions found by fnm.")
        log_info("You can install a Node.js version using a command like: 'fnm install lts'")
        return

    _, original_version_str = run_command(['fnm', 'current'])
    original_version = original_version_str.strip()

    display_versions = [f"{v} (current)" if v == original_version else v for v in versions]
    selected_display = select_from_list("Select a Node.js version to manage:", display_versions)
    if not selected_display:
        return

    selected_version = selected_display.split(' ')[0]
    log_info(f"Managing tools for node version {selected_version}...")

    script_path = Path(__file__).resolve()
    os.environ['_AI_CLI_INSTALL_CHILD'] = 'true'

    command_to_run = [
        'fnm', 'exec', f'--using={selected_version}',
        sys.executable, str(script_path)
    ]

    run_command(command_to_run, stream=True)

    if '_AI_CLI_INSTALL_CHILD' in os.environ:
        del os.environ['_AI_CLI_INSTALL_CHILD']



def manage_versions_with_nvm():
    nvm_dir = os.environ.get("NVM_DIR", Path.home() / ".nvm")
    nvm_sh = Path(nvm_dir) / "nvm.sh"
    if not nvm_sh.is_file():
        log_error("nvm.sh not found.")
        return

    log_info("Using nvm to manage Node.js versions.")

    def run_nvm_command(cmd):
        return subprocess.run(f'. "{nvm_sh}"; {cmd}', shell=True, capture_output=True, text=True, executable='/bin/bash')

    result = run_nvm_command('nvm ls')
    versions = [line.split()[0] for line in result.stdout.splitlines() if '->' not in line and line.strip()]
    original_version = run_nvm_command('nvm current').stdout.strip()

    display_versions = [f"{v} (current)" if v == original_version else v for v in versions]
    selected_display = select_from_list("Select a Node.js version to manage:", display_versions)
    if not selected_display:
        return

    selected_version = selected_display.split(' ')[0]
    log_info(f"Managing tools for node version {selected_version}...")

    script_path = Path(__file__).resolve()
    os.environ['_AI_CLI_INSTALL_CHILD'] = 'true'
    run_nvm_command(f'nvm exec {selected_version} {sys.executable} {script_path}')
    if '_AI_CLI_INSTALL_CHILD' in os.environ:
        del os.environ['_AI_CLI_INSTALL_CHILD']

def manage_all_node_versions():
    if shutil.which("fnm"):
        manage_versions_with_fnm()
    elif (Path.home() / ".nvm" / "nvm.sh").is_file():
        manage_versions_with_nvm()
    else:
        log_error("This feature requires 'fnm' or 'nvm' to manage Node.js versions.")
        log_info("Please install one of these tools to use this feature.")

# --- Main Loop ---
def main_loop(reset_cache=False):
    while True:
        show_status(reset_cache=reset_cache)
        reset_cache = False

        print("Please choose an option:")
        menu = {
            '1': "Install all missing tools",
            '2': "Install a specific tool",
            '3': "Upgrade all installed tools",
            '4': "Uninstall a specific tool",
            '5': "Uninstall all tools",
        }
        if not os.environ.get('_AI_CLI_INSTALL_CHILD'):
            menu['6'] = "Manage tools across all node versions (fnm or nvm)"

        menu['0'] = "Exit"

        for k, v in menu.items():
            print(f"{k}. {v}")

        try:
            choice = input("\nEnter your choice: ")
        except (EOFError, KeyboardInterrupt):
            choice = '0'

        print()

        if choice == '1': install_missing_tools()
        elif choice == '2': install_specific_tool()
        elif choice == '3': upgrade_all_tools()
        elif choice == '4': uninstall_specific_tool()
        elif choice == '5': uninstall_all_tools()
        elif choice == '6' and '6' in menu: manage_all_node_versions()
        elif choice == '0':
            log_success("Operations complete. Exiting.")
            break
        else:
            log_error("Invalid option. Please try again.")

        if os.environ.get('_AI_CLI_INSTALL_CHILD'):
            break
        print()


if __name__ == "__main__":
    if not shutil.which("npm") or not shutil.which("node"):
        log_error("npm and node must be installed and in your PATH.")
        sys.exit(1)
    main_loop()
