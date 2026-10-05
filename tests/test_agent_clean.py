"""Tests for agent-clean's pure logic (registry resolution, override, selection)."""

from __future__ import annotations

import json
from pathlib import Path

from toolscripts.commands.system.agent_clean import build_rows, select_matching_rows
from toolscripts.commands.system.agent_clean_profiles import (
    TOOL_PROFILES,
    CleanPart,
    ToolProfile,
    load_profiles,
    read_overrides,
    resolve_part_paths,
)
from toolscripts.core.size import human_size, path_size


def test_human_size() -> None:
    assert human_size(0) == "0B"
    assert human_size(512) == "512B"
    assert human_size(1024) == "1.0K"
    assert human_size(456 * 1024 * 1024) == "456M"
    assert human_size(1_500 * 1024 * 1024) == "1.5G"


def test_path_size_tallies_files(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_bytes(b"x" * 100)
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.txt").write_bytes(b"x" * 50)
    assert path_size(tmp_path) == 150


def test_resolve_part_paths_plain_and_missing(tmp_path: Path) -> None:
    (tmp_path / "keep").mkdir()
    part = CleanPart("p", "p", (str(tmp_path / "nope"), str(tmp_path / "keep")), note="")
    resolved = resolve_part_paths(part)
    assert resolved == [tmp_path / "keep"]


def test_resolve_part_paths_globs(tmp_path: Path) -> None:
    for name in ("1111", "2222"):
        (tmp_path / name).mkdir()
    part = CleanPart("p", "p", (str(tmp_path / "1*"), str(tmp_path / "missing-*")), note="")
    resolved = resolve_part_paths(part)
    assert sorted(p.name for p in resolved) == ["1111"]


def _tiny_profile(root: Path) -> ToolProfile:
    (root / "sessions").mkdir()
    (root / "sessions" / "s1.jsonl").write_bytes(b"x" * 300)
    (root / "logs").mkdir()
    (root / "logs" / "run.log").write_bytes(b"x" * 100)
    return ToolProfile(
        tool_id="fake",
        name="Fake CLI",
        parts=[
            CleanPart("sessions", "sessions", (str(root / "sessions"),), note=""),
            CleanPart("logs", "logs", (str(root / "logs"),), default=False, note=""),
            CleanPart("missing", "missing", (str(root / "nope"),), note=""),
        ],
    )


def test_build_rows_sizes_and_skips_missing(tmp_path: Path) -> None:
    rows = build_rows([_tiny_profile(tmp_path)])
    assert {r.part.key for r in rows} == {"sessions", "logs"}
    by_key = {r.part.key: r for r in rows}
    assert by_key["sessions"].size == 300
    assert by_key["logs"].size == 100
    assert by_key["sessions"].part.default is True
    assert by_key["logs"].part.default is False


def test_select_matching_rows_defaults_vs_specific(tmp_path: Path) -> None:
    rows = build_rows([_tiny_profile(tmp_path)])

    default = select_matching_rows(rows, ["fake"])
    assert default is not None
    assert [r.part.key for r in default] == ["sessions"]

    specific = select_matching_rows(rows, ["fake:logs"])
    assert specific is not None
    assert [r.part.key for r in specific] == ["logs"]

    unknown = select_matching_rows(rows, ["fake:nope"])
    assert unknown is None


def test_select_matching_rows_deduplicates(tmp_path: Path) -> None:
    rows = build_rows([_tiny_profile(tmp_path)])
    picked = select_matching_rows(rows, ["fake", "fake:sessions"])
    assert picked is not None
    assert len(picked) == 1


def test_read_overrides_missing_and_bad_json(tmp_path: Path) -> None:
    assert read_overrides(tmp_path / "nope.json") == {}
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert read_overrides(bad) == {}


def test_load_profiles_applies_user_override(tmp_path: Path) -> None:
    override = tmp_path / "agent-clean.json"
    override.write_text(
        json.dumps(
            {
                "tools": {
                    "zcode": {
                        "parts": [
                            {
                                "key": "archive",
                                "label": "archive",
                                "paths": [str(tmp_path / "custom-archive")],
                            }
                        ]
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "custom-archive").mkdir()
    profiles = {p.tool_id: p for p in load_profiles(override)}
    zcode = profiles["zcode"]
    assert [p.key for p in zcode.parts] == ["archive"]
    assert resolve_part_paths(zcode.parts[0]) == [tmp_path / "custom-archive"]


def test_load_profiles_adds_new_tool(tmp_path: Path) -> None:
    override = tmp_path / "agent-clean.json"
    override.write_text(
        json.dumps(
            {
                "tools": {
                    "my-tool": {
                        "name": "My Tool",
                        "parts": [
                            {"key": "s", "label": "sessions", "paths": [str(tmp_path / "d")]}
                        ],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "d").mkdir()
    profiles = {p.tool_id: p for p in load_profiles(override)}
    assert profiles["my-tool"].name == "My Tool"


def test_registry_contains_cli_agents_only() -> None:
    """GUI/IDE agents are out of scope and must not appear in the registry."""
    assert "qoder" not in TOOL_PROFILES
    assert "zcode" not in TOOL_PROFILES
    assert "workbuddy" not in TOOL_PROFILES
    assert "dsh" not in TOOL_PROFILES
    # The CLI agents stay.
    assert {"copilot", "cline", "pi", "codebuddy", "opencode", "cursor"} <= set(TOOL_PROFILES)
