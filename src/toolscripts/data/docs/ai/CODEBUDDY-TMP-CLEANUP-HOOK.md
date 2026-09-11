# CodeBuddy tmp-cleanup hook (`allow-tmp-removal.py`)

Why this machine carries a dedicated CodeBuddy PreToolUse hook, what it
auto-approves, and what it deliberately keeps prompting for. Works together
with the `codebuddy-setup` command (shipped in the toolscripts repo).

## Background / why it exists

CodeBuddy Code hard-codes `rm` as a HIGH risk command: in any interactive
session a command that contains `rm -rf` pops *"Do you want to proceed (High
risk operation detected - requires confirmation every time)?"* and needs a
manual "Yes" each time. This cannot be avoided via `permissions.allow` rules,
for two reasons (confirmed by observing the CLI and reading `codebuddy.js`):

1. **Allow-rule matching for compound commands requires ONE rule to match every
   subcommand.** `checkAllowRules` goes through `isCommandAllowed(rule, cmd)`,
   which splits `cd x && rm -rf /tmp/y && python3 z` into parts and requires
   each part to match the **same** rule. That is why the existing
   `Bash(rm -rf /tmp/*)` and `Bash(cd:*)` can never match a compound command.
2. **Dangerous commands still require approval in `bypassPermissions` mode**
   (special branch in `checkCommandSafety` / `isDangerousCommand`).

The only reliable escape hatch is a PreToolUse hook that emits
`permissionDecision: "allow"`: in `needsApproval`,
`executeAndCachePreToolUseHooks` short-circuits before the permission prompt
when the hook says `allow` - so no dialog is shown and the
`permission_prompt` notification sound never fires.

## What it auto-approves

The hook emits `allow` only when the command contains **at least one deletion
under a temp dir** (`/tmp`, `/var/tmp`, or `$TMPDIR`) **and every other
segment** fits one of:

- `rm` / `rmdir` whose operands all live under a temp dir - this is the trigger
- read-only commands: `cd echo printf ls cat head tail wc pwd which stat du df
  date uname basename dirname realpath file sort uniq cut tr column grep true
  false`, plus read-only `git status/log/diff/show/branch/...`
- pure variable assignments: `DATA="/path"`, `export X=...` (assignments
  containing command substitution `$(` are NOT treated as safe)
- benign prefix wrappers: `time`, `command`, `builtin`, `exec`
- heredoc blocks (`python3 - <<'PY' ... PY`) - the body is folded literally so
  `;`, `|`, `&&` inside it no longer confuse command splitting
- `ACCOMPANYING_EXECS`: `python3` / `python` (only allowed when paired with a
  temp-dir cleanup in the same command)

So these no longer prompt:

```
cd .../broiler-data-analysis && rm -rf /tmp/norm_flock6 && DATA="..."
cd ... && rm -rf /tmp/findings_base && python3 scripts/analyze.py ... 2>&1 | head -20 && echo ... && cat ...
rm -rf /tmp/x && time python3 .../normalize.py ... -o /tmp/x 2>&1 | tail -25
cd ...\nSKILL=...\nrm -rf /tmp/fix_batch\npython3 $SKILL/scripts/normalize.py ...\npython3 $SKILL/scripts/analyze.py ...
```

## What it deliberately keeps prompting for (safety boundary)

These still require manual confirmation, and that is correct:

- rewriting repo/disk source files (e.g. `python3 - <<'PY'` running
  `open(p,'w').write(...)`)
- deleting directory trees on disk, e.g. `find . -name __pycache__ -type d
  -exec rm -rf {} +`
- deletions outside temp dirs: `rm -rf ~/xxx`, `rm -rf /Users/jiemeng/xxx`
- download-and-run pipelines: `curl ... | sh`, `wget ... | bash`
- bare `python3` execution with no temp cleanup
- interpreters not in the allow-list: `node`, `ruby`, `perl`, `php`, ...

In one line: **only "temp-dir cleanup + read-only companions" is silently
approved; anything genuinely risky (writing files, deleting from disk,
downloading & executing) stays confirm-gated.**

## Install / reinstall / uninstall

Installed on this machine. To rebuild elsewhere or verify the current state:

```
codebuddy-setup --status  # settings entry present? hook file matches the bundled template?
codebuddy-setup           # idempotent install (writes hook file + merges settings.json)
codebuddy-setup --force   # rewrite the on-disk hook from the bundled template
codebuddy-setup --remove  # remove the entry from settings.json (keeps the hook file)
```

Note: `codebuddy-setup` is a console script - run `./manage.py install` (or
the toolscripts install flow) so the `~/.local/bin` entry is generated. Source
edits under `src/` are picked up live by the editable install, but the console
entry point itself needs a reinstall to appear.

## Related files

- command: `toolscripts/src/toolscripts/commands/system/codebuddy_setup.py`
- bundled template: `toolscripts/src/toolscripts/data/codebuddy/allow-tmp-removal.py`
- installed location: `~/.codebuddy/hooks/allow-tmp-removal.py`
- configuration: `~/.codebuddy/settings.json` -> `hooks.PreToolUse` (matcher `Bash`)

## Troubleshooting

- Still prompted? Inspect the session log
  `~/.codebuddy/logs/<date>/<project>__<hash>.log`, search for
  `HookExecutor ... allow-tmp-removal.py` (did the hook run?) and
  `[tool-permission] ASK` (which command, with the full text - note the logged
  command is truncated at 200 chars).
- Hook output ignored? Check the hook process exited cleanly (no
  `abnormal exit` record) and stdout is a single-line JSON
  `{"hookSpecificOutput":{... "permissionDecision":"allow"}}`.
- To observe the raw payload the hook receives, temporarily re-add a `_dbg`
  log block to the bundled template in `codebuddy_setup.py` and re-run
  `codebuddy-setup --force`.