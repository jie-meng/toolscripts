"""``npm-gsync`` - sync npm global packages across node versions.

Run with no subcommand (or ``npm-gsync wizard``) to open an interactive
curses flow that picks versions and packages for you.

Requires the ``fnm`` binary on PATH. Lists are read offline from each
version's ``lib/node_modules`` directory; copy/move/clean operations
run through ``fnm exec --using <ver> npm ...`` so they touch exactly the
requested node version.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.npm_global import read_global_packages
from toolscripts.core.prompts import yes_no
from toolscripts.core.shell import CommandNotFoundError, require, run

log = get_logger(__name__)

_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


# --- discovery -----------------------------------------------------------


def _versions_dir() -> Path:
    """Directory holding fnm's ``node-versions/`` tree."""
    env_dir = os.environ.get("FNM_DIR")
    if env_dir:
        return Path(env_dir)
    # fnm's default when FNM_DIR is unset (XDG data home on macOS/Linux).
    return Path.home() / ".local" / "share" / "fnm"


def _version_key(name: str) -> tuple[int, int, int]:
    match = _VERSION_RE.match(name)
    assert match is not None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def list_versions() -> list[str]:
    """Installed fnm node versions (``vX.Y.Z``), newest first."""
    versions_dir = _versions_dir() / "node-versions"
    if not versions_dir.is_dir():
        return []
    names = [e.name for e in versions_dir.iterdir() if e.is_dir() and _VERSION_RE.match(e.name)]
    return sorted(names, key=_version_key, reverse=True)


def resolve_version(installed: list[str], raw: str) -> str:
    """Map a fuzzy version (``22``, ``22.18``, ``v22.18.0``) to an installed one."""
    target = raw[1:] if raw.startswith("v") else raw
    matches = [ver for ver in installed if ver[1:] == target or ver[1:].startswith(f"{target}.")]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ValueError(f"node version {raw!r} is not installed")
    raise ValueError(f"node version {raw!r} is ambiguous: {', '.join(matches)}")


def packages_of(version: str) -> dict[str, str]:
    """name -> version for the global packages installed in ``version``."""
    modules = _versions_dir() / "node-versions" / version / "installation" / "lib" / "node_modules"
    return read_global_packages(modules)


# --- plans & diffs -------------------------------------------------------


def diff_packages(
    a: dict[str, str], b: dict[str, str]
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Return (only_in_a, only_in_b, version_mismatch); mismatch is pkg -> (a_ver, b_ver)."""
    only_a = {name: ver for name, ver in a.items() if name not in b}
    only_b = {name: ver for name, ver in b.items() if name not in a}
    mismatch = {name: (a[name], b[name]) for name in a if name in b and a[name] != b[name]}
    return only_a, only_b, mismatch


def build_sync_plan(
    source: dict[str, str],
    target: dict[str, str],
    selected: list[str] | None,
    *,
    force: bool,
) -> list[tuple[str, str]]:
    """Packages to install into target as ``(name, version)``.

    ``selected=None`` means every package in ``source``. Versions that
    already match the target are skipped unless ``force``.
    """
    names = selected if selected is not None else sorted(source)
    plan: list[tuple[str, str]] = []
    for name in names:
        version = source.get(name)
        if version is None:
            raise ValueError(f"{name!r} is not installed in the source version")
        if not force and target.get(name) == version:
            continue
        plan.append((name, version))
    return plan


# --- execution -----------------------------------------------------------


def _select_names(requested: list[str], available: dict[str, str], where: str) -> list[str]:
    """Deduplicate ``requested``, keeping only names installed in ``available``."""
    names: list[str] = []
    for name in requested:
        if name in available:
            if name not in names:
                names.append(name)
        else:
            log.warning("%s is not installed in the %s; skipping", name, where)
    return names


def _empty_scope_dirs(version: str) -> list[Path]:
    """Empty ``@scope`` dirs left in a version's global node_modules."""
    modules = _versions_dir() / "node-versions" / version / "installation" / "lib" / "node_modules"
    if not modules.is_dir():
        return []
    return [
        d
        for d in modules.iterdir()
        if d.is_dir() and d.name.startswith("@") and not any(d.iterdir())
    ]


def _run_installs(version: str, plan: list[tuple[str, str]]) -> int:
    failures: list[str] = []
    for name, pkg_version in plan:
        log.info("installing %s@%s into %s ...", name, pkg_version, version)
        result = run(
            [
                "fnm",
                "exec",
                "--using",
                version,
                "npm",
                "install",
                "-g",
                "--no-fund",
                "--no-audit",
                f"{name}@{pkg_version}",
            ],
            check=False,
        )
        if result.returncode != 0:
            failures.append(name)
    if failures:
        log.error("failed to install: %s", ", ".join(failures))
        return 1
    log.success("installed %d package(s) into %s", len(plan), version)
    return 0


def _run_uninstalls(version: str, names: list[str]) -> int:
    if not names:
        return 0
    log.info("uninstalling from %s: %s", version, ", ".join(names))
    result = run(["fnm", "exec", "--using", version, "npm", "uninstall", "-g", *names], check=False)
    if result.returncode != 0:
        log.error("failed to uninstall from %s", version)
        return 1
    log.success("removed %d package(s) from %s", len(names), version)
    return 0


# --- subcommands ---------------------------------------------------------


def _cmd_ls(versions: list[str]) -> int:
    for i, version in enumerate(versions):
        if i:
            print()
        packages = packages_of(version)
        print(f"{version} ({len(packages)} packages)")
        for name, pkg_version in sorted(packages.items()):
            print(f"  {name}@{pkg_version}")
    return 0


def _cmd_diff(from_version: str, to_version: str) -> int:
    only_a, only_b, mismatch = diff_packages(packages_of(from_version), packages_of(to_version))
    print(f"{from_version} -> {to_version}")
    print(f"\nonly in {from_version} ({len(only_a)}):")
    for name, version in sorted(only_a.items()):
        print(f"  {name}@{version}")
    print(f"\nonly in {to_version} ({len(only_b)}):")
    for name, version in sorted(only_b.items()):
        print(f"  {name}@{version}")
    print(f"\nversion differs ({len(mismatch)}):")
    for name, (ver_a, ver_b) in sorted(mismatch.items()):
        print(f"  {name}: {from_version}={ver_a} -> {to_version}={ver_b}")
    return 0


def _cmd_sync(args: argparse.Namespace, installed: list[str]) -> int:
    from_version = resolve_version(installed, args.from_version)
    to_version = resolve_version(installed, args.to_version)
    if from_version == to_version:
        log.error("source and target are the same version (%s)", from_version)
        return 1
    source = packages_of(from_version)
    selected: list[str] | None = args.packages or None
    if selected is not None:
        selected = _select_names(selected, source, "source")
    plan = build_sync_plan(source, packages_of(to_version), selected, force=args.force)
    if not plan:
        log.info("nothing to sync")
        return 0
    if args.dry_run:
        print(f"would install {len(plan)} package(s) into {to_version}:")
        for name, version in plan:
            print(f"  {name}@{version}")
        return 0
    if not args.yes and not yes_no(f"Install {len(plan)} package(s) into {to_version} this way?"):
        log.info("aborted")
        return 0
    return _run_installs(to_version, plan)


def _cmd_move(args: argparse.Namespace, installed: list[str]) -> int:
    from_version = resolve_version(installed, args.from_version)
    to_version = resolve_version(installed, args.to_version)
    if from_version == to_version:
        log.error("source and target are the same version (%s)", from_version)
        return 1
    source = packages_of(from_version)
    selected: list[str] | None = args.packages or None
    if selected is not None:
        selected = _select_names(selected, source, "source")
    plan = build_sync_plan(source, packages_of(to_version), selected, force=args.force)
    to_remove = selected if selected is not None else sorted(source)
    if not plan and not to_remove:
        log.info("nothing to move")
        return 0
    if args.dry_run:
        if plan:
            print(f"would install {len(plan)} package(s) into {to_version}:")
            for name, version in plan:
                print(f"  {name}@{version}")
        if to_remove:
            print(f"would uninstall {len(to_remove)} package(s) from {from_version}:")
            for name in to_remove:
                print(f"  {name}")
        return 0
    if not args.yes and not yes_no(
        f"Install {len(plan)} package(s) into {to_version}, then remove {len(to_remove)} from {from_version}?"
    ):
        log.info("aborted")
        return 0
    if plan:
        code = _run_installs(to_version, plan)
        if code != 0:
            return code  # keep the source copy intact when installs fail
    return _run_uninstalls(from_version, to_remove)


def _cmd_clean(args: argparse.Namespace, installed: list[str]) -> int:
    version = resolve_version(installed, args.version)
    if args.packages and args.all:
        log.error("pass either package names or --all, not both")
        return 1
    current = packages_of(version)
    if args.packages:
        names = _select_names(args.packages, current, "version")
    elif args.all:
        names = sorted(current)
    else:
        log.error("specify package names or --all (see npm-gsync clean --help)")
        return 1
    empty_dirs = _empty_scope_dirs(version) if args.prune else []
    if not names and not empty_dirs:
        log.info("nothing to clean")
        return 0
    if args.dry_run:
        if names:
            print(f"would uninstall from {version}: {', '.join(names)}")
        if empty_dirs:
            print("would remove empty dirs: " + ", ".join(str(d) for d in empty_dirs))
        return 0
    if not args.yes and not yes_no(f"Remove {len(names)} package(s) from {version}?"):
        log.info("aborted")
        return 0
    code = _run_uninstalls(version, names)
    if code != 0:
        return code
    for directory in empty_dirs:
        try:
            directory.rmdir()
        except OSError as exc:
            log.warning("could not remove %s: %s", directory, exc)
        else:
            log.info("removed empty dir %s", directory)
    return 0


# --- interactive wizard --------------------------------------------------


def _pick_value(
    title: str,
    options: list[tuple[str, str]],
    *,
    default_index: int | None = None,
) -> str | None:
    """One-shot curses menu; returns the picked value or None on cancel."""
    from toolscripts.core.ui_curses import select_one

    idx = select_one(title, [label for _, label in options], default_index=default_index)
    if idx is None:
        return None
    return options[idx][0]


def _pick_packages(title: str, names: list[str]) -> list[str] | None:
    """Multi-select from ``names`` (all preselected); None means cancel, [] means nothing."""
    from toolscripts.core.ui_curses import select_many

    if not names:
        return []
    idxs = select_many(title, names, preselected=[True] * len(names))
    if idxs is None:
        return None
    return [names[i] for i in idxs]


def _version_options(
    installed: list[str],
    packages: dict[str, dict[str, str]],
    *,
    exclude: str | None = None,
) -> list[tuple[str, str]]:
    return [(ver, f"{ver} ({len(packages[ver])} packages)") for ver in installed if ver != exclude]


def _wizard_sync(installed: list[str], packages: dict[str, dict[str, str]], *, move: bool) -> None:
    """Pick source/target versions, then delegate the rest."""
    verb = "move" if move else "sync"
    source = _pick_value(f"{verb}: source node version", _version_options(installed, packages))
    if source is None:
        return
    target = _pick_value(
        f"{verb}: target node version",
        _version_options(installed, packages, exclude=source),
    )
    if target is None:
        return
    _wizard_sync_versions(source, target, packages, move=move)


def _wizard_sync_versions(
    source: str, target: str, packages: dict[str, dict[str, str]], *, move: bool
) -> None:
    from toolscripts.core.prompts import yes_no

    if not packages[source]:
        log.warning("no global packages installed in %s", source)
        return
    selected = _pick_packages(
        f"{'move' if move else 'sync'}: packages from {source}", sorted(packages[source])
    )
    if selected is None:
        return
    if not selected:
        log.warning("no packages selected")
        return
    plan = build_sync_plan(packages[source], packages[target], selected, force=False)
    matched = sorted(set(selected) - {name for name, _ in plan})
    if not plan:
        log.info("nothing to do - selected packages already match %s", target)
        return
    print(f"plan: install {len(plan)} package(s) into {target}:")
    for name, version in plan:
        print(f"  {name}@{version}")
    if matched:
        log.info("skipping %d already matching: %s", len(matched), ", ".join(matched))
    if not yes_no(f"Install {len(plan)} package(s) into {target} as shown?"):
        return
    if _run_installs(target, plan) != 0:
        return
    if not move:
        return
    if not yes_no(f"Also remove {len(selected)} package(s) from {source}?"):
        return
    if _run_uninstalls(source, selected) != 0:
        return
    if yes_no(f"Delete node version {source} (fnm uninstall)?"):
        run(["fnm", "uninstall", source], check=False)


def _wizard_clean(installed: list[str], packages: dict[str, dict[str, str]]) -> None:
    from toolscripts.core.prompts import yes_no

    version = _pick_value(
        "clean: remove packages from node version", _version_options(installed, packages)
    )
    if version is None:
        return
    current = packages[version]
    if not current:
        log.warning("no global packages installed in %s", version)
        return
    selected = _pick_packages(f"clean: remove packages from {version}", sorted(current))
    if selected is None:
        return
    if not selected:
        log.warning("no packages selected")
        return
    if not yes_no(f"Remove {len(selected)} package(s) from {version}?"):
        return
    _run_uninstalls(version, selected)


# --- entry point ---------------------------------------------------------


def _wizard_diff(installed: list[str], packages: dict[str, dict[str, str]]) -> None:
    first = _pick_value("diff: first node version", _version_options(installed, packages))
    if first is None:
        return
    second = _pick_value(
        "diff: second node version",
        _version_options(installed, packages, exclude=first),
    )
    if second is None:
        return
    print()
    _cmd_diff(first, second)
    try:
        input("\nPress Enter to return to the menu...")
    except (EOFError, KeyboardInterrupt):
        return


def _wizard_uninstall(installed: list[str], packages: dict[str, dict[str, str]]) -> None:
    from toolscripts.core.prompts import yes_no

    version = _pick_value(
        "uninstall: node version to remove", _version_options(installed, packages)
    )
    if version is None:
        return
    if not yes_no(f"Delete node version {version} with 'fnm uninstall'?"):
        return
    result = run(["fnm", "uninstall", version], check=False)
    if result.returncode != 0:
        log.error("fnm uninstall failed for %s", version)


def _run_wizard() -> int:
    """Interactive curses flow: pick operations, versions and packages."""
    if not sys.stdin.isatty():
        log.error("interactive wizard requires a TTY (run it in a terminal)")
        return 1
    try:
        import curses  # noqa: F401
    except ImportError:
        log.error("curses is not available on this Python build")
        return 1

    menu = [
        ("sync", "sync: copy global packages into another node version"),
        ("move", "move: copy to another version, then delete from the source"),
        ("clean", "clean: remove global packages from a node version"),
        ("diff", "diff: compare global packages of two node versions"),
        ("uninstall", "uninstall: remove an entire node version"),
        ("quit", "quit"),
    ]
    while True:
        installed = list_versions()
        if not installed:
            log.warning("no fnm node versions are installed")
            return 0
        packages = {ver: packages_of(ver) for ver in installed}
        choice = _pick_value(f"npm-gsync ({len(installed)} node versions)", menu)
        if choice is None or choice == "quit":
            return 0
        if choice == "sync":
            _wizard_sync(installed, packages, move=False)
        elif choice == "move":
            _wizard_sync(installed, packages, move=True)
        elif choice == "clean":
            _wizard_clean(installed, packages)
        elif choice == "diff":
            _wizard_diff(installed, packages)
        elif choice == "uninstall":
            _wizard_uninstall(installed, packages)


# --- entry point ---------------------------------------------------------


def _add_pair_subparser(sub: argparse._SubParsersAction, name: str, desc: str) -> None:
    p = sub.add_parser(name, help=desc)
    p.add_argument(
        "--from", dest="from_version", metavar="FROM", required=True, help="source node version"
    )
    p.add_argument(
        "--to", dest="to_version", metavar="TO", required=True, help="target node version"
    )
    p.add_argument("packages", nargs="*", metavar="PKG", help="packages to sync (default: all)")
    p.add_argument("-y", "--yes", action="store_true", help="skip confirmation prompts")
    p.add_argument("--force", action="store_true", help="also reinstall same-version packages")
    p.add_argument("--dry-run", action="store_true", help="preview only")
    add_logging_flags(p)


def _dispatch(args: argparse.Namespace) -> int:
    installed = list_versions()
    if not installed:
        log.error("no fnm node versions found under %s", _versions_dir() / "node-versions")
        return 1
    if not args.command or args.command == "wizard":
        return _run_wizard()
    if args.command == "ls":
        return _cmd_ls(installed)
    if args.command == "diff":
        return _cmd_diff(
            resolve_version(installed, args.from_version),
            resolve_version(installed, args.to_version),
        )
    if args.command == "sync":
        return _cmd_sync(args, installed)
    if args.command == "move":
        return _cmd_move(args, installed)
    if args.command == "clean":
        return _cmd_clean(args, installed)
    raise AssertionError(f"unhandled command: {args.command}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="npm-gsync",
        description="Manage npm global packages across fnm node versions: ls, diff, sync, move, clean.",
    )
    sub = parser.add_subparsers(dest="command")

    p_wizard = sub.add_parser(
        "wizard", help="interactive curses flow (default when run with no subcommand)"
    )
    add_logging_flags(p_wizard)

    p_ls = sub.add_parser("ls", help="list global packages of every installed node version")
    add_logging_flags(p_ls)

    p_diff = sub.add_parser("diff", help="compare global packages of two versions")
    p_diff.add_argument("from_version", metavar="FROM", help="source node version")
    p_diff.add_argument("to_version", metavar="TO", help="target node version")
    add_logging_flags(p_diff)

    _add_pair_subparser(sub, "sync", "copy FROM's global packages into TO (same versions)")
    _add_pair_subparser(sub, "move", "copy FROM's packages into TO, then remove them from FROM")

    p_clean = sub.add_parser("clean", help="remove global packages from a version")
    p_clean.add_argument("version", metavar="VERSION", help="node version to clean")
    p_clean.add_argument("packages", nargs="*", metavar="PKG", help="packages to remove")
    p_clean.add_argument(
        "--all", action="store_true", help="remove every non-bundled global package"
    )
    p_clean.add_argument(
        "--prune", action="store_true", help="also remove empty @scope directories"
    )
    p_clean.add_argument("-y", "--yes", action="store_true", help="skip confirmation prompts")
    p_clean.add_argument("--dry-run", action="store_true", help="preview only")
    add_logging_flags(p_clean)

    args = parser.parse_args()
    configure_from_args(args)

    try:
        require("fnm")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)

    try:
        sys.exit(_dispatch(args))
    except ValueError as exc:
        log.error("%s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
