"""Tests for npm-gsync's pure logic and the shared global-package reader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from toolscripts.commands.system.npm_gsync import (
    build_sync_plan,
    diff_packages,
    resolve_version,
)
from toolscripts.core.npm_global import read_global_packages


def _write_pkg(pkg_dir: Path, version: str) -> None:
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "package.json").write_text(json.dumps({"version": version}), encoding="utf-8")


def test_read_global_packages(tmp_path: Path) -> None:
    modules = tmp_path / "node_modules"
    _write_pkg(modules / "npm", "10.9.4")
    _write_pkg(modules / "corepack", "0.34.0")
    _write_pkg(modules / "appium", "3.6.0")
    _write_pkg(modules / "@deepseek-ai" / "dsh", "0.1.0-rc.6")
    (modules / "@anthropic-ai").mkdir(parents=True)
    (modules / "broken").mkdir(parents=True)

    assert read_global_packages(modules) == {"appium": "3.6.0", "@deepseek-ai/dsh": "0.1.0-rc.6"}


def test_read_global_packages_missing_dir(tmp_path: Path) -> None:
    assert read_global_packages(tmp_path / "missing") == {}


def test_resolve_version() -> None:
    installed = ["v20.19.4", "v22.11.0", "v22.18.0", "v22.22.0"]
    assert resolve_version(installed, "22.22") == "v22.22.0"
    assert resolve_version(installed, "v22.18.0") == "v22.18.0"
    assert resolve_version(installed, "20") == "v20.19.4"
    assert resolve_version(installed, "v22.11.0") == "v22.11.0"
    with pytest.raises(ValueError):
        resolve_version(installed, "22")  # ambiguous
    with pytest.raises(ValueError):
        resolve_version(installed, "24")  # not installed


def test_build_sync_plan() -> None:
    source = {"a": "1.0.0", "b": "2.0.0", "c": "3.0.0"}
    target = {"b": "2.0.0", "d": "9.0.0"}
    assert build_sync_plan(source, target, None, force=False) == [("a", "1.0.0"), ("c", "3.0.0")]
    assert build_sync_plan(source, target, None, force=True) == [
        ("a", "1.0.0"),
        ("b", "2.0.0"),
        ("c", "3.0.0"),
    ]
    assert build_sync_plan(source, target, ["c", "a"], force=False) == [
        ("c", "3.0.0"),
        ("a", "1.0.0"),
    ]
    with pytest.raises(ValueError):
        build_sync_plan(source, target, ["ghost"], force=False)


def test_diff_packages() -> None:
    a = {"a": "1.0.0", "b": "2.0.0"}
    b = {"b": "2.0.1", "c": "3.0.0"}
    only_a, only_b, mismatch = diff_packages(a, b)
    assert only_a == {"a": "1.0.0"}
    assert only_b == {"c": "3.0.0"}
    assert mismatch == {"b": ("2.0.0", "2.0.1")}


# --- wizard (pick flow, with the curses pickers and npm exec mocked) -----


WIZARD_PKGS = {
    "v22.11.0": {"gh": "8.0.0", "pnpm": "10.33.0"},
    "v22.22.0": {"pnpm": "11.21.0"},
}
WIZARD_VERSIONS = ["v22.11.0", "v22.22.0"]


def test_wizard_sync_copies_picked_packages(monkeypatch) -> None:
    from toolscripts.commands.system import npm_gsync as mod
    from toolscripts.core import prompts, ui_curses

    installs: list[tuple] = []
    yes_ones = 0
    select_calls = 0

    def fake_select_one(_title, _items, **kwargs):  # noqa: ARG002
        nonlocal select_calls
        select_calls += 1
        return 0  # source=v22.11.0, target=v22.22.0 (source excluded)

    def fake_select_many(_title, items, *, preselected=None, disabled=None):  # noqa: ARG002
        assert preselected == [True] * len(items)
        return list(range(len(items)))

    def fake_yes_no(_question, *, default=False):  # noqa: ARG002
        nonlocal yes_ones
        yes_ones += 1
        return True

    monkeypatch.setattr(ui_curses, "select_one", fake_select_one)
    monkeypatch.setattr(ui_curses, "select_many", fake_select_many)
    monkeypatch.setattr(prompts, "yes_no", fake_yes_no)
    monkeypatch.setattr(mod, "_run_installs", lambda *a: installs.append(a) or 0)

    mod._wizard_sync(WIZARD_VERSIONS, WIZARD_PKGS, move=False)

    assert select_calls == 2
    assert yes_ones == 1
    assert installs == [("v22.22.0", [("gh", "8.0.0"), ("pnpm", "10.33.0")])]


def test_wizard_move_removes_source_and_deletes_version(monkeypatch) -> None:
    from types import SimpleNamespace

    from toolscripts.commands.system import npm_gsync as mod
    from toolscripts.core import prompts, ui_curses

    uninstalls: list[tuple[str, list[str]]] = []
    runs: list[list[str]] = []
    yes_ones = 0

    def fake_select_one(_title, _items, **kwargs):  # noqa: ARG002
        return 0

    def fake_select_many(_title, items, *, preselected=None, **kwargs):  # noqa: ARG002
        return list(range(len(items)))

    def fake_yes_no(_question, *, default=False):  # noqa: ARG002
        nonlocal yes_ones
        yes_ones += 1
        return True

    def fake_run(cmd, **kwargs):  # noqa: ARG002
        runs.append(list(cmd))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(ui_curses, "select_one", fake_select_one)
    monkeypatch.setattr(ui_curses, "select_many", fake_select_many)
    monkeypatch.setattr(prompts, "yes_no", fake_yes_no)
    monkeypatch.setattr(mod, "_run_installs", lambda *a: 0)
    monkeypatch.setattr(mod, "_run_uninstalls", lambda *a: uninstalls.append(a) or 0)
    monkeypatch.setattr(mod, "run", fake_run)

    mod._wizard_sync(WIZARD_VERSIONS, WIZARD_PKGS, move=True)

    assert yes_ones == 3  # install confirm, remove-from-source confirm, delete version
    assert uninstalls == [("v22.11.0", ["gh", "pnpm"])]
    assert runs == [["fnm", "uninstall", "v22.11.0"]]


def test_wizard_clean_removes_picked_packages(monkeypatch) -> None:
    from toolscripts.commands.system import npm_gsync as mod
    from toolscripts.core import prompts, ui_curses

    uninstalls: list[tuple[str, list[str]]] = []
    yes_ones = 0

    def fake_select_one(_title, _items, **kwargs):  # noqa: ARG002
        return 0  # v22.11.0

    def fake_select_many(_title, _items, **kwargs):  # noqa: ARG002
        return [1]  # only pnpm

    def fake_yes_no(_question, *, default=False):  # noqa: ARG002
        nonlocal yes_ones
        yes_ones += 1
        return True

    monkeypatch.setattr(ui_curses, "select_one", fake_select_one)
    monkeypatch.setattr(ui_curses, "select_many", fake_select_many)
    monkeypatch.setattr(prompts, "yes_no", fake_yes_no)
    monkeypatch.setattr(mod, "_run_uninstalls", lambda *a: uninstalls.append(a) or 0)

    mod._wizard_clean(WIZARD_VERSIONS, WIZARD_PKGS)

    assert yes_ones == 1
    assert uninstalls == [("v22.11.0", ["pnpm"])]


def test_wizard_cancel_aborts_without_changes(monkeypatch) -> None:
    from toolscripts.commands.system import npm_gsync as mod
    from toolscripts.core import ui_curses

    called = False

    def boom(*args, **kwargs):  # noqa: ARG002
        nonlocal called
        called = True

    monkeypatch.setattr(ui_curses, "select_one", lambda *a, **k: None)  # user pressed Esc
    monkeypatch.setattr(mod, "_run_installs", boom)

    mod._wizard_sync(WIZARD_VERSIONS, WIZARD_PKGS, move=False)

    assert not called
