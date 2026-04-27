---
name: toolscripts-command-remove
description: Delete an existing command from the toolscripts monorepo cleanly — removes the entry point from `[project.scripts]` in `pyproject.toml`, deletes the module file under `src/toolscripts/commands/<domain>/`, drops the command from the `README.md` and `README.zh-CN.md` tables, and surfaces any shared `core/`/`adb/`/`git_utils/` helpers that may now be orphaned. Confirms with the user that this is a real removal (not a rename — for renames use `toolscripts-command-modify`). Use when the user asks to delete/remove/drop a command, "remove this script", "this command is dead/obsolete", "下线脚本", "删除命令", "去掉这个工具", or wants to retire a tool from the monorepo.
---

# toolscripts-command-remove

Delete a command from the **toolscripts** monorepo cleanly. Removing a
command is a public-contract break (someone's shell history or alias may
depend on it), so we err on the side of confirming and leaving a clean
repo behind.

If you have not yet, read the shared conventions cheat sheet:
[../\_shared/CONVENTIONS.md](../_shared/CONVENTIONS.md)

---

## When *not* to use this skill

- **Rename** → use `toolscripts-command-modify`. A rename is one operation,
  not delete-then-add.
- **Bug fix or refactor** → use `toolscripts-command-modify`.
- **Move to a different domain folder** → use `toolscripts-command-modify`
  (it's just an entry-point right-hand-side change plus a file move).

---

## Workflow

```
- [ ] Step 1: Confirm this is a removal (not a rename) and confirm with the user
- [ ] Step 2: Locate every touch point of the command
- [ ] Step 3: Check for cross-command dependencies / shared helpers
- [ ] Step 4: Delete in this order: README rows → pyproject.toml entry → module file
- [ ] Step 5: Garbage-collect now-unused shared helpers (only when truly orphaned)
- [ ] Step 6: Tell the user what was removed and that ./manage.py install --force is needed
```

### Step 1 — Confirm intent

Before deleting anything, restate to the user:

> "About to **delete** the command `<my-cmd>`. Anyone with shell history
> or aliases pointing at it will see 'command not found' after they next
> reinstall. If you actually want to rename or move it instead, say so
> now. Otherwise reply 'yes, remove'."

If the user is removing because the command is replaced by another, also
mention: "Should I leave a deprecation alias (a thin entry that prints a
warning and forwards to `<replacement-cmd>`) for one release?" — that's
the friendliest migration path. Skip this question if the user already
specified.

Wait for confirmation before any file changes. Don't delete on a hunch.

### Step 2 — Locate every touch point

Find every place `<my-cmd>` appears:

1. **Entry point** in `pyproject.toml` under `[project.scripts]`. Note
   both the kebab name (left of `=`) and the module path (right of `=`).
2. **Module file**: `src/toolscripts/commands/<domain>/<snake_name>.py`.
3. **README rows**: `## Available commands` table in `README.md` and
   `## 命令一览` table in `README.zh-CN.md`.
4. **Cross-references** elsewhere:
   - search the repo for the kebab name (might be mentioned in another
     command's docstring, README prose, or a test).
   - search for the module's import path (`toolscripts.commands.<domain>.<snake>`)
     — should usually be zero hits since commands don't import each other.

Make a short bullet list of all the hits before editing anything.

### Step 3 — Check for orphaned helpers

If the command was the only consumer of a helper in
`src/toolscripts/core/`, `src/toolscripts/adb/`, `src/toolscripts/git_utils/`,
or `src/toolscripts/data/<domain>/`, that helper might now be dead code.

For each helper the deleted command used:

1. Search the rest of `src/toolscripts/` for other importers.
2. If there are no other importers and the helper isn't part of a
   documented public surface (`core.shell.run`, `core.log.get_logger`,
   etc. are public — leave them alone), call it out. Default to
   **leaving it in place** and flagging it to the user; only remove if
   they confirm.

`core/` helpers in particular are usually fine to keep — they're cheap
and other commands may grow to use them. Don't aggressively prune.

### Step 4 — Delete in the right order

The order matters to keep the repo in a coherent state at every commit:

1. **READMEs first** — drop `<my-cmd>` from the matching domain row in
   both `README.md` and `README.zh-CN.md`. If the deleted command was the
   only one in its domain row, decide with the user whether to drop the
   row entirely or leave it for an upcoming command (usually: drop the
   row if the domain folder will also be empty after Step 4.3, otherwise
   keep it).
2. **`pyproject.toml`** — delete the `<my-cmd> = "..."` line from
   `[project.scripts]`. Preserve the `# domain` group comments and the
   column alignment of the surrounding lines.
3. **Module file** — delete `src/toolscripts/commands/<domain>/<snake_name>.py`.
4. **Domain folder cleanup** — if the domain folder is now empty (only
   `__init__.py` left), the folder can be left in place; do **not** delete
   `__init__.py` unless every other domain becomes empty too. An empty
   domain folder is harmless.

If the user opted for a deprecation alias in Step 1, **skip step 4.3**
and instead replace the module body with a minimal forwarder:

```python
"""``my-cmd`` - deprecated, forwards to ``new-cmd``."""

from __future__ import annotations

import sys

from toolscripts.commands.<domain>.new_cmd import main as _new_main
from toolscripts.core.log import get_logger

log = get_logger(__name__)


def main() -> None:
    log.warning("'my-cmd' is deprecated; use 'new-cmd' instead.")
    sys.argv[0] = "new-cmd"
    _new_main()
```

Note: this is the **only** legitimate case where one command imports from
another. Document the planned removal date in the docstring.

### Step 5 — Tests / data resources

- If there's a test under `tests/` exercising the deleted command, remove
  it.
- If the command had its own bundled data under
  `src/toolscripts/data/<domain>/<something>/`, and nothing else uses
  those files, remove that subfolder. If the data is shared, leave it.

### Step 6 — Hand off to the user

Tell the user:

1. Which command was removed.
2. The list of files you touched (concise: "deleted X, edited Y, Z").
3. Whether you left a deprecation alias and, if so, when it should be
   removed.
4. The reinstall command, because `[project.scripts]` changed:

   ```bash
   ./manage.py install --force
   ```

5. Any shared helper you suspected might be orphaned but did **not**
   delete — let the user decide on the cleanup.

---

## Example

User: "Remove `extract-games`, we're not using it any more."

1. Confirm — "About to delete `extract-games`. Reply 'yes, remove' to
   confirm. (Or say 'rename' / 'replace by X' instead.)"
   User: "yes, remove."
2. Locate:
   - entry point: `extract-games = "toolscripts.commands.games.extract_games:main"`
   - module: `src/toolscripts/commands/games/extract_games.py`
   - README rows: under "misc" in `README.md` and "杂项" in `README.zh-CN.md`.
   - cross-refs: grep finds nothing else.
3. Orphaned helpers: the module only imports from `core.log`. Nothing to
   prune.
4. Delete:
   - drop `extract-games` from the `misc` / `杂项` rows in both READMEs.
     The `games/` row in the table — wait, there is none in the table; it
     was lumped into `misc`. Just drop the name from that row's command list.
   - remove the line from `[project.scripts]`.
   - delete `src/toolscripts/commands/games/extract_games.py`. The
     `games/` folder is now empty except for `__init__.py`; leave it.
5. No tests / no bundled data for this command.
6. Hand off: "Removed `extract-games`. Touched: `pyproject.toml`,
   `README.md`, `README.zh-CN.md`, deleted
   `src/toolscripts/commands/games/extract_games.py`. The `commands/games/`
   folder is now empty except `__init__.py` — left in place in case you
   add another games command. Run `./manage.py install --force` to drop
   the binary from `~/.local/bin`."

---

## Don'ts

- Don't delete without explicit confirmation. Removal is a contract break.
- Don't delete a command and then realize it was actually a rename — ask
  in Step 1.
- Don't aggressively prune `core/` helpers. They're shared infrastructure
  and cheap to keep around.
- Don't forget to update **both** READMEs. Leaving stale rows is the
  most common failure mode of this skill.
- Don't delete the `__init__.py` of a domain folder when the last command
  leaves. The folder is harmless and may be reused.
- Don't leave a deprecation alias forever — if you create one in Step 4,
  put a clear "remove after `<date or version>`" note in its docstring.
