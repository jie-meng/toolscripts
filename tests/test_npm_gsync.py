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
