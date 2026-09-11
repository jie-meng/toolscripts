#!/usr/bin/env python3
"""PreToolUse hook: auto-allow Bash commands whose only destructive part is a
temp-dir cleanup.

Emits an "allow" decision only when every subcommand is either an rm/rmdir
whose operands all live under a temp dir, a read-only inspection command, a
bare shell variable assignment (VAR=value, which executes nothing), or an
opt-in "accompanying exec" (see ACCOMPANYING_EXECS) that is paired with a
temp-dir cleanup. Anything else prints nothing, so the normal permission flow
applies.

This exists because `rm -rf` is hard-coded as a HIGH risk command that always
prompts in interactive sessions, and allow rules cannot cover it reliably:
compound commands require every subcommand to match an allow rule.
"""

import json
import os
import re
import sys

# A shell variable assignment (VAR=value). A bare assignment executes nothing,
# so it is safe to treat as read-only. Assignments with command substitution
# ($(...) or backticks) execute code and are deliberately NOT matched.
ASSIGNMENT_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")

# Kebab-safe shell prefix wrappers: `time cmd`, `command cmd`, `builtin cmd`,
# `exec cmd` all just run `cmd`, so the wrapper can be stripped before
# classifying. (`exec` replaces the shell, same effective command.)
PREFIX_WRAPPERS = {"time", "command", "builtin", "exec"}

# Hooks that are legitimately used to feed a heredoc to an interpreter. The
# heredoc BODY is arbitrary text (script code); we only ever fold bodies when
# they follow one of these host commands, so an attacker cannot hide a
# destructive segment inside an unrelated heredoc.
HEREDOC_HOSTS = {"python3", "python", "cat", "sh", "bash", "zsh", "sed", "awk"}

_HEREDOC_OPEN = re.compile(r"<<-?\s*(?:'([^']*)'|\"([^\"]*)\"|([A-Za-z_][A-Za-z0-9_]*))")


def strip_heredoc_bodies(command):
    """Collapse `cmd <<DELIM\n...\nDELIM` blocks to a single `<<DELIM` token.

    Without this, separators (`;`, `|`, `&&`) inside the heredoc body would
    be mistaken for command separators and shatter the compound command into
    unclassifiable fragments. Only folds heredocs whose host command is in
    HEREDOC_HOSTS; everything else is left untouched (and thus strict).
    """
    out, i, n = [], 0, len(command)
    while True:
        m = _HEREDOC_OPEN.search(command, i)
        if not m:
            out.append(command[i:])
            break
        # Host command = the typed command word that starts this shell segment
        # (e.g. the `python3` in `python3 - <<'PY'`), skipping assignments and
        # benign wrapper keywords.
        prefix = command[i : m.start()]
        seg = re.split(r";|&&|\|\||\||\n", prefix)[-1]
        words = seg.split()
        k = 0
        while k < len(words) and (
            ASSIGNMENT_TOKEN.match(words[k]) or words[k] in PREFIX_WRAPPERS
        ):
            k += 1
        host = words[k].split("/")[-1] if k < len(words) else ""
        delim = m.group(1) or m.group(2) or m.group(3)
        body_start = command.find("\n", m.end())
        if host not in HEREDOC_HOSTS or body_start == -1:
            out.append(command[i : m.end()])
            i = m.end()
            continue
        # Locate the terminator line: a line equal to DELIM (leading tabs ok).
        j, terminator_end = body_start + 1, -1
        while True:
            nxt = command.find("\n", j)
            line_end = nxt if nxt != -1 else len(command)
            if command[j:line_end].strip("\t") == delim:
                terminator_end = line_end
                break
            if nxt == -1:
                break
            j = nxt + 1
        if terminator_end == -1:  # unterminated: leave everything as-is (strict)
            out.append(command[i:])
            break
        out.append(command[i : m.start()])  # everything up to the << operator
        out.append("<<" + delim + "\n")     # placeholder token + separator
        i = terminator_end + 1              # resume after the terminator line
    return "".join(out)

READ_ONLY = {
    "cd", "echo", "printf", "ls", "cat", "head", "tail", "wc", "pwd", "which",
    "stat", "du", "df", "date", "uname", "basename", "dirname", "realpath",
    "file", "sort", "uniq", "cut", "tr", "column", "grep", "true", "false",
}

# Programs that actually execute code. They are NOT allowed on their own, and
# only pass the hook when the command ALSO contains a temp-dir cleanup and every
# other segment is read-only. This exists for workflows like:
#     rm -rf /tmp/findings_base && python3 scripts/analyze.py --input /tmp/x
# where the only destructive part is the tmp deletion.
#
# TRADEOFF: once added here, `python3 -c "import shutil; ..."` also passes when
# paired with any /tmp deletion. Only keep entries you fully trust. Empty the
# set to refuse these (strict default).
ACCOMPANYING_EXECS = {"python3", "python"}

GIT_READ_ONLY = {
    "status", "log", "diff", "show", "branch", "rev-parse", "describe",
    "ls-files", "tag", "blame", "worktree",
}

GIT_WORKTREE_READ_ONLY = {"list"}


def split_subcommands(command):
    parts, current, quote, i = [], "", None, 0
    while i < len(command):
        ch = command[i]
        if quote:
            current += ch
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            current += ch
        elif command.startswith(("&&", "||"), i):
            parts.append(current)
            current = ""
            i += 2
            continue
        elif ch in "|;\n":
            # `\n` is a command separator in the shell, equivalent to `;`
            parts.append(current)
            current = ""
        else:
            current += ch
        i += 1
    parts.append(current)
    return [p for p in (part.strip() for part in parts) if p]


def tokenize(subcommand):
    tokens, current, quote = [], "", None
    for ch in subcommand:
        if quote:
            if ch == quote:
                quote = None
            else:
                current += ch
        elif ch in "\"'":
            quote = ch
        elif ch.isspace():
            if current:
                tokens.append(current)
                current = ""
        else:
            current += ch
    if current:
        tokens.append(current)
    return tokens


def operands(tokens):
    paths, end_of_flags = [], False
    for token in tokens[1:]:
        if token == "--":
            end_of_flags = True
        elif end_of_flags or not token.startswith("-"):
            paths.append(token)
    return paths


def is_assignment(token):
    return bool(ASSIGNMENT_TOKEN.match(token)) and "$(" not in token and "`" not in token


def strip_prefixes(tokens):
    """Drop leading VAR=value assignments and benign shell wrapper keywords
    (time/command/builtin/exec) so the real command word can be classified.
    """
    i = 0
    while i < len(tokens):
        if is_assignment(tokens[i]) or tokens[i] in PREFIX_WRAPPERS:
            i += 1
        else:
            break
    return tokens[i:]


def is_pure_assignment(tokens):
    if not tokens:
        return False
    if tokens[0] in ("export", "local", "readonly"):
        tokens = tokens[1:]
    return bool(tokens) and all(is_assignment(t) for t in tokens)


def temp_dirs():
    dirs = {"/tmp", "/private/tmp", "/var/tmp"}
    tmpdir = os.environ.get("TMPDIR")
    if tmpdir:
        dirs.add(os.path.abspath(tmpdir.rstrip("/")))
    return dirs


def is_temp_path(path, cwd, temps):
    expanded = os.path.expanduser(os.path.expandvars(path))
    resolved = os.path.abspath(os.path.join(cwd, expanded))
    return any(resolved.startswith(temp + os.sep) for temp in temps)


def is_cleanup(tokens, cwd, temps):
    if tokens[0] not in ("rm", "rmdir"):
        return False
    paths = operands(tokens)
    return bool(paths) and all(is_temp_path(p, cwd, temps) for p in paths)


def is_read_only(tokens):
    name = tokens[0]
    if name in READ_ONLY:
        return True
    if name != "git":
        return False
    args = [t for t in tokens[1:] if not t.startswith("-")]
    if not args or args[0] not in GIT_READ_ONLY:
        return False
    if args[0] == "worktree":
        return len(args) > 1 and args[1] in GIT_WORKTREE_READ_ONLY
    return True


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return
    if payload.get("tool_name") != "Bash":
        return
    command = (payload.get("tool_input") or {}).get("command")
    if not isinstance(command, str) or not command.strip():
        return

    command = strip_heredoc_bodies(command)

    cwd = payload.get("cwd") or os.getcwd()
    temps = temp_dirs()
    cleanups = 0
    for subcommand in split_subcommands(command):
        tokens = tokenize(subcommand)
        if not tokens:
            continue
        if is_pure_assignment(tokens):
            continue  # VAR=value executes nothing; treat as read-only
        tokens = strip_prefixes(tokens)
        if is_cleanup(tokens, cwd, temps):
            cleanups += 1
        elif tokens[0] in ACCOMPANYING_EXECS:
            continue  # opt-in companion exec, only OK paired with tmp cleanup above
        elif not is_read_only(tokens):
            return
    if not cleanups:
        return

    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": "temp-dir cleanup with read-only companions",
            }
        },
        sys.stdout,
    )


if __name__ == "__main__":
    main()
