"""Tests for pi-extensions-setup's pure logic."""

from __future__ import annotations

import json
from pathlib import Path

from toolscripts.commands.ai.pi_extensions import (
    MCP_SERVERS,
    PI_EXTENSIONS,
    _agent_dir,
    _mcp_configured,
    _picker_inputs,
    _pkg_installed,
    _read_settings_packages,
    _remove_mcp_servers,
    _write_mcp_config,
)


def _write_pkg(agent_dir: Path, package: str) -> None:
    pkg_dir = agent_dir / "npm" / "node_modules" / package
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "package.json").write_text(json.dumps({"name": package, "version": "1.0.0"}))


def test_agent_dir_uses_env(monkeypatch) -> None:
    monkeypatch.setenv("PI_CODING_AGENT_DIR", "/tmp/fake-pi")
    assert _agent_dir() == Path("/tmp/fake-pi")


def test_agent_dir_defaults_to_home(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("PI_CODING_AGENT_DIR", raising=False)
    monkeypatch.setattr("toolscripts.commands.ai.pi_extensions.Path.home", lambda: tmp_path)
    assert _agent_dir() == tmp_path / ".pi" / "agent"


def test_read_settings_packages_missing_file(tmp_path: Path) -> None:
    assert _read_settings_packages(tmp_path) == set()


def test_read_settings_packages_parses(tmp_path: Path) -> None:
    (tmp_path / "settings.json").write_text(
        json.dumps({"packages": ["npm:pi-subagents", "npm:context-mode"]})
    )
    assert _read_settings_packages(tmp_path) == {"npm:pi-subagents", "npm:context-mode"}


def test_read_settings_packages_bad_json(tmp_path: Path) -> None:
    (tmp_path / "settings.json").write_text("{not json")
    assert _read_settings_packages(tmp_path) == set()


def test_pkg_installed_via_settings(tmp_path: Path) -> None:
    sources = {"npm:pi-subagents"}
    entry = next(e for e in PI_EXTENSIONS if e.package == "pi-subagents")
    assert _pkg_installed(tmp_path, entry, sources) is True


def test_pkg_installed_via_node_modules(tmp_path: Path) -> None:
    entry = next(e for e in PI_EXTENSIONS if e.package == "pi-subagents")
    _write_pkg(tmp_path, entry.package)
    assert _pkg_installed(tmp_path, entry, set()) is True


def test_pkg_installed_neither(tmp_path: Path) -> None:
    entry = next(e for e in PI_EXTENSIONS if e.package == "pi-subagents")
    assert _pkg_installed(tmp_path, entry, set()) is False


def test_mcp_configured_user_global(tmp_path: Path, monkeypatch) -> None:
    config = tmp_path / ".config" / "mcp" / "mcp.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(json.dumps({"mcpServers": {"context7": {"enabled": True}}}))
    monkeypatch.setattr("toolscripts.commands.ai.pi_extensions.Path.home", lambda: tmp_path)
    assert _mcp_configured("context7") is True
    assert _mcp_configured("playwright") is False


def test_write_mcp_config_preserves_existing(tmp_path: Path) -> None:
    target = tmp_path / "mcp.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"mcpServers": {"existing": {"enabled": False}}}))
    _write_mcp_config(target, {"context7": {"enabled": True}})
    data = json.loads(target.read_text())
    assert set(data["mcpServers"]) == {"existing", "context7"}
    assert data["mcpServers"]["existing"]["enabled"] is False


def test_write_mcp_config_creates_file(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "mcp.json"
    _write_mcp_config(target, {"playwright": {"enabled": True}})
    data = json.loads(target.read_text())
    assert data["mcpServers"]["playwright"]["enabled"] is True


def test_remove_mcp_servers_removes_only_managed(tmp_path: Path) -> None:
    target = tmp_path / "mcp.json"
    target.write_text(
        json.dumps({"mcpServers": {"context7": {"enabled": True}, "other": {"enabled": True}}})
    )
    _remove_mcp_servers(target, ["context7"])
    data = json.loads(target.read_text())
    assert "context7" not in data["mcpServers"]
    assert data["mcpServers"]["other"]["enabled"] is True


def test_remove_mcp_servers_missing_file(tmp_path: Path) -> None:
    target = tmp_path / "mcp.json"
    _remove_mcp_servers(target, ["context7"])
    assert not target.exists()


def test_picker_inputs_marks_and_preselects_installed() -> None:
    names, preselected, tags = _picker_inputs(["a", "b", "c"], {1})
    assert names == ["a", "b", "c"]
    assert preselected == [False, True, False]
    assert tags == [None, "installed", None]


def test_catalog_is_consistent() -> None:
    """Every entry must have a source, a display name, and a help text."""
    assert PI_EXTENSIONS
    assert MCP_SERVERS
    for entry in PI_EXTENSIONS:
        assert entry.source.startswith("npm:")
        assert entry.package
        assert entry.help
    for server in MCP_SERVERS:
        assert server.name
        assert server.help
        assert isinstance(server.config, dict)
