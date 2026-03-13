# ToolScripts

A comprehensive collection of utility scripts (primarily Python and Bash) to streamline development, system administration, and daily workflows across various platforms.

## 🚀 Overview

ToolScripts acts as a personal "Swiss Army Knife" for developers. It categorizes scripts by domain (Android, iOS, Git, Database, Text processing, AI tooling) so that they can be easily executed or linked via the `shell/` directory.

## 📂 Project Structure

- `ai/`: Tools for managing and integrating AI agents and LLM providers.
- `android/` & `ios/`: Mobile development utilities (ADB sync, screen recording, logcat, simulator management).
- `calc/` & `time/`: Hex/Dec/Bin calculators and Unix timestamp conversions.
- `codec/` & `file/`: Format converters (JSON decoding, text-to-numbers, Markdown).
- `git/`: Git workflow enhancements (patch applications, branch cleanup).
- `docker/`: Docker registry scripts and custom environments.
- `plot/`: Charting and visualization scripts (Mermaid generation).
- `shell/`: Executable wrappers and shell aliases that expose these scripts globally.
- *...and many more domain-specific directories.*

## 🛠️ Installation & Usage

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd toolscripts
   ```

2. **Install dependencies:**
   Some Python scripts require external libraries (e.g., Pillow, openpyxl, matplotlib).
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the Environment:**
   You can add the `shell/` directory to your system `PATH` to access these utilities from anywhere:
   ```bash
   export PATH="/path/to/toolscripts/shell:$PATH"
   ```

## 📜 License

This project is licensed under the terms provided in the [LICENSE](./LICENSE) file.
