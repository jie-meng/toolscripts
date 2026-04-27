"""``axios-audit`` - audit a directory for vulnerable axios versions.

Migrated from ``security/axios-audit.py``. Detects axios 1.14.1 / 0.30.4 in
package.json and lockfiles, optionally patching them.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time

from toolscripts.core.colors import colored
from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)

VULNERABLE_VERSIONS = {"1.14.1", "0.30.4"}
SAFE_VERSIONS = {"1.x": "1.14.0", "0.x": "0.30.3"}
MALICIOUS_PKG = "plain-crypto-js"

_tmp = os.environ.get(
    "TEMP",
    os.path.join(
        os.environ.get("USERPROFILE", "C:\\Users\\Default"), "AppData", "Local", "Temp"
    ),
)
_pd = os.environ.get("PROGRAMDATA", "C:\\ProgramData")
IOC_PATHS: dict[str, list[str]] = {
    "darwin": ["/Library/Caches/com.apple.act.mond"],
    "linux": ["/tmp/ld.py"],
    "win32": [
        os.path.join(_pd, "wt.exe"),
        os.path.join(_tmp, "6202033.vbs"),
        os.path.join(_tmp, "6202033.ps1"),
    ],
}


_last_progress = 0.0


def _print_progress(path: str) -> None:
    global _last_progress
    now = time.monotonic()
    if now - _last_progress < 0.1:
        return
    _last_progress = now
    label = path if len(path) <= 65 else "..." + path[-62:]
    print(f"\r  Scanning: {label:<65}", end="", file=sys.stderr, flush=True)


def _clear_progress() -> None:
    print("\r" + " " * 82 + "\r", end="", file=sys.stderr, flush=True)


def _parse_version(version: str) -> str:
    match = re.match(r"^[\^~>=<\s]*(\d+\.\d+\.\d+)", version.strip())
    return match.group(1) if match else version.strip()


def _is_vulnerable(version: str) -> bool:
    return _parse_version(version) in VULNERABLE_VERSIONS


def _has_unsafe_prefix(version: str) -> bool:
    version = version.strip()
    if not (version.startswith("^") or version.startswith("~")):
        return False
    parts = _parse_version(version).split(".")
    if len(parts) < 2:
        return False
    major, minor = int(parts[0]), int(parts[1])
    if major == 1 and minor <= 14:
        return True
    if major == 0 and minor == 30:
        return True
    return False


def _safe_version_for(version: str) -> str | None:
    parts = _parse_version(version).split(".")
    if not parts:
        return None
    return SAFE_VERSIONS.get(f"{parts[0]}.x")


def _detect_pm(project_dir: str) -> str:
    if os.path.exists(os.path.join(project_dir, "yarn.lock")):
        return "yarn"
    if os.path.exists(os.path.join(project_dir, "pnpm-lock.yaml")):
        return "pnpm"
    return "npm"


def _audit_package_json(filepath: str, findings: dict) -> None:
    try:
        with open(filepath) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        log.error("could not parse %s: %s", filepath, exc)
        return
    rel = os.path.relpath(filepath)
    for section in (
        "dependencies",
        "devDependencies",
        "peerDependencies",
        "optionalDependencies",
    ):
        version = data.get(section, {}).get("axios")
        if version is None:
            continue
        entry = {"file": filepath, "rel": rel, "version": version, "section": section}
        if _is_vulnerable(version):
            findings["critical"].append({**entry, "type": "vulnerable"})
        elif _has_unsafe_prefix(version):
            findings["warning"].append({**entry, "type": "unpinned"})
        else:
            findings["ok"].append(entry)


def _audit_package_lock(filepath: str, findings: dict) -> None:
    try:
        with open(filepath) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        log.error("could not parse %s: %s", filepath, exc)
        return
    rel = os.path.relpath(filepath)
    project_dir = os.path.dirname(filepath)
    for pkg_path, info in data.get("packages", {}).items():
        if pkg_path.endswith("node_modules/axios"):
            version = info.get("version", "")
            if _is_vulnerable(version):
                findings["critical"].append(
                    {
                        "file": filepath,
                        "rel": rel,
                        "version": version,
                        "type": "lockfile_vulnerable",
                        "project_dir": project_dir,
                    }
                )
        if MALICIOUS_PKG in pkg_path:
            findings["ioc"].append(
                {
                    "type": "lockfile_malicious_pkg",
                    "detail": f"{rel} contains {MALICIOUS_PKG}",
                }
            )
    deps_v1 = data.get("dependencies", {})
    version = deps_v1.get("axios", {}).get("version", "")
    if version and _is_vulnerable(version):
        findings["critical"].append(
            {
                "file": filepath,
                "rel": rel,
                "version": version,
                "type": "lockfile_vulnerable",
                "project_dir": project_dir,
            }
        )
    if MALICIOUS_PKG in deps_v1:
        findings["ioc"].append(
            {
                "type": "lockfile_malicious_pkg",
                "detail": f"{rel} contains {MALICIOUS_PKG}",
            }
        )


def _audit_yarn_lock(filepath: str, findings: dict) -> None:
    try:
        with open(filepath) as f:
            content = f.read()
    except OSError as exc:
        log.error("could not read %s: %s", filepath, exc)
        return
    rel = os.path.relpath(filepath)
    project_dir = os.path.dirname(filepath)
    pattern = re.compile(
        r'(?:"axios@[^"]*"|axios@\S+)\s*:\s*\n\s*version[: ]+"?([^\s"]+)"?',
        re.MULTILINE,
    )
    seen: set[str] = set()
    for match in pattern.finditer(content):
        version = match.group(1)
        if version not in seen and _is_vulnerable(version):
            seen.add(version)
            findings["critical"].append(
                {
                    "file": filepath,
                    "rel": rel,
                    "version": version,
                    "type": "yarn_lock_vulnerable",
                    "project_dir": project_dir,
                }
            )
    if MALICIOUS_PKG in content:
        findings["ioc"].append(
            {
                "type": "lockfile_malicious_pkg",
                "detail": f"{rel} contains {MALICIOUS_PKG}",
            }
        )


def _audit_pnpm_lock(filepath: str, findings: dict) -> None:
    try:
        with open(filepath) as f:
            content = f.read()
    except OSError as exc:
        log.error("could not read %s: %s", filepath, exc)
        return
    rel = os.path.relpath(filepath)
    project_dir = os.path.dirname(filepath)
    pattern = re.compile(r"['\"/\s]axios[@/](\d+\.\d+\.\d+)", re.MULTILINE)
    seen: set[str] = set()
    for match in pattern.finditer(content):
        version = match.group(1)
        if version not in seen and _is_vulnerable(version):
            seen.add(version)
            findings["critical"].append(
                {
                    "file": filepath,
                    "rel": rel,
                    "version": version,
                    "type": "pnpm_lock_vulnerable",
                    "project_dir": project_dir,
                }
            )
    if MALICIOUS_PKG in content:
        findings["ioc"].append(
            {
                "type": "lockfile_malicious_pkg",
                "detail": f"{rel} contains {MALICIOUS_PKG}",
            }
        )


def _scan_iocs() -> list[str]:
    return [path for path in IOC_PATHS.get(sys.platform, []) if os.path.exists(path)]


def _scan_plain_crypto_js(target_dir: str) -> list[str]:
    found: list[str] = []
    for root, dirs, _ in os.walk(target_dir):
        if os.path.basename(root) == "node_modules":
            malicious = os.path.join(root, MALICIOUS_PKG)
            if os.path.isdir(malicious):
                found.append(os.path.relpath(malicious))
            dirs[:] = []
    return found


def _fix_package_json(filepath: str, items: list[dict]) -> bool:
    try:
        with open(filepath) as f:
            content = f.read()
    except OSError as exc:
        log.error("cannot read %s: %s", filepath, exc)
        return False
    rel = os.path.relpath(filepath)
    new_content = content
    fixed = False
    for item in items:
        old = item["version"]
        target = _safe_version_for(old)
        if not target:
            log.warning("no safe version for axios@%s in %s", old, rel)
            continue
        updated = re.sub(
            r'("axios"\s*:\s*)"' + re.escape(old) + r'"',
            rf'\g<1>"{target}"',
            new_content,
        )
        if updated != new_content:
            log.warning('fixed %s: "%s" -> "%s"', rel, old, target)
            new_content = updated
            fixed = True
    if fixed:
        try:
            with open(filepath, "w") as f:
                f.write(new_content)
        except OSError as exc:
            log.error("cannot write %s: %s", filepath, exc)
            return False
    return fixed


def _add_overrides(filepath: str, safe: str, pm: str) -> bool:
    try:
        with open(filepath) as f:
            content = f.read()
            data = json.loads(content)
    except (OSError, json.JSONDecodeError) as exc:
        log.error("cannot read %s: %s", filepath, exc)
        return False
    rel = os.path.relpath(filepath)
    if pm == "yarn":
        section = data.setdefault("resolutions", {})
        key = "resolutions.axios"
    elif pm == "pnpm":
        section = data.setdefault("pnpm", {}).setdefault("overrides", {})
        key = "pnpm.overrides.axios"
    else:
        section = data.setdefault("overrides", {})
        key = "overrides.axios"
    if section.get("axios") == safe:
        return False
    section["axios"] = safe
    log.warning('added %s="%s" to %s (transitive dep pin)', key, safe, rel)
    indent = 2
    for line in content.splitlines():
        stripped = line.lstrip()
        if stripped and stripped != line:
            indent = len(line) - len(stripped)
            break
    try:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=indent)
            f.write("\n")
        return True
    except OSError as exc:
        log.error("cannot write %s: %s", filepath, exc)
        return False


def _run_install(project_dir: str) -> bool:
    pm = _detect_pm(project_dir)
    cmd = {"npm": ["npm", "install"], "yarn": ["yarn", "install"], "pnpm": ["pnpm", "install"]}[
        pm
    ]
    rel = os.path.relpath(project_dir) or "."
    log.info("running %s in %s", " ".join(cmd), rel)
    try:
        result = subprocess.run(
            cmd, cwd=project_dir, capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            log.success("lockfile regenerated in %s", rel)
            return True
        log.error("install failed in %s:\n%s", rel, result.stderr.strip())
        return False
    except FileNotFoundError:
        log.error("'%s' not found - run '%s' manually", pm, " ".join(cmd))
        return False
    except subprocess.TimeoutExpired:
        log.error("install timed out in %s", rel)
        return False


def _audit_directory(target_dir: str, *, fix: bool) -> bool:
    findings: dict[str, list[dict]] = {
        "critical": [],
        "warning": [],
        "ok": [],
        "ioc": [],
    }
    print(colored(f"Axios Security Audit: {os.path.abspath(target_dir)}", "cyan", bold=True))
    log.info("vulnerable: %s", ", ".join(sorted(VULNERABLE_VERSIONS)))
    log.info("safe pin:   %s", ", ".join(SAFE_VERSIONS.values()))

    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d != "node_modules"]
        _print_progress(os.path.relpath(root, target_dir) or ".")
        for filename in files:
            filepath = os.path.join(root, filename)
            if filename == "package.json":
                _audit_package_json(filepath, findings)
            elif filename == "package-lock.json":
                _audit_package_lock(filepath, findings)
            elif filename == "yarn.lock":
                _audit_yarn_lock(filepath, findings)
            elif filename == "pnpm-lock.yaml":
                _audit_pnpm_lock(filepath, findings)
    _clear_progress()

    for path in _scan_iocs():
        findings["ioc"].append({"type": "fs_ioc", "detail": path})
    for path in _scan_plain_crypto_js(target_dir):
        findings["ioc"].append({"type": "malicious_pkg", "detail": path})

    if findings["ioc"]:
        log.error("indicators of compromise detected!")
        for item in findings["ioc"]:
            log.error("  %s: %s", item["type"], item["detail"])
        log.error("rotate credentials, contact infosec")

    for item in findings["critical"]:
        safe = _safe_version_for(item["version"]) or "safe version"
        log.error("CRITICAL %s axios@%s -> %s", item["rel"], item["version"], safe)
    for item in findings["warning"]:
        safe = _safe_version_for(item["version"]) or "safe version"
        log.warning("UNPINNED %s axios@%s (pin to %s)", item["rel"], item["version"], safe)
    for item in findings["ok"]:
        log.success("OK %s axios@%s", item["rel"], item["version"])

    if not (findings["critical"] or findings["warning"] or findings["ok"]):
        log.info("no axios dependency found in %s", target_dir)

    if fix:
        fixable: dict[str, list[dict]] = {}
        for item in findings["critical"]:
            if item["type"] == "vulnerable":
                fixable.setdefault(item["file"], []).append(item)
        for item in findings["warning"]:
            if item["type"] == "unpinned":
                fixable.setdefault(item["file"], []).append(item)

        install_dirs: set[str] = set()
        fixable_dirs: set[str] = set()
        for filepath, items in fixable.items():
            if _fix_package_json(filepath, items):
                d = os.path.dirname(filepath)
                install_dirs.add(d)
                fixable_dirs.add(d)

        lockfile_types = {
            "lockfile_vulnerable",
            "yarn_lock_vulnerable",
            "pnpm_lock_vulnerable",
        }
        transitive_handled: set[str] = set()
        for item in findings["critical"]:
            if item["type"] not in lockfile_types:
                continue
            pdir = os.path.abspath(item.get("project_dir", os.path.dirname(item["file"])))
            install_dirs.add(pdir)
            if pdir in fixable_dirs or pdir in transitive_handled:
                continue
            pkg = os.path.join(pdir, "package.json")
            if os.path.exists(pkg):
                target = _safe_version_for(item["version"]) or "1.14.0"
                pm = _detect_pm(pdir)
                if _add_overrides(pkg, target, pm):
                    transitive_handled.add(pdir)

        for d in sorted(install_dirs):
            _run_install(d)

    return not (findings["ioc"] or findings["critical"])


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="axios-audit",
        description="Audit a directory for vulnerable axios versions (1.14.1 / 0.30.4).",
    )
    parser.add_argument(
        "directory", nargs="?", default=".", help="directory to audit (default: cwd)"
    )
    parser.add_argument("--fix", action="store_true", help="patch package.json + reinstall")
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    target = os.path.abspath(args.directory)
    if not os.path.isdir(target):
        log.error("not a directory: %s", target)
        sys.exit(1)
    sys.exit(0 if _audit_directory(target, fix=args.fix) else 1)


if __name__ == "__main__":
    main()
