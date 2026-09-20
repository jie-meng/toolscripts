"""Read npm's globally installed packages from a ``node_modules`` directory.

Pure filesystem utility shared by ``npm-tools`` (the active node) and
``npm-gsync`` (any fnm-managed node version).
"""

from __future__ import annotations

import json
from pathlib import Path

#: Bundled with every Node.js install - never user-installed globals.
SYSTEM_PACKAGES = frozenset({"npm", "corepack"})


def _is_trash(name: str) -> bool:
    """True for npm's housekeeping entries, which are never real packages.

    While replacing a package, arborist renames the old copy aside to
    ``.<name>-<path hash>`` (see ``@npmcli/arborist/lib/retire-path.js``) and only
    deletes it once the whole install succeeds - an interrupted install leaves it
    behind, complete with the old ``package.json``. No valid npm package name can
    start with a dot, so the prefix identifies the trash plus ``.bin``/``.pnpm``.
    """
    return name.startswith(".")


def read_global_packages(modules_dir: Path) -> dict[str, str]:
    """Return ``name -> version`` for top-level packages under ``modules_dir``.

    Skips the Node-bundled ``npm``/``corepack``, npm's trash and dot directories,
    and entries without a ``package.json`` (e.g. empty ``@scope`` leftovers).
    """
    packages: dict[str, str] = {}
    if not modules_dir.is_dir():
        return packages
    for entry in sorted(modules_dir.iterdir()):
        if _is_trash(entry.name) or not entry.is_dir():
            continue
        if entry.name.startswith("@"):
            for sub in sorted(entry.iterdir()):
                if not _is_trash(sub.name) and sub.is_dir():
                    _record(packages, f"{entry.name}/{sub.name}", sub)
        else:
            _record(packages, entry.name, entry)
    return packages


def _record(packages: dict[str, str], name: str, pkg_dir: Path) -> None:
    if name in SYSTEM_PACKAGES:
        return
    version = _read_version(pkg_dir)
    if version is not None:
        packages[name] = version


def _read_version(pkg_dir: Path) -> str | None:
    try:
        data = json.loads((pkg_dir / "package.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    version = data.get("version")
    return version if isinstance(version, str) and version else None
