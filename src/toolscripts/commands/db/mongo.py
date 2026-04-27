"""``mongo-tool`` - dump / restore a mongodb to/from a zip archive.

Migrated from ``db/mongo/run.py``. Reads a config from
``~/.config/toolscripts/mongo.json`` (or the legacy bundled config when the
package is run from a checkout).
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import CommandNotFoundError, require, run

log = get_logger(__name__)

CONFIG_DIR = Path.home() / ".config" / "toolscripts"
CONFIG_FILE = CONFIG_DIR / "mongo.json"
DUMP_DIR = CONFIG_DIR / "mongo-dump"


def _load_config() -> dict:
    if CONFIG_FILE.is_file():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            log.error("could not read %s: %s", CONFIG_FILE, exc)
            sys.exit(1)
    log.warning("config file not found at %s", CONFIG_FILE)
    log.info(
        "create one with: {\"port\":27017,\"host\":\"127.0.0.1\","
        "\"username\":\"...\",\"password\":\"...\",\"dbname\":\"...\","
        "\"recordsCount\":10}"
    )
    sys.exit(1)


def _ensure_tools() -> None:
    for tool in ("mongodump", "mongorestore", "zip", "unzip"):
        try:
            require(tool)
        except CommandNotFoundError as exc:
            log.error("%s", exc)
            sys.exit(1)


def _dump(config: dict) -> None:
    _ensure_tools()
    DUMP_DIR.mkdir(parents=True, exist_ok=True)
    target = DUMP_DIR / config["dbname"]
    if target.is_dir():
        run(["rm", "-rf", str(target)])
    run(
        [
            "mongodump",
            "--forceTableScan",
            "--host",
            f"{config['host']}:{config['port']}",
            "--authenticationDatabase",
            config["dbname"],
            "-u",
            config["username"],
            "-p",
            config["password"],
            "-d",
            config["dbname"],
            "-o",
            str(DUMP_DIR),
        ]
    )

    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    archive = DUMP_DIR / f"{config['dbname']}_{timestamp}.zip"
    run(["zip", "-r", str(archive), config["dbname"]], cwd=str(DUMP_DIR))
    run(["rm", "-rf", str(target)])

    archives = sorted(p for p in DUMP_DIR.iterdir() if p.is_file() and p.suffix == ".zip")
    keep = config.get("recordsCount", 10)
    if len(archives) > keep:
        for old in archives[: len(archives) - keep]:
            log.info("rotating out old dump: %s", old.name)
            old.unlink(missing_ok=True)
    log.success("created %s", archive)


def _list_archives() -> list[Path]:
    if not DUMP_DIR.is_dir():
        return []
    return sorted(
        (p for p in DUMP_DIR.iterdir() if p.is_file() and p.suffix == ".zip"),
        reverse=True,
    )


def _select_archive() -> Path | None:
    archives = _list_archives()
    if not archives:
        log.warning("no archives in %s", DUMP_DIR)
        return None
    print("Select archive:")
    for i, p in enumerate(archives, 1):
        print(f"  {i}. {p.name}")
    try:
        raw = input(f"Choice (1-{len(archives)}): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    if not raw.isdigit():
        return None
    idx = int(raw) - 1
    if 0 <= idx < len(archives):
        return archives[idx]
    return None


def _restore(config: dict, *, full: bool) -> None:
    _ensure_tools()
    archive = _select_archive()
    if archive is None:
        return
    DUMP_DIR.mkdir(parents=True, exist_ok=True)
    extracted = DUMP_DIR / config["dbname"]
    if extracted.is_dir():
        run(["rm", "-rf", str(extracted)])
    run(["unzip", str(archive)], cwd=str(DUMP_DIR))

    cmd = [
        "mongorestore",
        "--drop",
        "--host",
        f"{config['host']}:{config['port']}",
        "-u",
        config["username"],
        "-p",
        config["password"],
        "-d",
        config["dbname"],
    ]

    if full:
        cmd.append(str(extracted))
    else:
        try:
            class_name = input("Collection name to restore: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not class_name:
            return
        cmd.extend(["-c", class_name, str(extracted / f"{class_name}.bson")])

    run(cmd)
    run(["rm", "-rf", str(extracted)])
    log.success("restore complete")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mongo-tool",
        description="Dump / restore a mongo database to/from a zip archive.",
    )
    parser.add_argument(
        "--mode",
        choices=("dump", "restore-collection", "restore-all"),
        help="non-interactive mode",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    config = _load_config()

    if args.mode == "dump":
        _dump(config)
        return
    if args.mode == "restore-collection":
        _restore(config, full=False)
        return
    if args.mode == "restore-all":
        _restore(config, full=True)
        return

    print("Select action:")
    print("  1) dump database")
    print("  2) restore single collection")
    print("  3) restore whole database")
    print("  0) quit")
    try:
        choice = input("Choice: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    if choice == "1":
        _dump(config)
    elif choice == "2":
        _restore(config, full=False)
    elif choice == "3":
        _restore(config, full=True)


if __name__ == "__main__":
    main()
