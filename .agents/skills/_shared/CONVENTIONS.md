# toolscripts conventions cheat-sheet

This is a tight, copy-friendly reference for the **toolscripts** monorepo,
extracted from `AGENTS.md`. The three `toolscripts-command-*` skills link
here so they can stay short.

---

## 1. Layout (where everything lives)

```
src/toolscripts/
  core/             # pure utilities (log, colors, shell, prompts, platform...)
  adb/              # ADB helpers shared by android-* commands
  git_utils/        # git helpers shared by git-* commands
  commands/<domain>/<snake_name>.py    # one file per command
  data/<domain>/    # bundled non-code resources (agent prompts, configs...)
scripts/            # rare bash-only scripts (last resort)
tests/              # pytest suite
pyproject.toml      # [project.scripts] entry points + extras
README.md           # English commands table
README.zh-CN.md     # Chinese commands table
AGENTS.md           # full conventions
```

### Layering rules

- `core/` may not import from `adb/`, `git_utils/`, or `commands/`.
- `adb/` and `git_utils/` may import from `core/`.
- `commands/` may import from anything in `core/`, `adb/`, `git_utils/`.
- A command must **not** import from another command. Lift shared code to
  `core/` (or to a domain helper package) instead.

### Existing domains under `commands/`

`adb` (helpers only), `ai`, `android`, `calc`, `codec`, `cpp`, `credential`,
`db`, `docker`, `games`, `git`, `ios`, `media`, `security`, `system`, `text`,
`time`. Reuse one of these when it fits — only add a new domain folder when
none of them is a reasonable home.

---

## 2. Naming

| Thing | Style | Example |
|---|---|---|
| Command (user-facing) | `kebab-case` | `git-copy-diff`, `android-record` |
| Module file | `snake_case.py` | `copy_diff.py`, `record.py` |
| Domain folder | `lowercase` | `git/`, `android/` |
| Entry point in `pyproject.toml` | `kebab = "toolscripts.commands.<domain>.<snake>:main"` | `git-copy-diff = "toolscripts.commands.git.copy_diff:main"` |

Command names are user muscle memory — treat them as a stable contract.

---

## 3. Module skeleton

```python
"""``my-cmd`` - one-line summary."""

from __future__ import annotations

import argparse

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="my-cmd",
        description="Longer description shown in --help.",
    )
    parser.add_argument("input", help="...")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    log.info("doing the thing with %s", args.input)


if __name__ == "__main__":
    main()
```

Required for every command:

- `def main()` is the entry point. **No top-level side effects.**
- Use `argparse`. Always set `prog=` to the kebab-case command name.
- Always call `add_logging_flags(parser)` and `configure_from_args(args)` so
  `-v`/`-q` work uniformly.
- Print human output to **stdout**; logs (`debug/info/success/warning/error`)
  go through the logger to **stderr** so stdout stays clean for piping.
- **No shebang** in `src/toolscripts/` files (they are imported, not executed).

---

## 4. Core helpers (use these instead of rolling your own)

| Need | Use | From |
|---|---|---|
| Logging | `get_logger`, `add_logging_flags`, `configure_from_args` | `toolscripts.core.log` |
| Run external command (streaming) | `run([...])` | `toolscripts.core.shell` |
| Capture stdout | `capture([...])` | `toolscripts.core.shell` |
| Probe / require binary | `which("foo")`, `require("foo")` | `toolscripts.core.shell` |
| Best-effort run | `try_run([...])` | `toolscripts.core.shell` |
| Clipboard | `copy_to_clipboard(text)` | `toolscripts.core.clipboard` |
| Platform gate | `require_platform("macos")` (also `"linux"`, `"windows"`) | `toolscripts.core.platform` |
| Prompts | `yes_no(...)`, `choice(...)`, `ask(...)` | `toolscripts.core.prompts` |
| ANSI colors | `colors.RED`, `colors.colored(...)`, `colors_enabled(...)` | `toolscripts.core.colors` |
| Curses multi-select | `select_many(...)` | `toolscripts.core.ui_curses` |

`require_platform` prints a yellow warning and exits **0** (intentional no-op,
not a failure) on unsupported OSes.

---

## 5. Dependencies

- The base install must have **zero third-party runtime deps**. Standard
  library only.
- Anything else goes behind an extra in `pyproject.toml`:
  - `clipboard` → `pyperclip`
  - `media`     → `pillow`, `matplotlib`
  - `office`    → `openpyxl`
  - `text`      → `markdownify`, `translate`, `binaryornot`
  - `windows`   → `windows-curses` (Windows only)
- When a command needs an optional dep, **import it lazily inside `main()`**
  and surface a friendly error if missing — or, better, route through a
  `core/` helper that already does the fallback (e.g. `core.clipboard`).

```python
def main() -> None:
    try:
        import pyperclip  # noqa: F401
    except ImportError:
        log.error("clipboard support not installed; run: pipx inject toolscripts pyperclip")
        sys.exit(1)
```

If you really need a brand-new third-party dep, add it to the right extra in
`[project.optional-dependencies]` and update both READMEs' extras tables.

---

## 6. Bundled data resources

Non-code resources live under `src/toolscripts/data/<domain>/`. They ship
with the package via:

```toml
[tool.setuptools.package-data]
toolscripts = ["data/**/*"]
```

Read them at runtime through `importlib.resources`:

```python
from importlib.resources import files

text = (files("toolscripts.data.ai") / "AGENTS.md").read_text(encoding="utf-8")
```

Don't hard-code absolute paths and don't read from the source tree.

---

## 7. External binaries

If a command shells out to an external tool (`adb`, `gh`, `ffmpeg`,
`docker`, ...):

1. State the requirement in the module docstring.
2. Call `core.shell.require("the-binary")` (or `which(...)` if optional)
   early in `main()` so the failure is fast and clear.

---

## 8. Logging levels

| Method | Color | Use for |
|---|---|---|
| `log.debug(...)` | grey | diagnostic detail (hidden by default) |
| `log.info(...)` | blue | what the command is currently doing |
| `log.success(...)` | green | a milestone or completion |
| `log.warning(...)` | yellow | something off but recoverable |
| `log.error(...)` | red | the command can't do what was asked |

Logs go to **stderr**. Real human output goes to **stdout**.

---

## 9. Style

- Python 3.10+, `from __future__ import annotations` at the top of new files.
- Type hints encouraged where they help.
- `ruff check src/ && ruff format src/` must pass.
- Only comment the *why*, not the *what*. Don't narrate code.
- Keep the line length under 100 chars (ruff is configured that way).

---

## 10. Bash scripts (`scripts/`)

Bash is allowed only when Python genuinely cannot do the job (e.g. shelling
out to `yum`/`make` for system installs). When you must:

```bash
#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'
```

Mark it executable (`chmod +x`). Bash scripts are **not** registered in
`pyproject.toml`; users invoke them by path or set up their own alias.

---

## 11. README tables

`README.md` and `README.zh-CN.md` both have a "命令一览 / Available commands"
table grouped by domain. Whenever you add, rename, or remove a command, the
matching row(s) in **both** READMEs must be updated.

The English table lives under the heading `## Available commands` and the
Chinese table under `## 命令一览`. Keep the row order grouped by domain and
matching between the two files.

---

## 12. Editable install reload

After editing `[project.scripts]` (adding/removing/renaming an entry point),
the user has to refresh the install:

```bash
./manage.py install --force      # pipx (recommended)
./manage.py install --pip --force
```

Tell them this when finishing the change. Pure source edits to a command's
body don't need a reinstall — the editable install picks them up directly.
