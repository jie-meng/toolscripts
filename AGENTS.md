# Context for AI Assistants (AGENTS.md)

This file provides context, coding conventions, and architectural guidelines
for AI coding assistants (Claude, Cursor, Copilot, ...) working on the
`toolscripts` repository.

**Whenever you write, modify, or debug code in this repository, follow the
rules below.**

---

## 1. Project context

- **Purpose**: a monorepo of small, single-purpose CLI utilities. The mantra
  is "make work simple."
- **Distribution**: a single Python package, `toolscripts`, installed with
  `pip install -e .` (or `pipx install -e .` for daily global use). Each
  user-facing command is a `[project.scripts]` entry point — there is **no**
  `shell/` directory of bash wrappers any more.
- **Languages**: Python 3.10+. Bash is allowed only for the rare cases where
  Python genuinely cannot do the job (e.g. `update_vim8_centos`, which builds
  vim from source via `yum`/`make`).
- **Platforms**: macOS, Linux, Windows. Commands that are inherently
  platform-specific must call `require_platform(...)` from
  `toolscripts.core.platform` and warn-then-exit on unsupported OSes.
- **Design principle**: keep commands small, fast, and obvious. Prefer the
  Python standard library; pull in third-party deps only when they save real
  effort, and put them behind an extra in `pyproject.toml`.

---

## 2. Repository layout

```
src/toolscripts/
  __init__.py            # __version__
  core/                  # pure utilities, no business logic
    log.py               # unified colored logger
    colors.py            # ANSI helpers (with tty / NO_COLOR awareness)
    platform.py          # is_macos/linux/windows + require_platform
    shell.py             # subprocess wrappers (run/capture/which/require)
    clipboard.py         # cross-platform clipboard
    prompts.py           # interactive prompts (yes_no/choice/ask)
    ui_curses.py         # curses pickers: select_one / select_many / browse_commands
  adb/                   # ADB helpers shared by android-* commands
  git_utils/             # git helpers shared by git-* commands
  commands/              # CLI implementations, one file per command
    android/
    ios/
    time/
    git/
    ...
data/                    # bundled non-code resources (agent prompts, configs)
scripts/                 # rare bash-only scripts (last resort)
tests/                   # pytest suite
```

### Layering rules

- `core/` may not import from `adb/`, `git_utils/`, or `commands/`.
- `adb/` and `git_utils/` may import from `core/`.
- `commands/` may import from anything in `core/`, `adb/`, `git_utils/`.
- A command must **not** import from another command. If two commands need
  to share code, lift it into `core/` or a domain-shared package.

---

## 3. Reuse first (DRY)

**Every change — new command, bug fix, refactor — starts with a quick "is
this already done?" check.** Duplicated code is the single biggest source
of long-term drift in this monorepo, so we treat reuse as a default
behavior, not a stretch goal.

### 3.1 The reuse reflex (do this *before* writing code)

For each non-trivial piece of behavior you're about to write, ask:

1. **Is there already a `core/` helper for this?** Skim
   `src/toolscripts/core/` — `log`, `colors`, `shell`, `clipboard`,
   `prompts`, `platform`, `ui_curses`. If a helper already does it, use
   the helper.
2. **Is there a domain-shared package for this?** ADB-related plumbing
   lives in `src/toolscripts/adb/`; git plumbing lives in
   `src/toolscripts/git_utils/`. Reuse those before writing yet another
   `subprocess.run(["adb", ...])` or `subprocess.run(["git", ...])`.
3. **Has another command already solved this?** Grep the relevant
   `commands/<domain>/` folder for the keyword. If yes, see §3.2.

### 3.2 When you find duplication

| Situation | What to do |
|---|---|
| The shared helper exists and fits — just use it. | Use it. Done. |
| The helper exists but doesn't quite fit — close, but missing a small option. | **Extend the helper** (add a kwarg with a backwards-compatible default). Don't fork it. |
| Two commands already have near-identical code, and you're about to write a third copy. | **Stop and lift it.** Move the shared code to `core/` (or to `adb/` / `git_utils/` if it's domain-specific), have all call sites — old and new — go through the helper. Do this in the **same change**, not "later". |
| The would-be shared code is platform-specific, depends on a third-party library, or has fallback logic | All the more reason to centralize it once: the fallback / version check / try-import block belongs in `core/`, not duplicated in N commands. |

The threshold is **two**. The first time you write a piece of logic, fine,
write it inline. The second time it's about to appear, lift it. Don't wait
for "three strikes" — by then the call sites have already drifted.

### 3.3 Hard rules

- A command **must not** `import` from another command. If you're tempted,
  that's the signal to lift code into `core/` (or `adb/` / `git_utils/`).
- Don't reach for `subprocess` directly — `core.shell` (`run`, `capture`,
  `try_run`, `which`, `require`) covers the common cases and gives you
  consistent error handling.
- Don't roll your own ANSI color escapes — use `core.colors`.
- Don't roll your own prompt loops — use `core.prompts.yes_no` /
  `choice` / `ask`.
- Don't roll your own curses picker — use `core.ui_curses.select_one` /
  `select_many` / `browse_commands` (see §6 *Interactive UIs* below for the
  decision tree).
- Don't reimplement clipboard fallbacks — `core.clipboard.copy_to_clipboard`
  already handles the cross-platform mess.
- Don't reimplement OS detection — use `core.platform.is_macos` /
  `is_linux` / `is_windows` / `require_platform`.

### 3.4 If you genuinely need something new

If the helper you need doesn't exist anywhere:

1. Add it to **`core/`** if it has no business logic (pure utility, useful
   across domains).
2. Add it to **`adb/`** or **`git_utils/`** if it's specific to one
   external tool's plumbing.
3. Don't add it to a `commands/...` module just because you happen to be
   editing that file. The next person looking for the same helper will
   never find it there.

When you create a new shared helper, update the **Core helpers** table in
`.agents/skills/_shared/CONVENTIONS.md` (§5 there) so future agents discover
it on the reuse reflex pass. If the helper introduces a new category worth
its own AGENTS.md section (rare), add a section here too.

### 3.5 Concrete examples from this repo

- `agents-setup` and `agents-cleanup` both need to know about the same set
  of AI tool integrations (Claude, Cursor, Codex, ...). The `Integration`
  dataclass and the `INTEGRATIONS` list live once in
  `commands/ai/_integrations.py`, **not** duplicated across the two
  commands.
- `aido-models` needed an interactive single-choice picker. Instead of
  copying the multi-select curses code from `agents-setup`, the picker
  was generalized into `core.ui_curses.select_one` so both commands share
  the same curses skeleton. (See §6 *Interactive UIs*.)
- ADB device probing is centralized in `src/toolscripts/adb/` so every
  `android-*` command speaks to ADB the same way (same timeout, same
  error message, same single-vs-multi-device handling).

---

## 4. Adding a new command

Pick a domain, create the module, register the entry point, done.

### 4.1 File layout

```
src/toolscripts/commands/<domain>/<snake_name>.py
```

- File names use `snake_case` (Python convention).
- Command names exposed to users use `kebab-case` (terminal convention).
- Command names should be stable — they are user-facing muscle memory.

### 4.2 Module skeleton

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

Required:
- `def main()` is the entry point. No top-level side effects.
- Use `argparse` for any input. Always set `prog=` to the kebab-case command
  name so `--help` shows the right thing.
- Always call `add_logging_flags(parser)` and `configure_from_args(args)` so
  `-v`/`-q` work uniformly across every command.
- Print human output to **stdout**; print logs (debug/info/warn/error) via
  the logger which goes to **stderr**. This keeps stdout clean for piping.

### 4.3 Register the entry point

Add a line to `[project.scripts]` in `pyproject.toml`:

```toml
my-cmd = "toolscripts.commands.<domain>.<snake_name>:main"
```

After editing, re-run `pip install -e .` (or `pipx reinstall toolscripts`).

### 4.4 Platform gating

If the command only works on a subset of OSes:

```python
from toolscripts.core.platform import require_platform

def main() -> None:
    require_platform("macos")             # or "macos", "linux"
    ...
```

`require_platform` prints a yellow warning and exits with status `0` (the
command is an intentional no-op on this OS, not a failure).

### 4.5 External commands

Use `toolscripts.core.shell` instead of raw `subprocess`:

```python
from toolscripts.core.shell import run, capture, require, CommandNotFoundError

require("adb")                       # raises if not on PATH
run(["adb", "devices"])              # streams output to user
sha = capture(["git", "rev-parse", "HEAD"])
```

---

## 5. Logging

Use `toolscripts.core.log.get_logger(__name__)`. Levels:

| Method            | Level    | Color  | When                                   |
| ----------------- | -------- | ------ | -------------------------------------- |
| `log.debug(...)`  | DEBUG    | grey   | diagnostic info, hidden by default     |
| `log.info(...)`   | INFO     | blue   | what the command is doing              |
| `log.success(...)`| SUCCESS  | green  | a milestone or completion              |
| `log.warning(...)`| WARNING  | yellow | something off but recoverable          |
| `log.error(...)`  | ERROR    | red    | the command can't do what was asked    |

The logger writes to **stderr**, auto-disables ANSI colors when stderr is not
a TTY, and respects `NO_COLOR=1` / `FORCE_COLOR=1` per the
[NO_COLOR convention](https://no-color.org/).

---

## 6. Interactive UIs (pickers)

When a command needs the user to choose from a list, **always prefer the
shared pickers in `core.ui_curses`** over rolling a fresh curses loop or a
hand-written numbered prompt. This keeps every command's picker consistent
(same keys, same colors, same Esc/q behavior).

| Need | Use | Returns |
|---|---|---|
| Pick exactly one item | `select_one(title, items, *, default_index=None)` | `int` index or `None` (cancel) |
| Pick zero or more items | `select_many(title, items, *, preselected=None, disabled=None)` | `list[int]` indices or `None` (cancel) |
| Drill into a tree (group → item) and view detail | `browse_commands(title, entries, *, detail_provider=...)` | `BrowseEntry` or `None` (cancel) |

Examples in the codebase:

- `aido-models` (`commands/ai/aido.py`) — `select_one` for picking a model.
- `agents-setup` / `agents-cleanup` (`commands/ai/`) — `select_many` for
  picking which AI tool integrations to act on, with `disabled=` greying
  out tools that aren't installed.
- `toolscripts-list -i` (`commands/system/list_commands.py`) —
  `browse_commands` for the domain → command → `--help` browser.

Decision rule: if your need is "show a list, get the user's pick(s) back,
then continue in normal stdout/stderr code" → it fits one of the three
helpers above.

### When to roll your own curses

Write a custom `curses.wrapper(...)` loop **only** when the command needs
behavior the helpers don't model:

- live-updating rows from a background worker (e.g. `npm-tools` fetching
  latest versions for each globally-installed package);
- running external commands without leaving the picker (e.g. `npm-tools`
  invoking `npm install`/`uninstall` and returning to the menu);
- non-list layouts (multi-pane, tabular columns, persistent status bars).

If you write one, document it as such in the module docstring. Do **not**
copy it as a template for plain "pick one of N" / "pick any of N" needs —
go back to `select_one` / `select_many`.

The legacy names `single_select` and `multi_select` still work as aliases
for `select_one` / `select_many`. New code should use the new names.

---

## 7. Dependencies

- Core install must have **zero third-party runtime deps**. The base package
  only uses the standard library.
- Anything else goes behind an extra in `pyproject.toml`:
  - `clipboard` → `pyperclip`
  - `media`     → `pillow`, `matplotlib`
  - `office`    → `openpyxl`
  - `text`      → `markdownify`, `translate`, `binaryornot`
  - `windows`   → `windows-curses` (Windows only)
- When importing an optional dep, do it lazily inside the function and
  surface a friendly error if the user hasn't installed the extra:

```python
def main() -> None:
    try:
        import pyperclip  # noqa: F401
    except ImportError:
        log.error("clipboard support not installed; run: pipx inject toolscripts pyperclip")
        sys.exit(1)
```

(Or just call `core.clipboard.copy_to_clipboard()` which already falls back
to native tools — that's preferred.)

---

## 8. Style

- Python 3.10+, type hints encouraged, `from __future__ import annotations`
  at the top of new files.
- `ruff check` and `ruff format` must pass: `ruff check src/ && ruff format src/`.
- Avoid comments that just restate the code. Comments should explain
  non-obvious *why*, not the *what*.
- Modules: shebang **only** on stand-alone scripts (e.g. things in `scripts/`).
  Files in `src/toolscripts/` are imported, not executed directly, so no
  shebang.

---

## 9. Bash scripts

Living in `scripts/` only. Two acceptable reasons to keep something in bash:

1. It's a system-level orchestrator that calls native tools whose Python
   wrappers add no value (e.g. `update_vim8_centos`).
2. It's run by an external system that expects a `.sh` (shouldn't really
   happen here).

Otherwise, port it to a Python command.

If you do write bash:

```bash
#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'
```

Mark it executable (`chmod +x`).

---

## 10. Modifying existing code

- **Preserve user-facing CLI behavior** unless the change is the explicit
  ask. Existing command names, flags, and output formats are part of the
  contract — users have shell history and scripts that depend on them.
- Refactors should be focused. Don't sweep unrelated files into a "fix one
  thing" change.
- When migrating an old top-level domain script (under `android/`, `git/`,
  ...) to `src/toolscripts/commands/<domain>/`, replace the original file
  with the package version in the same change set so the repo never has two
  copies of the same command.

---

## 11. Helping the user

- When the user asks for a new tool, ask one or two clarifying questions if
  the domain isn't obvious, then implement it following the conventions
  above and tell them which command name they will run.
- If a tool requires an external binary (`adb`, `ffmpeg`, ...), state that
  in the module docstring and use `core.shell.require(...)` to fail fast
  with a clear message.

---

## 12. Bundled skills for command lifecycle

This repo ships three project-scoped skills under `.agents/skills/` that
encode the workflows above. Use them whenever you can — they handle the
fiddly bits (entry-point alignment, both-READMEs sync, overlap checks,
deprecation aliases) so you don't have to reinvent the procedure.

| Skill | Purpose | Triggers on |
|---|---|---|
| `toolscripts-command-add`    | Add a brand-new command. **Includes a mandatory overlap check** against existing commands and proposes refactoring the closest match instead of creating a duplicate. | "add a command", "新增命令", "create a tool", "I want a command that..." |
| `toolscripts-command-modify` | Fix, debug, or change behavior of an existing command. Preserves the public CLI contract by default; renames, default changes, and output-format changes require explicit confirmation. | "fix the command", "调整一下命令", "X command is broken", "rename this command" |
| `toolscripts-command-remove` | Cleanly delete a command (entry point + module + README rows + any bundled data) and optionally leave a deprecation alias for a release. | "remove this command", "删除命令", "下线命令" |

All three reference a shared cheat sheet at
`.agents/skills/_shared/CONVENTIONS.md`, which is a tight, copy-friendly
distillation of this very file. If you change the conventions in this
document, **update that cheat sheet too** so the skills don't fall out of
sync. The skills are also responsible for keeping `pyproject.toml`,
`README.md`, and `README.zh-CN.md` consistent — never edit only one of
those three when touching the public command surface.

### Tool-specific skill discovery

Different AI tools look for skills at different paths. To avoid maintaining
three copies, this repo keeps the canonical content under `.agents/skills/`
and creates symlinks for each tool:

```
.agents/skills/                          # canonical location (the real files)
.cursor/skills  → ../.agents/skills      # symlink for Cursor
.claude/skills  → ../.agents/skills      # symlink for Claude Code
CLAUDE.md       → AGENTS.md              # symlink so Claude Code finds this file
```

When adding a skill, write it under `.agents/skills/<skill-name>/`. Both
Cursor and Claude Code will pick it up automatically through their
respective symlinks. Don't add new top-level tool-specific skills folders
— extend the symlink set instead.
