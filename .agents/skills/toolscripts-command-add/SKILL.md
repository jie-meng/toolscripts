---
name: toolscripts-command-add
description: Add a new CLI command to the toolscripts monorepo following its conventions — picks the right domain folder, writes a `def main()` module under `src/toolscripts/commands/<domain>/`, wires the entry point into `[project.scripts]` in `pyproject.toml`, and updates the command tables in `README.md` and `README.zh-CN.md`. ALWAYS performs an "is this already covered?" check first against existing commands and proposes refactoring the closest match instead of creating a duplicate when the overlap is high. Use whenever the user asks to add a new tool/script/command, "create a script", "新增脚本", "加一个命令", "add a tool", or describes functionality they want exposed as a `toolscripts` CLI.
---

# toolscripts-command-add

Add a new CLI command to the **toolscripts** monorepo. The user's expectation
is that you do this end-to-end: code + entry point + docs, all consistent
with existing conventions.

If you have not yet, read the shared conventions cheat sheet:
[../\_shared/CONVENTIONS.md](../_shared/CONVENTIONS.md)

---

## Workflow

Copy this checklist and tick items as you go:

```
- [ ] Step 1: Clarify the requirement (one sentence)
- [ ] Step 2: Check for overlap with existing commands → propose reuse / refactor if any
- [ ] Step 3: Pick the domain folder and command name
- [ ] Step 4: Write the module under src/toolscripts/commands/<domain>/<snake>.py
- [ ] Step 5: Register the entry point in pyproject.toml
- [ ] Step 6: Update README.md and README.zh-CN.md tables
- [ ] Step 7: Tell the user the command name + ./manage.py install --force
```

### Step 1 — Clarify

Restate the requested behavior in one sentence and the proposed kebab-case
command name (e.g. `mp4-rotate` → "rotate an MP4 video by N degrees").

If the domain or input/output format is genuinely ambiguous, ask **one or
two** clarifying questions max — don't interrogate the user.

### Step 2 — Overlap check (mandatory, do not skip)

Before writing anything, list candidate commands that already do something
similar. Concretely:

1. Read `[project.scripts]` in `pyproject.toml` and skim names by domain.
2. Search command source for related keywords:
   - keyword in command name (e.g. user wants "json prettifier" → grep
     `commands/codec/` for `json`)
   - keyword in module docstring (the first line of every command file is
     a one-line summary)
3. Score the closest 1–3 candidates as **none / partial / strong** overlap.

Then act on the score:

| Overlap | What to do |
|---|---|
| **none** | Proceed to Step 3. |
| **partial** (a flag or sub-mode would cover the new ask) | Stop and tell the user: "`<existing-cmd>` already does X; we could either (a) add a `--new-flag` to `<existing-cmd>` or (b) create a separate `<new-cmd>`. Which do you prefer?" Wait for the answer. |
| **strong** (the existing command basically already does this) | Stop and tell the user the existing command's name and the exact invocation that solves their problem. Only proceed to create a new one if they explicitly say so. |

Be honest — if there's a real overlap, surface it. Forcing the user to
discover a duplicate later is worse than asking once.

### Step 3 — Pick domain and name

- **Domain**: choose an existing folder under `src/toolscripts/commands/`
  (`time/`, `git/`, `media/`, `system/`, ...). Only add a brand-new domain
  folder if none of the 17 existing ones is a reasonable home.
- **Command name (user-facing)**: `kebab-case`, prefixed by domain when the
  domain isn't obvious from the verb (e.g. `git-copy-diff`, `android-record`,
  but `myip` and `slugify` are fine without a prefix because they are
  unambiguous).
- **Module name**: `snake_case.py` mirroring the command name without the
  domain prefix (e.g. `copy_diff.py` for `git-copy-diff`).

### Step 4 — Write the module

Path: `src/toolscripts/commands/<domain>/<snake_name>.py`

Use this skeleton verbatim and fill in the body. **No shebang, no top-level
side effects.**

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

Apply the rules from `_shared/CONVENTIONS.md`:

- Use `core.shell.run` / `core.shell.capture` instead of bare `subprocess`.
- Use `core.shell.require("foo")` early when the command needs an external
  binary; mention the binary in the module docstring.
- Platform-specific commands: call `require_platform("macos")` (or `"linux"`,
  `"windows"`) at the top of `main()`.
- Optional third-party deps go behind an extra and are imported **lazily**
  inside `main()` with a friendly error if missing. New dependencies are a
  big deal — only add if there's no stdlib path. Update the right
  `[project.optional-dependencies]` group and both READMEs' extras tables.
- Bundled non-code resources go under `src/toolscripts/data/<domain>/...` and
  are read with `importlib.resources.files(...)`.
- Print human output to **stdout**; logs go through `log.*` (stderr).
- Don't import from another command — lift shared code into `core/`.

### Step 5 — Register the entry point

Add a single line to `[project.scripts]` in `pyproject.toml`, in the **same
domain section** as similar commands (the file is grouped by `# domain`
comments — keep that grouping):

```toml
my-cmd = "toolscripts.commands.<domain>.<snake_name>:main"
```

Keep the columns aligned with the surrounding entries (the existing file
pads command names to a consistent width; match it).

### Step 6 — Update both READMEs

Both `README.md` and `README.zh-CN.md` have a command table grouped by
domain. Add the new command name to the matching domain row in **both**
files. If you added a new domain, add a new row in the same place in both
tables and pick the same domain label translation.

If you added a new optional dependency or extra, also update the extras
table ("Optional dependency groups" / "可选依赖分组") in both READMEs.

### Step 7 — Hand off to the user

Tell the user, in this order:

1. The new command name (kebab-case).
2. A one-line example of how to run it with sensible args.
3. The reinstall command, because `[project.scripts]` changed:

   ```bash
   ./manage.py install --force
   ```

4. Mention any new external binary requirement (`brew install ffmpeg` etc.)
   or new optional extra (`pipx inject toolscripts pyperclip`).

---

## Example: end-to-end

User: "I want a command that prints my external IPv6 address."

1. **Clarify** — "Prints the user's public IPv6 address. Proposed name:
   `myip6`."
2. **Overlap check** — `pyproject.toml` already has `myip` under
   `# system / files`. Reading `commands/system/myip.py` shows it prints
   IPv4 only. **Partial overlap.** Tell the user:

   > `myip` already prints the public IPv4 address. Two options:
   > (a) extend `myip` with a `--v6` flag,
   > (b) add a separate `myip6` command.
   > Which would you prefer?

3. User picks (a) → switch to the `toolscripts-command-modify` skill.
   User picks (b) → continue here:
   - Create `src/toolscripts/commands/system/myip6.py` with a `def main()`
     that hits `https://api64.ipify.org` (stdlib `urllib.request`, no new
     dep) and prints the result to stdout.
   - Add to `[project.scripts]` under `# system / files`:
     `myip6                     = "toolscripts.commands.system.myip6:main"`
   - Add `myip6` to the `system` row of both README tables.
   - Tell the user: run `./manage.py install --force`, then `myip6`.

---

## Don'ts

- Don't add a new entry to `[project.scripts]` without a corresponding row
  update in both READMEs.
- Don't put the script anywhere outside `src/toolscripts/commands/<domain>/`
  (no top-level files, no `shell/`, no `bin/`).
- Don't introduce a new third-party dependency without (a) checking it's
  really needed, (b) putting it behind the right extra, (c) lazy-importing
  it, (d) updating the extras table in both READMEs.
- Don't import from another `commands/...` module. Lift shared code into
  `core/` first.
- Don't write a bash script unless the task genuinely needs system-level
  shelling out (system package install, etc.). Bash scripts go in
  `scripts/`, get `chmod +x`, and are **not** added to `[project.scripts]`.
