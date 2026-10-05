"""Registry of CLI AI agent data locations for ``agent-clean``.

Scope: command-line agents only. GUI/IDE agents (Qoder, ZCode, WorkBuddy,
DeepSeek Harness, ...) are deliberately excluded — their sessions live in
app-internal databases behind the app sidebar and are cleaned from inside the
app, not from a script.

Each tool profile describes the on-disk "parts" that can be deleted to free
space. Paths drift between tool versions, so users can override any tool's
parts (or add brand-new tools) via
``$XDG_CONFIG_HOME/toolscripts/agent-clean.json`` (default
``~/.config/toolscripts/agent-clean.json``), e.g.::

    {"tools": {"cline": {"parts": [
        {"key": "sessions", "label": "sessions",
         "paths": ["~/.cline/data/sessions"],
         "default": true, "note": "resumable task records"}
    ]}}}
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, replace
from pathlib import Path


@dataclass
class CleanPart:
    """One deletable unit (sessions, logs, cache, ...) inside a tool."""

    key: str  # stable id used by ``--del TOOL:KEY``
    label: str
    paths: tuple[str, ...]  # "~"-relative; a trailing glob component is allowed
    default: bool = True  # pre-checked in the curses picker
    note: str = ""  # what the user loses by deleting this part


@dataclass
class ToolProfile:
    """One detected CLI agent tool and its cleanable parts."""

    tool_id: str
    name: str
    parts: list[CleanPart] = field(default_factory=list)


TOOL_PROFILES: dict[str, ToolProfile] = {
    "copilot": ToolProfile(
        tool_id="copilot",
        name="GitHub Copilot CLI",
        parts=[
            CleanPart(
                key="sessions",
                label="sessions",
                paths=("~/.copilot/session-state/*", "~/.copilot/history-session-state/*"),
                note="All --resume-able session history",
            ),
            CleanPart(
                key="index",
                label="session index db",
                paths=("~/.copilot/session-store.db*",),
                note="Session index SQLite; clean it together with sessions",
            ),
            CleanPart(
                key="pkg",
                label="pkg cache",
                paths=("~/.copilot/pkg",),
                default=False,
                note="CLI package cache; re-downloaded on demand",
            ),
            CleanPart(
                key="logs",
                label="logs",
                paths=("~/.copilot/logs",),
                default=False,
                note="Run logs",
            ),
        ],
    ),
    "cline": ToolProfile(
        tool_id="cline",
        name="Cline",
        parts=[
            CleanPart(
                key="sessions",
                label="sessions",
                paths=("~/.cline/data/sessions",),
                note="Resumable task/session records",
            ),
            CleanPart(
                key="logs",
                label="logs",
                paths=("~/.cline/data/logs",),
                note="Per-session verbose logs, usually the biggest",
            ),
            CleanPart(
                key="db",
                label="state db",
                paths=("~/.cline/data/db",),
                default=False,
                note="State index; deleting may force re-login / re-index",
            ),
        ],
    ),
    "pi": ToolProfile(
        tool_id="pi",
        name="pi",
        parts=[
            CleanPart(
                key="sessions",
                label="sessions",
                paths=("~/.pi/agent/sessions",),
                note="Resumable sessions for all projects",
            ),
            CleanPart(
                key="npm",
                label="runtime cache",
                paths=("~/.pi/agent/npm",),
                default=False,
                note="pi runtime cache; rebuilt automatically",
            ),
            CleanPart(
                key="models",
                label="downloaded models",
                paths=("~/.pi/models",),
                default=False,
                note="Downloaded local model files",
            ),
        ],
    ),
    "codebuddy": ToolProfile(
        tool_id="codebuddy",
        name="CodeBuddy Code",
        parts=[
            CleanPart(
                key="sessions",
                label="sessions",
                paths=("~/.codebuddy/projects/*",),
                note="Per-project session jsonl + state",
            ),
            CleanPart(
                key="traces",
                label="traces",
                paths=("~/.codebuddy/traces",),
                note="Per-session tool-call traces (debug; can be large)",
            ),
            CleanPart(
                key="logs",
                label="logs",
                paths=("~/.codebuddy/logs",),
                default=False,
                note="Run logs",
            ),
            CleanPart(
                key="blobs",
                label="blobs",
                paths=("~/.codebuddy/blobs",),
                default=False,
                note="Session artifact cache",
            ),
        ],
    ),
    "opencode": ToolProfile(
        tool_id="opencode",
        name="OpenCode",
        parts=[
            CleanPart(
                key="sessions",
                label="sessions db",
                paths=("~/.local/share/opencode/opencode.db*",),
                note="All sessions (new opencode stores them in SQLite)",
            ),
            CleanPart(
                key="snapshot",
                label="snapshots",
                paths=("~/.local/share/opencode/snapshot",),
                note="Rollback snapshots",
            ),
            CleanPart(
                key="logs",
                label="logs",
                paths=("~/.local/share/opencode/log",),
                default=False,
                note="Run logs",
            ),
        ],
    ),
    "cursor": ToolProfile(
        tool_id="cursor",
        name="Cursor (agent)",
        parts=[
            CleanPart(
                key="sessions",
                label="agent sessions",
                paths=("~/.cursor/projects/*/agent-transcripts/*", "~/.cursor/chats/*"),
                note="Agents window / CLI session records",
            ),
        ],
    ),
}


def resolve_part_paths(part: CleanPart) -> list[Path]:
    """Expand a part's path specs into existing paths.

    The last component of a spec may be a glob (``~/.copilot/session-state/*``);
    it is expanded against its parent directory. Results are deduplicated and
    sorted.
    """

    paths: list[Path] = []
    seen: set[Path] = set()
    for spec in part.paths:
        expanded = Path(spec).expanduser()
        if any(ch in spec for ch in "*?["):
            for match in sorted(expanded.parent.glob(expanded.name)):
                if match.exists() and match not in seen:
                    seen.add(match)
                    paths.append(match)
        elif expanded.exists() and expanded not in seen:
            seen.add(expanded)
            paths.append(expanded)
    return paths


def default_override_path() -> Path:
    """Where the user override file is expected to live."""

    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base).expanduser() if base else Path.home() / ".config"
    return root / "toolscripts" / "agent-clean.json"


def read_overrides(path: Path) -> dict:
    """Load the user override file; missing/unreadable/bad JSON -> ``{}``."""

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _part_from_dict(data: dict) -> CleanPart | None:
    """Build a :class:`CleanPart` from a user-supplied dict, or ``None`` if malformed."""

    try:
        return CleanPart(
            key=str(data["key"]),
            label=str(data.get("label", data["key"])),
            paths=tuple(str(p) for p in data["paths"]),
            default=bool(data.get("default", True)),
            note=str(data.get("note", "")),
        )
    except (KeyError, TypeError, ValueError):
        return None


def load_profiles(override_path: Path | None = None) -> list[ToolProfile]:
    """Deep-copy the builtin registry and apply user overrides."""

    profiles = {
        tid: replace(prof, parts=[replace(p) for p in prof.parts])
        for tid, prof in TOOL_PROFILES.items()
    }
    overrides = read_overrides(override_path or default_override_path())
    for tid, data in overrides.get("tools", {}).items():
        if not isinstance(data, dict):
            continue
        prof = profiles.get(tid)
        if prof is None:  # a brand-new tool defined by the user
            prof = ToolProfile(tool_id=tid, name=str(data.get("name", tid)))
            profiles[tid] = prof
        parts = data.get("parts")
        if isinstance(parts, list):
            prof.parts = [
                p for p in (_part_from_dict(d) for d in parts if isinstance(d, dict)) if p
            ]
    return list(profiles.values())
