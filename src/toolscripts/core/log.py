"""Unified colored logger for toolscripts.

Quick start::

    from toolscripts.core.log import get_logger

    log = get_logger(__name__)
    log.debug("connecting...")
    log.info("connected")
    log.success("done")        # custom level (between INFO and WARNING)
    log.warning("retrying")
    log.error("oh no")

Verbosity::

    # via env
    TOOLSCRIPTS_LOG_LEVEL=DEBUG mycmd

    # via argparse helpers
    parser = argparse.ArgumentParser()
    add_logging_flags(parser)            # adds -v / -q
    args = parser.parse_args()
    configure_from_args(args)            # apply level

Default level is INFO. Output goes to stderr so stdout stays clean for piping.
ANSI colors are auto-disabled when stderr is not a TTY (or NO_COLOR=1).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import cast

from toolscripts.core import colors

SUCCESS = 25
logging.addLevelName(SUCCESS, "SUCCESS")

_LEVEL_COLORS: dict[int, str] = {
    logging.DEBUG: colors.GREY,
    logging.INFO: colors.BLUE,
    SUCCESS: colors.GREEN,
    logging.WARNING: colors.YELLOW,
    logging.ERROR: colors.RED,
    logging.CRITICAL: colors.RED,
}

_LEVEL_NAMES: dict[int, str] = {
    logging.DEBUG: "DEBUG",
    logging.INFO: "INFO",
    SUCCESS: "OK",
    logging.WARNING: "WARN",
    logging.ERROR: "ERROR",
    logging.CRITICAL: "CRIT",
}


class ToolLogger(logging.Logger):
    """Logger subclass exposing a ``success()`` convenience method."""

    def success(self, msg: object, *args: object, **kwargs: object) -> None:
        if self.isEnabledFor(SUCCESS):
            self._log(SUCCESS, msg, args, **kwargs)  # type: ignore[arg-type]


logging.setLoggerClass(ToolLogger)


class _ColorFormatter(logging.Formatter):
    """Format records like ``LEVEL  logger.name  message`` with ANSI colors."""

    def __init__(self, *, with_time: bool, use_color: bool) -> None:
        super().__init__()
        self.with_time = with_time
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        level_name = _LEVEL_NAMES.get(record.levelno, record.levelname)
        level_str = f"{level_name:<5}"
        name = record.name
        if name.startswith("toolscripts."):
            name = name[len("toolscripts.") :]
        msg = record.getMessage()

        if self.use_color:
            color = _LEVEL_COLORS.get(record.levelno, colors.WHITE)
            bold = record.levelno >= logging.CRITICAL
            level_str = colors.colored(level_str, color, bold=bold)
            name = colors.colored(name, colors.GREY)

        prefix = ""
        if self.with_time:
            ts = self.formatTime(record, "%H:%M:%S")
            prefix = f"[{colors.colored(ts, colors.GREY) if self.use_color else ts}] "

        line = f"{prefix}{level_str}  {name}  {msg}"
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


_HANDLER_TAG = "_toolscripts_handler"
_DEFAULT_LEVEL_ENV = "TOOLSCRIPTS_LOG_LEVEL"


def _resolve_level(value: str | int | None) -> int:
    if value is None:
        return logging.INFO
    if isinstance(value, int):
        return value
    name = value.strip().upper()
    if name in {"SUCCESS", "OK"}:
        return SUCCESS
    return logging.getLevelName(name) if name else logging.INFO  # type: ignore[return-value]


def _ensure_handler() -> logging.Handler:
    root = logging.getLogger("toolscripts")
    for h in root.handlers:
        if getattr(h, _HANDLER_TAG, False):
            return h

    handler = logging.StreamHandler(stream=sys.stderr)
    setattr(handler, _HANDLER_TAG, True)
    use_color = colors.colors_enabled(sys.stderr)
    with_time = bool(os.environ.get("TOOLSCRIPTS_LOG_TIME"))
    handler.setFormatter(_ColorFormatter(with_time=with_time, use_color=use_color))
    root.addHandler(handler)
    root.propagate = False

    env_level = os.environ.get(_DEFAULT_LEVEL_ENV)
    root.setLevel(_resolve_level(env_level))
    return handler


def get_logger(name: str | None = None) -> ToolLogger:
    """Return a logger under the ``toolscripts`` namespace.

    ``name`` may be ``__name__`` (recommended) or any short tag. The
    ``toolscripts.`` prefix is stripped on output to keep lines tidy.
    """
    _ensure_handler()
    if not name or name == "__main__":
        full = "toolscripts"
    elif name.startswith("toolscripts"):
        full = name
    else:
        full = f"toolscripts.{name}"
    return cast(ToolLogger, logging.getLogger(full))


def set_level(level: str | int) -> None:
    """Set the root toolscripts logger level."""
    _ensure_handler()
    logging.getLogger("toolscripts").setLevel(_resolve_level(level))


def add_logging_flags(parser: argparse.ArgumentParser) -> None:
    """Add ``-v/--verbose`` and ``-q/--quiet`` to an argparse parser."""
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-v", "--verbose", action="store_true", help="enable debug logging"
    )
    group.add_argument(
        "-q", "--quiet", action="store_true", help="only show warnings and errors"
    )


def configure_from_args(args: argparse.Namespace) -> None:
    """Apply ``-v``/``-q`` from a parsed argparse namespace."""
    if getattr(args, "verbose", False):
        set_level(logging.DEBUG)
    elif getattr(args, "quiet", False):
        set_level(logging.WARNING)
