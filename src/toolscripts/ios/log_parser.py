"""iOS log parsing utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# iOS log levels (similar to Apple's unified logging system)
LEVELS = ["Debug", "Info", "Default", "Error", "Fault"]

# Level mapping for filtering (lower index = more verbose)
_LEVEL_ORDER = {level: i for i, level in enumerate(LEVELS)}

# Colors for different log levels
_COLORS = {
    "Debug": 4,  # Blue
    "Info": 2,  # Green
    "Default": 6,  # Cyan
    "Error": 1,  # Red
    "Fault": 5,  # Magenta
}

# Patterns for iOS log formats
# Compact style: 2026-06-08 12:00:01.123 D MyApp[1234:5678] Message
_COMPACT_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\s+"
    r"([VDIWEF])\s+"
    r"(\S+?)\s*"
    r"(?:\[(\d+):(\d+)\])?\s*"
    r":\s*(.*)"
)

# /syslog style: Jun  8 12:00:01 iPhone MyApp[1234]: Message
_SYSLOG_RE = re.compile(
    r"(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+"
    r"(\S+)\s+"
    r"(\S+?)\s*"
    r"(?:\[(\d+)\])?\s*"
    r":\s*(.*)"
)

# idevicesyslog style: Jun  9 15:01:59.287776 audiomxd(MediaSafetyNet)[109] <Debug>: ...
_IDEVICYSYSLOG_RE = re.compile(
    r"(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\.\d+)\s+"
    r"(\S+?)\s*"
    r"(?:\[(\d+)\])?\s*"
    r"<(\w+)>\s*:\s*(.*)"
)

# Level mapping from single char to full name
_PRIORITY_TO_LEVEL = {
    "V": "Debug",
    "D": "Debug",
    "I": "Info",
    "W": "Default",
    "E": "Error",
    "F": "Fault",
}

# Full level names from idevicesyslog <Level> tags
_FULL_LEVEL_TO_LEVEL = {
    "Debug": "Debug",
    "Info": "Info",
    "Default": "Default",
    "Error": "Error",
    "Fault": "Fault",
    "Notice": "Info",
}


@dataclass
class LogEntry:
    """Represents a single iOS log entry."""

    timestamp: str
    level: str
    process: str
    pid: int = 0
    tid: int = 0
    message: str = ""
    raw: str = field(repr=False, default="")

    @property
    def level_index(self) -> int:
        """Return the numeric index of this entry's level for filtering."""
        return _LEVEL_ORDER.get(self.level, 2)  # Default to Info if unknown


def parse_log_line(line: str) -> LogEntry | None:
    """Parse a single iOS log line into a LogEntry.

    Supports both compact and syslog formats.
    Returns None if the line doesn't match any known format.
    """
    # Try compact format first
    m = _COMPACT_RE.match(line)
    if m:
        level_char = m.group(2)
        level = _PRIORITY_TO_LEVEL.get(level_char, "Default")
        return LogEntry(
            timestamp=m.group(1),
            level=level,
            process=m.group(3),
            pid=int(m.group(4)) if m.group(4) else 0,
            tid=int(m.group(5)) if m.group(5) else 0,
            message=m.group(6),
            raw=line,
        )

    # Try syslog format
    m = _SYSLOG_RE.match(line)
    if m:
        return LogEntry(
            timestamp=m.group(1),
            level="Default",  # syslog doesn't include level
            process=m.group(3),
            pid=int(m.group(4)) if m.group(4) else 0,
            message=m.group(5),
            raw=line,
        )

    # Try idevicesyslog format
    m = _IDEVICYSYSLOG_RE.match(line)
    if m:
        level = _FULL_LEVEL_TO_LEVEL.get(m.group(4), "Default")
        return LogEntry(
            timestamp=m.group(1),
            level=level,
            process=m.group(2),
            pid=int(m.group(3)) if m.group(3) else 0,
            message=m.group(5),
            raw=line,
        )

    return None


def passes_filter(
    entry: LogEntry,
    min_level: str = "Debug",
    filter_text: str = "",
) -> bool:
    """Check if a log entry passes the current filters."""
    # Check level filter
    entry_idx = entry.level_index
    min_idx = _LEVEL_ORDER.get(min_level, 0)
    if entry_idx < min_idx:
        return False

    # Check text filter
    if filter_text:
        f = filter_text.lower()
        if f not in entry.process.lower() and f not in entry.message.lower():
            return False

    return True
