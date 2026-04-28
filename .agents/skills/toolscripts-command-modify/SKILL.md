---
name: toolscripts-command-modify
description: Fix, debug, or change behavior of an existing command in the toolscripts monorepo while preserving its public CLI contract. Locates the right module under `src/toolscripts/commands/<domain>/`, applies the smallest correct change, keeps `[project.scripts]` and the README tables in sync (e.g. when a command is renamed or gains a new flag worth documenting), and tells the user whether a `./manage.py install --force` is needed. Also the right skill when the user reports "X command is broken / behaving wrong / missing a flag", "fix the script", "调整一下命令", "修改脚本", "脚本有 bug", or asks to refactor an existing command.
---

# toolscripts-command-modify

Modify an existing command in the **toolscripts** monorepo. The default
mode is *preserve user-facing behavior unless the change is the explicit
ask* — command names, flags, defaults, and output format are part of the
contract.

If you have not yet, read the shared conventions cheat sheet:
[../\_shared/CONVENTIONS.md](../_shared/CONVENTIONS.md)

---

## When to use this skill (vs. -add / -remove)

| Situation | Use |
|---|---|
| User wants new behavior on an existing command (new flag, fix bug, change algorithm) | **this skill** |
| User wants completely new functionality that no existing command covers | `toolscripts-command-add` |
| User wants to drop a command entirely | `toolscripts-command-remove` |
| User wants to **rename** a command | this skill (rename is a modification of the entry point + module + READMEs; do not delete then re-add) |

---

## Workflow

```
- [ ] Step 1: Locate the command (module, entry point, READMEs)
- [ ] Step 2: Reproduce / understand the current behavior
- [ ] Step 3: Decide if this is a "preserve contract" or "intentional break" change
- [ ] Step 4: Apply the smallest correct change
              (reuse-first reflex: lift duplication into core/ or domain packages
              instead of copy-pasting; never import from another command)
- [ ] Step 5: Sync pyproject.toml + READMEs (only if the public surface changed)
- [ ] Step 6: Tell the user whether ./manage.py install --force is needed
```

### Step 1 — Locate

Resolve the command name (`my-cmd`) to all three of its touch points:

1. **Entry point** in `pyproject.toml` under `[project.scripts]`. Grep for
   the kebab-case name. The right side of `=` tells you the module path:

   ```
   my-cmd = "toolscripts.commands.<domain>.<snake_name>:main"
   ```

2. **Module file**: `src/toolscripts/commands/<domain>/<snake_name>.py`.
3. **README rows**: `## Available commands` table in `README.md` and
   `## 命令一览` table in `README.zh-CN.md`. The command will show up in
   the row for its domain.

If the user gave you a kebab name and the entry point is missing — flag it,
that's a packaging bug worth fixing too.

### Step 2 — Understand the current behavior

Read the **whole** module before editing. In particular:

- The module docstring (the one-line summary on line 1).
- The `argparse` setup — every flag, default, and help string is part of
  the user-facing contract.
- What's printed to **stdout** (data) vs **stderr** (logs via `log.*`).
  Don't shuffle these.
- What external binaries / optional deps it depends on.

If the user reported a bug, also try to reconstruct the failing scenario
(input, expected, observed) before you start editing.

### Step 3 — Classify the change

Bucket the change into one of:

- **A. Internal-only fix** (bug fix, refactor, performance) — no flag/output
  change, no entry-point change. → No README or `pyproject.toml` edits
  needed, no reinstall needed.
- **B. Add a new optional flag with a backwards-compatible default** —
  module-only change. README rows usually don't need to change because they
  list command names, not flags. (Exception: if the README has prose about
  the command's options, update it.) No reinstall needed.
- **C. Change a default, remove a flag, change output format, or rename
  the command** — this is an **intentional break** of the contract.
  - Confirm with the user first if they didn't explicitly ask for a break.
  - If renaming, edit `pyproject.toml`, the module's `prog=` argument, the
    module docstring, and the README tables in both READMEs. Reinstall is
    required.
  - If changing output, mention it in the commit-style explanation you
    return to the user so they know to retest piping.

### Step 4 — Apply the change (reuse-first reflex applies here too)

Before writing **any new code** inside the module, do the same reuse-first
reflex from `_shared/CONVENTIONS.md` §4:

1. **Is what I'm about to write already in `core/` / `adb/` / `git_utils/`?**
   Match the new behavior to the helpers table at
   `_shared/CONVENTIONS.md` §5. If yes, use the helper.
2. **Is this fix or new behavior also needed by another command in the
   same domain?** Grep `commands/<domain>/`. If yes, decide:

   | Situation | What to do |
   |---|---|
   | A `core/` / `adb/` / `git_utils/` helper exists and fits | Use it. Done. |
   | The would-be shared logic still lives inside another command file | **Stop and lift it** into `core/` (or the right domain package) in this same change. Update the other command to route through it too. Don't `import` from another command. |
   | Helper exists but needs one more knob | Extend the helper with a kwarg (backwards-compatible default). Don't fork. |

Concrete reuse traps to catch (same list as the -add skill, repeated here
because the *modify* path is where they get re-introduced most often):

- "Pick from a list" UI → `core.ui_curses.select_one` / `select_many` /
  `browse_commands`. Do not introduce a fresh `curses.wrapper(...)` loop
  unless the command genuinely needs an application-level TUI (live
  worker updates, in-UI external command execution, multi-pane). The only
  current exception is `commands/ai/npm_tools.py`.
- Calling `adb` / `git` → `toolscripts.adb` / `toolscripts.git_utils`,
  not raw `subprocess`.
- Yes/no or numbered prompts → `core.prompts.yes_no` / `choice` / `ask`.
- ANSI color → `core.colors`.
- Clipboard → `core.clipboard.copy_to_clipboard`.
- OS branching → `core.platform.is_macos` / `is_linux` / `is_windows` /
  `require_platform`.

Then make the change:

- Keep using `argparse`, `log = get_logger(__name__)`, `add_logging_flags`,
  `configure_from_args`, `core.shell.run/capture/require`.
- Keep the change focused. If you spot unrelated style nits, leave them
  unless the user asked for cleanup — don't sweep them in. (The reuse
  lift in the table above is **not** "unrelated" — it's required to make
  the fix correctly without growing duplication.)
- If the command uses an optional third-party dep, keep the lazy-import
  pattern with a friendly error message intact.
- Run/eyeball `ruff check src/<path> && ruff format src/<path>` before
  finishing if non-trivial.

### Step 5 — Sync the public surface

Update the documentation **only when the public surface actually changed**:

| Change | `pyproject.toml`? | `README.md` & `README.zh-CN.md` rows? |
|---|---|---|
| Internal fix / refactor | No | No |
| New optional flag with default | No | No (unless README mentions flags explicitly) |
| Renamed command | **Yes** (entry-point left side) | **Yes** (replace old name with new in domain row, in both files) |
| Removed flag / changed output | No | Update if README explicitly mentions the removed thing |
| Moved to a different domain folder | **Yes** (entry-point right side) | **Yes** if the domain row changes |

When updating both READMEs, keep the row order consistent between them and
preserve the same domain labels each side already uses.

### Step 6 — Hand off to the user

Tell the user:

1. **What was wrong / what changed** in one or two lines.
2. **What you changed** — list the touched files briefly.
3. **Whether they need to reinstall**:
   - If `[project.scripts]` was edited (rename, move, new entry point):
     ```bash
     ./manage.py install --force
     ```
   - If only the module body changed: editable install picks it up
     automatically — no reinstall needed.
4. **Anything new they need on the system** — e.g. if you added a call to
   a new external binary, mention `brew install foo` / `apt install foo`.

---

## Example: bug fix without contract change

User: "`timestamp-now` is showing the wrong year."

1. Locate: `pyproject.toml` → `timestamp-now =
   "toolscripts.commands.time.now:main"` →
   `src/toolscripts/commands/time/now.py`.
2. Read the module — `datetime.now().strftime("%Y-...")` is fine, but the
   logger is printing `"now=..."` with a stale formatter that drops the
   year. Bug confirmed.
3. Classify: **A — internal-only fix**.
4. Apply: fix the format string. No flag/output change visible to the
   user (the printed output to stdout was already correct, only the
   `log.debug` line was wrong).
5. Sync: nothing to update in `pyproject.toml` or READMEs.
6. Hand off: "Fixed the log formatter in `commands/time/now.py`. No
   reinstall needed — editable install picks it up. Try `timestamp-now -v`
   to see the corrected debug line."

## Example: rename a command

User: "Rename `mp4cut` to `mp4-cut` for consistency with the other media
commands."

1. Locate: `pyproject.toml` →
   `mp4cut = "toolscripts.commands.media.mp4cut:main"` and module
   `src/toolscripts/commands/media/mp4cut.py`. README tables list `mp4cut`
   under the `media` row.
2. Read the module to confirm `prog="mp4cut"` and that the docstring
   uses ``\`\`mp4cut\`\``.
3. Classify: **C — intentional break**. Old shell history with `mp4cut`
   will stop working. Tell the user that and confirm. Optionally, ship
   both names for a deprecation period (add **two** entry points pointing
   at the same `:main` and have the module detect `argv[0]` to print a
   deprecation warning when invoked as `mp4cut`).
4. Apply (assuming hard rename):
   - `pyproject.toml`: change the entry-point key from `mp4cut` to
     `mp4-cut`. Optionally rename the module file to `mp4_cut.py` for
     style consistency and update the right-hand side of the entry point.
   - In the module: update `prog="mp4-cut"` and the docstring opening.
   - In both READMEs: change `mp4cut` → `mp4-cut` in the `media` row.
5. Sync: done above.
6. Hand off: "Renamed `mp4cut` → `mp4-cut`. Reinstall with
   `./manage.py install --force`, then use `mp4-cut`. Old shell aliases /
   muscle memory pointing at `mp4cut` will need updating."

---

## Don'ts

- Don't change a command's public name, flags, defaults, or output without
  the user's explicit ask. That's a contract break and breaks shell
  history and downstream scripts.
- Don't fix a bug by introducing a new third-party dependency when the
  stdlib (or an existing `core/` helper) would do.
- Don't refactor unrelated files into a focused fix. One change, one
  scope.
- Don't bypass `core/` helpers. If you're writing a fresh `subprocess.run`
  call or a fresh ANSI color escape, you're probably reinventing what's
  already in `core/shell` or `core/colors`.
- Don't forget the docstring. The first line is the one-liner shown when
  someone greps for what a command does — keep it accurate.
