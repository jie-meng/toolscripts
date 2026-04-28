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

## 4. Reuse first (DRY) — the reflex before writing code

Every new command, bug fix, or refactor starts with a **reuse reflex** pass.
Duplicated code is the biggest source of long-term drift here, so we treat
reuse as a default behavior, not a stretch goal.

### The 3-question check (do this *before* writing code)

For each non-trivial bit of behavior you're about to write:

1. **Is there a `core/` helper for this?** Skim `src/toolscripts/core/` —
   `log`, `colors`, `shell`, `clipboard`, `prompts`, `platform`,
   `ui_curses`. If yes, use it. (See §5 for the table.)
2. **Is there a domain-shared package?** ADB plumbing → `toolscripts.adb`,
   git plumbing → `toolscripts.git_utils`. Reuse before writing yet another
   `subprocess.run(["adb", ...])` / `subprocess.run(["git", ...])`.
3. **Has another command already solved it?** Grep the relevant
   `commands/<domain>/` folder for keywords. If yes, see "When you find
   duplication" below.

### When you find duplication

| Situation | What to do |
|---|---|
| Helper exists and fits | Use it. Done. |
| Helper exists but missing one option | **Extend the helper** with a kwarg (backwards-compatible default). Don't fork. |
| Two commands have near-identical code, you're about to write a third copy | **Stop and lift it.** Move shared code into `core/` (or `adb/` / `git_utils/` for domain-specific), then route old + new through it — in the **same change**, not "later". |

**Threshold is two.** First time, fine, write it inline. Second time it's
about to appear, lift it. Don't wait for "three strikes" — by then the
call sites have drifted.

### Hard rules

- A command **must not** import from another command. If you're tempted,
  lift the shared code into `core/` (or `adb/` / `git_utils/`).
- No raw `subprocess` — use `core.shell.run` / `capture` / `try_run` /
  `which` / `require`.
- No raw ANSI color escapes — use `core.colors`.
- No hand-rolled prompt loops — use `core.prompts.yes_no` / `choice` /
  `ask`.
- No hand-rolled curses pickers — use `core.ui_curses.select_one` /
  `select_many` / `browse_commands` (see §5).
- No DIY clipboard fallbacks — use `core.clipboard.copy_to_clipboard`.
- No DIY OS detection — use `core.platform.is_macos` / `is_linux` /
  `is_windows` / `require_platform`.

### When you genuinely need something new

- Pure utility, useful across domains → add to `core/`.
- Specific to one external tool's plumbing → add to `adb/` or `git_utils/`
  (or create a new domain-shared package if a third tool earns it).
- Never put a "shared helper" inside a `commands/...` module just because
  you happen to be editing that file — the next person looking for the
  same helper will not find it there.

When you create a new shared helper, add a row to §5 below so the next
agent discovers it on the reflex pass.

### Concrete examples already in the repo

- `agents-setup` and `agents-cleanup` share their AI tool list via
  `commands/ai/_integrations.py` (a domain-shared `Integration` dataclass
  + `INTEGRATIONS` list) — **not** by importing from each other.
- `aido-models` reused / generalized the curses single-picker rather than
  copying multi-select code; the result lives in
  `core.ui_curses.select_one`.
- Every `android-*` command goes through `toolscripts.adb` for ADB calls
  so timeouts, error messages, and single-vs-multi-device handling are
  consistent.

---

## 5. Core helpers (use these instead of rolling your own)

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
| Pick one item from a list (curses) | `select_one(title, items, *, default_index=None)` → `int \| None` | `toolscripts.core.ui_curses` |
| Pick zero or more items from a list (curses) | `select_many(title, items, *, preselected=None, disabled=None)` → `list[int] \| None` | `toolscripts.core.ui_curses` |
| Drill-down browser (group → item + detail pane) | `browse_commands(title, entries, *, detail_provider=...)` | `toolscripts.core.ui_curses` |

`require_platform` prints a yellow warning and exits **0** (intentional no-op,
not a failure) on unsupported OSes.

### Pickers — always reuse, almost never roll your own

When a command needs the user to choose from a list, **default to** the
shared pickers in `toolscripts.core.ui_curses`:

| Need | Helper |
|---|---|
| Pick exactly one item | `select_one(title, items, *, default_index=None)` |
| Pick any subset of items | `select_many(title, items, *, preselected=None, disabled=None)` |
| Drill into a tree (group → item + detail) | `browse_commands(title, entries, *, detail_provider=...)` |

Reference implementations in the codebase:

- `select_one` → `commands/ai/aido.py` (`aido-models` model picker).
- `select_many` → `commands/ai/agents_setup.py` and `agents_cleanup.py`
  (multi-tool pick with `disabled=` for not-installed tools).
- `browse_commands` → `commands/system/list_commands.py`
  (`toolscripts-list -i`).

Roll your own `curses.wrapper(...)` loop **only** when you need behavior the
helpers don't model: live-updating rows from a background worker, running
external commands without leaving the UI, or non-list/multi-pane layouts.
The reference for that pattern is `commands/ai/npm_tools.py`. If you're
doing plain "pick N of M" / "pick 1 of M", **stop** and use the helpers
above — do not copy the npm-tools template.

(Legacy aliases `single_select` / `multi_select` still work but are
deprecated in new code.)

---

## 6. Dependencies

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

## 7. Bundled data resources

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

## 8. External binaries

If a command shells out to an external tool (`adb`, `gh`, `ffmpeg`,
`docker`, ...):

1. State the requirement in the module docstring.
2. Call `core.shell.require("the-binary")` (or `which(...)` if optional)
   early in `main()` so the failure is fast and clear.

---

## 9. Logging levels

| Method | Color | Use for |
|---|---|---|
| `log.debug(...)` | grey | diagnostic detail (hidden by default) |
| `log.info(...)` | blue | what the command is currently doing |
| `log.success(...)` | green | a milestone or completion |
| `log.warning(...)` | yellow | something off but recoverable |
| `log.error(...)` | red | the command can't do what was asked |

Logs go to **stderr**. Real human output goes to **stdout**.

---

## 10. Style

- Python 3.10+, `from __future__ import annotations` at the top of new files.
- Type hints encouraged where they help.
- `ruff check src/ && ruff format src/` must pass.
- Only comment the *why*, not the *what*. Don't narrate code.
- Keep the line length under 100 chars (ruff is configured that way).

---

## 11. Bash scripts (`scripts/`)

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

## 12. README tables

`README.md` and `README.zh-CN.md` both have a "命令一览 / Available commands"
table grouped by domain. Whenever you add, rename, or remove a command, the
matching row(s) in **both** READMEs must be updated.

The English table lives under the heading `## Available commands` and the
Chinese table under `## 命令一览`. Keep the row order grouped by domain and
matching between the two files.

---

## 13. Editable install reload

After editing `[project.scripts]` (adding/removing/renaming an entry point),
the user has to refresh the install:

```bash
./manage.py install --force      # pipx (recommended)
./manage.py install --pip --force
```

Tell them this when finishing the change. Pure source edits to a command's
body don't need a reinstall — the editable install picks them up directly.
