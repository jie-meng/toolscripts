# 🤖 Context for AI Assistants (AGENTS.md)

This file provides context, coding conventions, and architectural guidelines for AI coding assistants (like Claude, Cursor, Copilot, etc.) working on the `toolscripts` repository. 

**Whenever you are asked to write, modify, or debug code in this repository, please adhere to the following rules.**

## 1. Project Context & Philosophy
- **Purpose**: `toolscripts` is a monorepo containing a diverse collection of single-purpose utility scripts. Its goal is to "make work simple."
- **Environment**: Primarily targeted for Unix/Linux/macOS environments.
- **Languages**: Python 3 (primary) and Bash/Shell.
- **Design Principle**: Scripts should be standalone, fast, and require minimal external setup. Avoid over-engineering. If a task can be solved with standard libraries, do not introduce external dependencies.

## 2. Directory Structure Conventions
- Scripts are organized by their domain (e.g., `android/` for ADB scripts, `time/` for timestamp converters, `git/` for git operations).
- The `shell/` directory contains executable wrappers, aliases, or short shell scripts that invoke the Python scripts from other directories.
- If you create a new script, place it in the most relevant domain folder, and consider whether a corresponding executable wrapper should be added to `shell/`.

## 3. Python Coding Standards
- **Version**: Python 3.x (Use modern Python features like f-strings, type hints where helpful, but remain compatible with Python 3.8+).
- **Shebang**: All executable Python scripts must start with `#!/usr/bin/env python3`.
- **Dependencies**: 
  - Prefer the Python Standard Library (`os`, `sys`, `json`, `subprocess`, `pathlib`, `argparse`, `datetime`, etc.).
  - If a 3rd-party library is absolutely necessary, it must be added to `requirements.txt`.
- **CLI Design**: 
  - For anything taking more than one argument, use the built-in `argparse` module.
  - Provide a clear `--help` description.
  - Handle exceptions gracefully (e.g., catching `FileNotFoundError` or `subprocess.CalledProcessError`) and print human-readable error messages to `sys.stderr`.
- **Output Colors**: Use colors for terminal output to improve readability:
  - Green for success messages
  - Red for error messages (print to stderr)
  - Yellow for warning messages
  - Use ANSI escape codes or a simple helper:
    ```python
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[0;33m'
    NC = '\033[0m'  # No Color
    ```
- **Formatting & Linting**: Follow PEP 8 guidelines. Keep code clean and readable.

## 4. Shell Scripting Standards
- **Shebang**: Always start with `#!/usr/bin/env bash` or `#!/bin/sh`.
- **Robustness**: 
  - Use `set -e` to exit on errors.
  - Quote variables (e.g., `"$FILE"`) to prevent word splitting issues.
- **Permissions**: New shell scripts must be made executable (`chmod +x`).
- **Output Colors**: Use colors for terminal output to improve readability:
  - Green for success messages
  - Red for error messages (print to stderr)
  - Yellow for warning messages
  - Define color variables at the top of the script:
    ```bash
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    NC='\033[0m' # No Color
    ```

## 5. Modifying Existing Code
- **Preserve Behavior**: Do not break the existing CLI interface of a script unless explicitly requested, as other scripts or user habits might depend on it.
- **Refactoring**: Keep changes minimal and focused on the user's request. Avoid refactoring unrelated parts of the codebase.

## 6. How to Help the User
- When the user asks for a new tool, ask clarifying questions if the domain isn't obvious, then write the script and tell them exactly where to place it (or write it directly if you have filesystem access).
- If the tool requires specific system dependencies (e.g., `adb`, `ffmpeg`, `imagemagick`), explicitly state them in the script's docstring or output.
