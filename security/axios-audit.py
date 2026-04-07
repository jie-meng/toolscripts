#!/usr/bin/env python3
"""
Audit a directory recursively for vulnerable axios versions (1.14.1 and 0.30.4).

Scans package.json, package-lock.json, yarn.lock, and pnpm-lock.yaml to detect:
- Direct or transitive dependencies on axios@1.14.1 or axios@0.30.4
- Unpinned axios versions (^ or ~) that could resolve to malicious versions
- Presence of the injected malicious package plain-crypto-js
- Filesystem indicators of compromise (IOCs) left by the RAT

Usage:
    axios-audit <directory> [--fix]

Options:
    --fix    Patch axios versions in package.json (including transitive overrides)
             and regenerate lockfiles
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
NC = "\033[0m"

VULNERABLE_VERSIONS = {"1.14.1", "0.30.4"}
SAFE_VERSIONS = {
    "1.x": "1.14.0",
    "0.x": "0.30.3",
}

# The malicious dependency injected by the attacker
MALICIOUS_PKG = "plain-crypto-js"

# Filesystem IOCs left by the RAT after installation
# Source: StepSecurity / Aikido security bulletins
_tmp = os.environ.get("TEMP", os.path.join(os.environ.get("USERPROFILE", "C:\\Users\\Default"), "AppData", "Local", "Temp"))
_pd = os.environ.get("PROGRAMDATA", "C:\\ProgramData")
IOC_PATHS: dict[str, list[str]] = {
    "darwin": ["/Library/Caches/com.apple.act.mond"],
    "linux":  ["/tmp/ld.py"],
    "win32":  [
        os.path.join(_pd, "wt.exe"),
        os.path.join(_tmp, "6202033.vbs"),
        os.path.join(_tmp, "6202033.ps1"),
    ],
}

# ---------------------------------------------------------------------------
# Progress indicator — writes to stderr so it doesn't pollute stdout findings
# ---------------------------------------------------------------------------

_last_progress: float = 0.0


def _print_progress(path: str) -> None:
    global _last_progress
    now = time.monotonic()
    if now - _last_progress < 0.1:  # update at most ~10×/sec
        return
    _last_progress = now
    label = path if len(path) <= 65 else "..." + path[-62:]
    print(f"\r  {CYAN}Scanning:{NC} {label:<65}", end="", file=sys.stderr, flush=True)


def _clear_progress() -> None:
    print("\r" + " " * 82 + "\r", end="", file=sys.stderr, flush=True)


def print_header(text):
    print(f"\n{BOLD}{CYAN}{'=' * 60}{NC}")
    print(f"{BOLD}{CYAN}  {text}{NC}")
    print(f"{BOLD}{CYAN}{'=' * 60}{NC}")


def print_error(text):
    print(f"{RED}  [CRITICAL] {text}{NC}")


def print_warning(text):
    print(f"{YELLOW}  [WARNING]  {text}{NC}")


def print_success(text):
    print(f"{GREEN}  [OK]       {text}{NC}")


def print_info(text):
    print(f"  {CYAN}[INFO]     {text}{NC}")


def parse_version(version_str):
    """Extract clean semver from a version string that may have ^, ~, or other prefixes."""
    match = re.match(r"^[\^~>=<\s]*(\d+\.\d+\.\d+)", version_str.strip())
    return match.group(1) if match else version_str.strip()


def is_vulnerable(version_str):
    return parse_version(version_str) in VULNERABLE_VERSIONS


def has_unsafe_prefix(version_str):
    """Return True if the version range (^ or ~) can resolve to a vulnerable version."""
    version_str = version_str.strip()
    if not (version_str.startswith("^") or version_str.startswith("~")):
        return False
    clean = parse_version(version_str)
    parts = clean.split(".")
    if len(parts) < 2:
        return False
    major, minor = int(parts[0]), int(parts[1])
    # ^1.x.x resolves up to <2.0.0 — any 1.x where x <= 14 can pull 1.14.1
    if major == 1 and minor <= 14:
        return True
    # ^0.30.x / ~0.30.x resolves within 0.30.x — can pull 0.30.4
    # ^0.29.x resolves to <0.30.0 so it is safe — only flag minor == 30
    if major == 0 and minor == 30:
        return True
    return False


def get_major_branch(version_str):
    """Return '1.x' or '0.x' for the given version string."""
    parts = parse_version(version_str).split(".")
    return f"{parts[0]}.x" if parts else None


def safe_version_for(version_str):
    branch = get_major_branch(version_str)
    return SAFE_VERSIONS.get(branch) if branch else None


# ---------------------------------------------------------------------------
# IOC & malicious package scanning
# ---------------------------------------------------------------------------

def scan_iocs() -> list[str]:
    """Check the local machine for known malware persistence paths left by the RAT."""
    found = []
    for path in IOC_PATHS.get(sys.platform, []):
        if os.path.exists(path):
            found.append(path)
    return found


def scan_plain_crypto_js(target_dir: str) -> list[str]:
    """Scan node_modules trees under target_dir for the malicious plain-crypto-js package."""
    found = []
    for root, dirs, _ in os.walk(target_dir):
        # Only descend into node_modules to look for the malicious package;
        # prune any nested node_modules once we've found the top-level one.
        if os.path.basename(root) == "node_modules":
            malicious = os.path.join(root, MALICIOUS_PKG)
            if os.path.isdir(malicious):
                found.append(os.path.relpath(malicious))
            dirs[:] = []  # don't recurse deeper inside node_modules
    return found


# ---------------------------------------------------------------------------
# Audit functions — each appends to findings and stores the absolute filepath
# ---------------------------------------------------------------------------

def audit_package_json(filepath, findings):
    try:
        with open(filepath) as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print_error(f"Failed to parse {filepath}: {e}")
        return

    rel = os.path.relpath(filepath)
    for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        version = data.get(section, {}).get("axios")
        if version is None:
            continue
        entry = {"file": filepath, "rel": rel, "version": version, "section": section}
        if is_vulnerable(version):
            findings["critical"].append({**entry, "type": "vulnerable"})
        elif has_unsafe_prefix(version):
            findings["warning"].append({**entry, "type": "unpinned"})
        else:
            findings["ok"].append(entry)


def audit_package_lock(filepath, findings):
    try:
        with open(filepath) as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print_error(f"Failed to parse {filepath}: {e}")
        return

    rel = os.path.relpath(filepath)
    project_dir = os.path.dirname(filepath)

    # lockfile v2/v3
    for pkg_path, pkg_info in data.get("packages", {}).items():
        if pkg_path.endswith("node_modules/axios"):
            version = pkg_info.get("version", "")
            if is_vulnerable(version):
                findings["critical"].append({
                    "file": filepath, "rel": rel, "version": version,
                    "type": "lockfile_vulnerable", "project_dir": project_dir,
                })
        if MALICIOUS_PKG in pkg_path:
            findings["ioc"].append({
                "type": "lockfile_malicious_pkg", "detail": f"{rel} contains {MALICIOUS_PKG}",
            })

    # lockfile v1
    deps_v1 = data.get("dependencies", {})
    version = deps_v1.get("axios", {}).get("version", "")
    if version and is_vulnerable(version):
        findings["critical"].append({
            "file": filepath, "rel": rel, "version": version,
            "type": "lockfile_vulnerable", "project_dir": project_dir,
        })
    if MALICIOUS_PKG in deps_v1:
        findings["ioc"].append({
            "type": "lockfile_malicious_pkg", "detail": f"{rel} contains {MALICIOUS_PKG}",
        })


def audit_yarn_lock(filepath, findings):
    try:
        with open(filepath) as f:
            content = f.read()
    except IOError as e:
        print_error(f"Failed to read {filepath}: {e}")
        return

    rel = os.path.relpath(filepath)
    project_dir = os.path.dirname(filepath)

    # Matches both Yarn v1 (unquoted) and Yarn v2/Berry (quoted) entry formats:
    #   Yarn v1:  axios@^1.14.0:\n  version "1.14.1"
    #   Yarn v2:  "axios@npm:^1.14.0":\n  version: 1.14.1
    pattern = re.compile(
        r'(?:"axios@[^"]*"|axios@\S+)\s*:\s*\n\s*version[: ]+"?([^\s"]+)"?',
        re.MULTILINE,
    )
    seen = set()
    for match in pattern.finditer(content):
        version = match.group(1)
        if version not in seen and is_vulnerable(version):
            seen.add(version)
            findings["critical"].append({
                "file": filepath, "rel": rel, "version": version,
                "type": "yarn_lock_vulnerable", "project_dir": project_dir,
            })

    if MALICIOUS_PKG in content:
        findings["ioc"].append({
            "type": "lockfile_malicious_pkg", "detail": f"{rel} contains {MALICIOUS_PKG}",
        })


def audit_pnpm_lock(filepath, findings):
    try:
        with open(filepath) as f:
            content = f.read()
    except IOError as e:
        print_error(f"Failed to read {filepath}: {e}")
        return

    rel = os.path.relpath(filepath)
    project_dir = os.path.dirname(filepath)

    # Matches pnpm-lock.yaml entries like:
    #   /axios@1.14.1:   (v5 format)
    #   /axios/1.14.1:   (v6 format)
    pattern = re.compile(r"['\"/\s]axios[@/](\d+\.\d+\.\d+)", re.MULTILINE)
    seen = set()
    for match in pattern.finditer(content):
        version = match.group(1)
        if version not in seen and is_vulnerable(version):
            seen.add(version)
            findings["critical"].append({
                "file": filepath, "rel": rel, "version": version,
                "type": "pnpm_lock_vulnerable", "project_dir": project_dir,
            })

    if MALICIOUS_PKG in content:
        findings["ioc"].append({
            "type": "lockfile_malicious_pkg", "detail": f"{rel} contains {MALICIOUS_PKG}",
        })


# ---------------------------------------------------------------------------
# Fix functions
# ---------------------------------------------------------------------------

def fix_package_json(filepath, items):
    """
    Patch axios versions in package.json using string replacement to preserve
    the original file formatting. Handles both exact vulnerable versions and
    unpinned ranges.
    """
    try:
        with open(filepath) as f:
            content = f.read()
    except IOError as e:
        print_error(f"Cannot read {filepath}: {e}")
        return False

    rel = os.path.relpath(filepath)
    new_content = content
    fixed = False

    for item in items:
        old_version = item["version"]
        target = safe_version_for(old_version)
        if not target:
            print_warning(f"No safe version found for axios@{old_version} in {rel}, skipping.")
            continue

        # Replace only the axios version value, preserving surrounding formatting
        updated = re.sub(
            r'("axios"\s*:\s*)"' + re.escape(old_version) + r'"',
            rf'\g<1>"{target}"',
            new_content,
        )
        if updated != new_content:
            print_warning(f"Fixed {rel}: \"{old_version}\" → \"{target}\"")
            new_content = updated
            fixed = True

    if fixed:
        try:
            with open(filepath, "w") as f:
                f.write(new_content)
        except IOError as e:
            print_error(f"Cannot write {filepath}: {e}")
            return False

    return fixed


def detect_package_manager(project_dir):
    if os.path.exists(os.path.join(project_dir, "yarn.lock")):
        return "yarn"
    if os.path.exists(os.path.join(project_dir, "pnpm-lock.yaml")):
        return "pnpm"
    return "npm"


def add_overrides_to_package_json(filepath: str, safe_version: str, pm: str) -> bool:
    """
    Add axios version overrides/resolutions to package.json to pin transitive
    dependencies to a safe version.

    npm  → "overrides": {"axios": "1.14.0"}
    yarn → "resolutions": {"axios": "1.14.0"}
    pnpm → "pnpm": {"overrides": {"axios": "1.14.0"}}
    """
    try:
        with open(filepath) as f:
            content = f.read()
            data = json.loads(content)
    except (json.JSONDecodeError, IOError) as e:
        print_error(f"Cannot read {filepath}: {e}")
        return False

    rel = os.path.relpath(filepath)

    if pm == "yarn":
        resolutions = data.setdefault("resolutions", {})
        if resolutions.get("axios") == safe_version:
            return False
        resolutions["axios"] = safe_version
        print_warning(f"Added resolutions.axios=\"{safe_version}\" to {rel} (transitive dep pin)")
    elif pm == "pnpm":
        pnpm_section = data.setdefault("pnpm", {})
        overrides = pnpm_section.setdefault("overrides", {})
        if overrides.get("axios") == safe_version:
            return False
        overrides["axios"] = safe_version
        print_warning(f"Added pnpm.overrides.axios=\"{safe_version}\" to {rel} (transitive dep pin)")
    else:
        overrides = data.setdefault("overrides", {})
        if overrides.get("axios") == safe_version:
            return False
        overrides["axios"] = safe_version
        print_warning(f"Added overrides.axios=\"{safe_version}\" to {rel} (transitive dep pin)")

    # Detect original indentation to minimise diff noise
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
    except IOError as e:
        print_error(f"Cannot write {filepath}: {e}")
        return False


def run_install(project_dir):
    """Re-run the package manager to regenerate the lockfile with safe versions."""
    pm = detect_package_manager(project_dir)
    cmd = {
        "npm": ["npm", "install"],
        "yarn": ["yarn", "install"],
        "pnpm": ["pnpm", "install"],
    }[pm]
    rel = os.path.relpath(project_dir) or "."
    print_info(f"Running '{' '.join(cmd)}' in {rel} ...")
    try:
        result = subprocess.run(cmd, cwd=project_dir, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print_success(f"Lockfile regenerated in {rel}")
            return True
        else:
            print_error(f"Install failed in {rel}:\n{result.stderr.strip()}")
            return False
    except FileNotFoundError:
        print_error(f"'{pm}' not found — run '{' '.join(cmd)}' manually in {rel}")
        return False
    except subprocess.TimeoutExpired:
        print_error(f"Install timed out in {rel} — run '{' '.join(cmd)}' manually")
        return False


# ---------------------------------------------------------------------------
# Main audit orchestration
# ---------------------------------------------------------------------------

def audit_directory(target_dir, fix=False):
    findings = {"critical": [], "warning": [], "ok": [], "ioc": []}

    print_header(f"Axios Security Audit: {os.path.abspath(target_dir)}")
    print_info(f"Vulnerable versions : {', '.join(sorted(VULNERABLE_VERSIONS))}")
    print_info(f"Safe versions       : {', '.join(SAFE_VERSIONS.values())}")

    # --- Scan dependency files (skip node_modules) ---
    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d != "node_modules"]
        _print_progress(os.path.relpath(root, target_dir) or ".")
        for filename in files:
            filepath = os.path.join(root, filename)
            if filename == "package.json":
                audit_package_json(filepath, findings)
            elif filename == "package-lock.json":
                audit_package_lock(filepath, findings)
            elif filename == "yarn.lock":
                audit_yarn_lock(filepath, findings)
            elif filename == "pnpm-lock.yaml":
                audit_pnpm_lock(filepath, findings)
    _clear_progress()

    # --- IOC: filesystem malware artifacts ---
    ioc_files = scan_iocs()
    for path in ioc_files:
        findings["ioc"].append({"type": "fs_ioc", "detail": path})

    # --- IOC: plain-crypto-js in node_modules ---
    malicious_dirs = scan_plain_crypto_js(target_dir)
    for path in malicious_dirs:
        findings["ioc"].append({"type": "malicious_pkg", "detail": path})

    # --- Print findings ---
    if findings["ioc"]:
        print_header("CRITICAL: Indicators of Compromise detected!")
        for item in findings["ioc"]:
            if item["type"] == "fs_ioc":
                print_error(f"Malware artifact found: {item['detail']}")
            elif item["type"] == "malicious_pkg":
                print_error(f"Malicious package installed: {item['detail']}")
            else:
                print_error(f"Malicious package in lockfile: {item['detail']}")
        print_error("Your machine/runner is likely compromised. Rotate all credentials")
        print_error("immediately and report to infosec")

    if findings["critical"]:
        print_header("CRITICAL: Vulnerable axios versions found!")
        for item in findings["critical"]:
            safe = safe_version_for(item["version"]) or "a safe version"
            print_error(f"{item['rel']}  (axios@{item['version']} → downgrade to {safe})")

    if findings["warning"]:
        print_header("WARNING: Unpinned axios versions (could resolve to vulnerable)")
        for item in findings["warning"]:
            safe = safe_version_for(item["version"]) or "safe version"
            print_warning(f"{item['rel']}  ({item['version']} → pin to {safe})")

    if findings["ok"]:
        print_header("OK: Safe axios versions")
        for item in findings["ok"]:
            print_success(f"{item['rel']}  (axios@{item['version']})")

    if not findings["critical"] and not findings["warning"] and not findings["ok"]:
        print_header("No axios dependency found")
        print_info("This directory does not appear to use axios.")

    # --- Apply fixes ---
    if fix:
        # Collect package.json files to patch (direct vulnerable or unpinned)
        fixable: dict[str, list] = {}
        for item in findings["critical"]:
            if item["type"] == "vulnerable":
                fixable.setdefault(item["file"], []).append(item)
        for item in findings["warning"]:
            if item["type"] == "unpinned":
                fixable.setdefault(item["file"], []).append(item)

        install_dirs: set[str] = set()
        fixable_dirs: set[str] = set()

        if fixable:
            print_header("Auto-fixing package.json files...")
            for filepath, items in fixable.items():
                if fix_package_json(filepath, items):
                    d = os.path.dirname(filepath)
                    install_dirs.add(d)
                    fixable_dirs.add(d)

        # Transitive deps: lockfile has vulnerable version but package.json
        # has no direct axios entry → add overrides/resolutions to force the
        # safe version through the full dependency tree.
        lockfile_types = {"lockfile_vulnerable", "yarn_lock_vulnerable", "pnpm_lock_vulnerable"}
        transitive_handled: set[str] = set()
        for item in findings["critical"]:
            if item["type"] not in lockfile_types:
                continue
            pdir = os.path.abspath(item.get("project_dir", os.path.dirname(item["file"])))
            install_dirs.add(pdir)
            if pdir in fixable_dirs or pdir in transitive_handled:
                continue
            pkg_json = os.path.join(pdir, "package.json")
            if os.path.exists(pkg_json):
                target = safe_version_for(item["version"]) or "1.14.0"
                pm = detect_package_manager(pdir)
                if add_overrides_to_package_json(pkg_json, target, pm):
                    transitive_handled.add(pdir)

        if install_dirs:
            print_header("Regenerating lockfiles...")
            for d in sorted(install_dirs):
                run_install(d)
        elif not fixable:
            print_info("Nothing to fix.")

    # --- Summary ---
    print_header("Summary")
    n_ioc  = len(findings["ioc"])
    n_crit = len(findings["critical"])
    n_warn = len(findings["warning"])
    n_ok   = len(findings["ok"])

    if n_ioc:
        print_error(f"{n_ioc} indicator(s) of compromise found on this machine!")
        print_error("Stop work. Rotate all credentials. Contact infosec NOW.")

    if n_crit:
        print_error(f"{n_crit} vulnerable axios instance(s) found.")
        if fix:
            print_success("Versions patched and lockfiles regenerated.")
        else:
            print_error("Run with --fix to patch versions and regenerate lockfiles.")
        if not n_ioc:
            print_error("If this version was ever installed, treat machine as compromised.")
    elif n_warn:
        if fix:
            print_success(f"{n_warn} unpinned version(s) pinned and lockfiles regenerated.")
        else:
            print_warning(f"{n_warn} unpinned version(s). Run with --fix to auto-pin.")
    elif n_ok:
        print_success(f"All {n_ok} axios instance(s) are using safe versions.")
    else:
        print_info("No axios dependencies found.")

    print()
    return n_ioc == 0 and n_crit == 0


def main():
    parser = argparse.ArgumentParser(
        description="Audit directory for vulnerable axios versions (1.14.1 and 0.30.4)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s .                    Audit current directory
  %(prog)s /path/to/project     Audit specific project
  %(prog)s . --fix              Patch versions and regenerate lockfiles
        """,
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Directory to audit (default: current directory)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Patch axios versions in package.json and regenerate lockfiles",
    )

    args = parser.parse_args()

    target_dir = os.path.abspath(args.directory)
    if not os.path.isdir(target_dir):
        print(f"{RED}Error: '{target_dir}' is not a valid directory{NC}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0 if audit_directory(target_dir, fix=args.fix) else 1)


if __name__ == "__main__":
    main()
