"""``dockercmd`` - interactive front-end for common docker operations."""

from __future__ import annotations

import argparse
import subprocess
import sys

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import CommandNotFoundError, require
from toolscripts.core.ui_curses import select_many, select_one

log = get_logger(__name__)

_MENU = [
    "List all containers",
    "Stop container(s)",
    "Remove container(s)",
    "List all images",
    "Remove image(s)",
    "Show logs of a container",
    "Inspect a network",
    "Exec bash into a container",
    "Show docker disk usage",
    "System prune (-a)",
    "Volume prune",
]


def _run(cmd: list[str]) -> None:
    log.info("executing: %s", " ".join(cmd))
    subprocess.run(cmd, check=False)


def _pick_containers(
    title: str, *, running_only: bool = False, multi: bool = True
) -> list[tuple[str, str]]:
    """Curses picker; returns list of (id, name) for selected containers."""
    flags = [] if running_only else ["-a"]
    try:
        out = subprocess.check_output(
            ["docker", "container", "ls", *flags, "--format", "{{.ID}}\t{{.Names}}\t{{.Status}}"],
            text=True,
        )
    except subprocess.CalledProcessError:
        return []
    rows = [r.strip() for r in out.splitlines() if r.strip()]
    if not rows:
        log.warning("no containers found")
        return []
    ids, names, display = [], [], []
    for row in rows:
        parts = row.split("\t")
        cid = parts[0][:12]
        name = parts[1] if len(parts) > 1 else cid
        status = parts[2] if len(parts) > 2 else ""
        ids.append(cid)
        names.append(name)
        display.append(f"{name}  [{cid}]  {status}")
    if multi:
        chosen = select_many(title, display)
        if chosen is None:
            return []
        return [(ids[i], names[i]) for i in chosen]
    chosen = select_one(title, display)
    return [(ids[chosen], names[chosen])] if chosen is not None else []


def _pick_images(title: str) -> list[tuple[str, str]]:
    """Curses multi-select; returns list of (id, repo_tag) for selected images."""
    try:
        out = subprocess.check_output(
            ["docker", "image", "ls", "--format", "{{.ID}}\t{{.Repository}}:{{.Tag}}\t{{.Size}}"],
            text=True,
        )
    except subprocess.CalledProcessError:
        return []
    rows = [r.strip() for r in out.splitlines() if r.strip()]
    if not rows:
        log.warning("no images found")
        return []
    ids, names, display = [], [], []
    for row in rows:
        parts = row.split("\t")
        iid = parts[0][:12]
        repo_tag = parts[1] if len(parts) > 1 else iid
        size = parts[2] if len(parts) > 2 else ""
        ids.append(iid)
        names.append(repo_tag)
        display.append(f"{repo_tag}  [{iid}]  {size}")
    chosen = select_many(title, display)
    if chosen is None:
        return []
    return [(ids[i], names[i]) for i in chosen]


def _pick_network(title: str) -> str | None:
    """Curses single-select; returns selected network name or None."""
    try:
        out = subprocess.check_output(
            ["docker", "network", "ls", "--format", "{{.Name}}\t{{.Driver}}\t{{.Scope}}"],
            text=True,
        )
    except subprocess.CalledProcessError:
        return None
    rows = [r.strip() for r in out.splitlines() if r.strip()]
    if not rows:
        log.warning("no networks found")
        return None
    names, display = [], []
    for row in rows:
        parts = row.split("\t")
        name = parts[0]
        driver = parts[1] if len(parts) > 1 else ""
        scope = parts[2] if len(parts) > 2 else ""
        names.append(name)
        display.append(f"{name}  [{driver}]  {scope}")
    chosen = select_one(title, display)
    return names[chosen] if chosen is not None else None


def _dispatch(idx: int) -> None:
    if idx == 0:
        _run(["docker", "container", "ls", "-a"])
    elif idx == 1:
        selected = _pick_containers("Select containers to stop:", running_only=True)
        if selected:
            ids, _ = zip(*selected, strict=False)
            _run(["docker", "container", "stop", *ids])
    elif idx == 2:
        selected = _pick_containers("Select containers to remove:")
        if selected:
            ids, _ = zip(*selected, strict=False)
            _run(["docker", "container", "rm", "-f", *ids])
    elif idx == 3:
        _run(["docker", "image", "ls"])
    elif idx == 4:
        selected = _pick_images("Select images to remove:")
        if selected:
            ids, _ = zip(*selected, strict=False)
            _run(["docker", "image", "rm", *ids])
    elif idx == 5:
        selected = _pick_containers("Select container for logs:", multi=False)
        if selected:
            _run(["docker", "logs", "--tail", "100", selected[0][0]])
    elif idx == 6:
        net = _pick_network("Select network to inspect:")
        if net:
            _run(["docker", "network", "inspect", net])
    elif idx == 7:
        selected = _pick_containers(
            "Select container to exec bash into:", running_only=True, multi=False
        )
        if selected:
            _run(["docker", "container", "exec", "-it", selected[0][0], "bash"])
    elif idx == 8:
        _run(["docker", "system", "df", "-v"])
    elif idx == 9:
        _run(["docker", "system", "prune", "-a"])
    elif idx == 10:
        _run(["docker", "volume", "prune"])


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="dockercmd",
        description="Interactive front-end for common docker operations.",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        require("docker")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)

    while True:
        idx = select_one("dockercmd — Select a Docker operation:", _MENU)
        if idx is None:
            return
        print()
        _dispatch(idx)
        print("-" * 28)
        try:
            input("Press Enter to return to menu…")
        except (EOFError, KeyboardInterrupt):
            print()
            return


if __name__ == "__main__":
    main()
