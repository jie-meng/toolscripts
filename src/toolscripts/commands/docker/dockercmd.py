"""``dockercmd`` - interactive browser for common docker operations."""

from __future__ import annotations

import argparse
import contextlib
import subprocess
import sys
from dataclasses import dataclass

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger
from toolscripts.core.shell import CommandNotFoundError, require
from toolscripts.core.ui_curses import select_many, select_one

log = get_logger(__name__)


@dataclass
class DockerCommand:
    name: str
    command: str
    description: str
    examples: list[str]


_DOCKER_COMMANDS: list[DockerCommand] = [
    DockerCommand(
        name="List containers",
        command="docker container ls -a",
        description="Run anywhere. Lists all containers — both running and stopped.",
        examples=["docker container ls -a", "docker ps -a"],
    ),
    DockerCommand(
        name="Stop container(s)",
        command="docker container stop <ID>...",
        description="Run anywhere. Stops one or more running containers. "
        "A picker will show all running containers to choose from.",
        examples=["docker container stop <id>", "docker stop myapp db"],
    ),
    DockerCommand(
        name="Remove container(s)",
        command="docker container rm -f <ID>...",
        description="Run anywhere. Force-removes containers (running or stopped). "
        "A picker will show all containers to choose from.",
        examples=["docker container rm -f <id>", "docker rm myapp"],
    ),
    DockerCommand(
        name="List images",
        command="docker image ls",
        description="Run anywhere. Lists all Docker images on the host.",
        examples=["docker image ls", "docker images"],
    ),
    DockerCommand(
        name="Remove image(s)",
        command="docker image rm <ID>...",
        description="Run anywhere. Removes one or more Docker images. "
        "A picker will show all local images to choose from.",
        examples=["docker image rm <id>", "docker rmi myimage:latest"],
    ),
    DockerCommand(
        name="Show logs",
        command="docker logs --tail 100 <ID>",
        description="Run anywhere. Shows the last 100 log lines of a container. "
        "A picker will let you choose the container.",
        examples=["docker logs --tail 100 <id>", "docker logs -f myapp"],
    ),
    DockerCommand(
        name="Inspect network",
        command="docker network inspect <NAME>",
        description="Run anywhere. Inspects a Docker network in detail. "
        "A picker will show all available networks.",
        examples=["docker network inspect bridge", "docker network ls"],
    ),
    DockerCommand(
        name="Exec bash",
        command="docker container exec -it <ID> bash",
        description="Run anywhere. Opens an interactive bash shell inside a running container. "
        "A picker will show all running containers.",
        examples=["docker exec -it myapp bash", "docker exec -it <id> sh"],
    ),
    DockerCommand(
        name="Disk usage",
        command="docker system df -v",
        description="Run anywhere. Shows Docker disk usage: images, containers, and volumes.",
        examples=["docker system df -v", "docker system df"],
    ),
    DockerCommand(
        name="System prune",
        command="docker system prune -a",
        description="Run anywhere. Removes ALL unused images, stopped containers, and "
        "unused networks. This cannot be undone.",
        examples=["docker system prune -a", "docker system prune"],
    ),
    DockerCommand(
        name="Volume prune",
        command="docker volume prune",
        description="Run anywhere. Removes all unused local volumes. This cannot be undone.",
        examples=["docker volume prune"],
    ),
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


# ---------------------------------------------------------------------------
# Curses UI
# ---------------------------------------------------------------------------


def _wrap(text: str, width: int) -> list[str]:
    if width <= 0:
        return []
    out: list[str] = []
    for raw_line in text.splitlines():
        if not raw_line.strip():
            out.append("")
            continue
        line = raw_line.rstrip()
        while len(line) > width:
            cut = line.rfind(" ", 0, width)
            if cut <= 0:
                cut = width
            out.append(line[:cut])
            line = line[cut:].lstrip()
        if line:
            out.append(line)
    return out


def _ensure_curses() -> None:
    try:
        import curses  # noqa: F401

        return
    except ImportError:
        if sys.platform == "win32":
            log.error("curses not available on Windows. Install with: pip install windows-curses")
        else:
            log.error("curses module not available on this Python build.")
        sys.exit(1)


def _run_curses(stdscr) -> None:
    import curses

    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_WHITE, -1)
    curses.init_pair(5, curses.COLOR_MAGENTA, -1)

    def cp(n: int) -> int:
        return curses.color_pair(n)

    commands = _DOCKER_COMMANDS
    cursor = 0
    top = 0

    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        preview_top = height - 13
        list_height = max(1, preview_top - 3)

        title = " dockercmd - docker command browser "
        stdscr.addstr(0, 0, title.center(width, " "), cp(1) | curses.A_BOLD)
        hint = "j/k or arrows: move  |  Enter: execute  |  q: quit"
        stdscr.addstr(1, 0, hint[:width], cp(3))
        stdscr.hline(2, 0, curses.ACS_HLINE, width)

        cmd = commands[cursor]

        visible_count = list_height
        if cursor < top:
            top = cursor
        elif cursor >= top + visible_count:
            top = cursor - visible_count + 1
        top = max(0, min(top, len(commands) - visible_count))

        for i in range(visible_count):
            idx = top + i
            if idx >= len(commands):
                break
            c = commands[idx]
            is_selected = idx == cursor
            marker = "▶" if is_selected else " "
            attr = curses.A_REVERSE if is_selected else 0
            color = cp(2) if is_selected else cp(4)
            name_text = f" {marker}  {c.name}"
            with contextlib.suppress(curses.error):
                stdscr.addstr(3 + i, 0, name_text[: width - 1], attr | color)

        stdscr.hline(preview_top - 1, 0, curses.ACS_HLINE, width)

        try:
            stdscr.addstr(preview_top, 2, "Command:", cp(5) | curses.A_BOLD)
            stdscr.addstr(preview_top + 1, 4, cmd.command[: width - 4], cp(2))
        except curses.error:
            pass

        desc_lines = _wrap(cmd.description, width - 4)
        try:
            stdscr.addstr(preview_top + 3, 2, "Description:", cp(5) | curses.A_BOLD)
            for li, line in enumerate(desc_lines[:3]):
                stdscr.addstr(preview_top + 4 + li, 4, line[: width - 4], cp(4))
        except curses.error:
            pass

        offset = preview_top + 4 + len(desc_lines[:3]) + 1
        with contextlib.suppress(curses.error):
            stdscr.addstr(offset, 2, "Examples:", cp(5) | curses.A_BOLD)
        for li, ex in enumerate(cmd.examples[:3]):
            with contextlib.suppress(curses.error):
                stdscr.addstr(offset + 1 + li, 4, f"  $ {ex}"[: width - 4], cp(1))

        with contextlib.suppress(curses.error):
            stdscr.addstr(height - 1, 0, f"  {cursor + 1}/{len(commands)}"[: width - 1], cp(3))

        stdscr.refresh()
        key = stdscr.getch()

        if key in (curses.KEY_UP, ord("k")):
            cursor = max(0, cursor - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            cursor = min(len(commands) - 1, cursor + 1)
        elif key == ord("g"):
            key2 = stdscr.getch()
            if key2 == ord("g"):
                cursor = 0
        elif key == ord("G"):
            cursor = len(commands) - 1
        elif key in (curses.KEY_ENTER, 10, 13):
            curses.endwin()
            try:
                _dispatch(cursor)
            except Exception as exc:
                print(f"Error: {exc}")
            input("\nPress Enter to return to the browser...")
            curses.noecho()
            curses.cbreak()
            stdscr.keypad(True)
            stdscr.clearok(True)
            stdscr.refresh()
        elif key in (ord("q"), 27):
            break


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="dockercmd",
        description="Interactive browser for common docker operations.",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    try:
        require("docker")
    except CommandNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)

    _ensure_curses()
    import curses

    curses.wrapper(_run_curses)


if __name__ == "__main__":
    main()
