"""``statcounter`` - draw a pie chart of OS-version coverage from a Statcounter CSV."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)

_VERSION_RE = re.compile(r"\d+\.\d+|\d+")


def _read_data(
    csv_path: Path, *, min_version: int, threshold: float
) -> tuple[dict[str, float], str]:
    versions: dict[str, float] = defaultdict(float)
    with csv_path.open("r", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        title = next(reader)[1]
        for row in reader:
            version_str, percentage_str = row
            major = _VERSION_RE.findall(version_str)
            major_version = (
                major[0].split(".")[0] if major else version_str
            )
            try:
                pct = float(percentage_str)
            except ValueError:
                continue
            if (
                pct < threshold
                or (major_version.isdigit() and int(major_version) < min_version)
            ):
                major_version = "Other"
            versions[major_version] += pct
    return versions, title


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="statcounter",
        description="Draw a pie chart of OS-version coverage from a Statcounter CSV.",
    )
    parser.add_argument("csv", help="path to the Statcounter CSV file")
    parser.add_argument(
        "--min-version", type=int, default=10, help="minimum major version (default: 10)"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.1,
        help="aggregate versions below this percent into 'Other' (default: 0.1)",
    )
    parser.add_argument(
        "--save",
        help="save the chart to file instead of displaying",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    csv_path = Path(args.csv).expanduser()
    if not csv_path.is_file():
        log.error("file not found: %s", csv_path)
        sys.exit(1)

    try:
        import matplotlib.pyplot as plt  # type: ignore[import-not-found]
    except ImportError:
        log.error("missing dependency: install with `pip install matplotlib`")
        sys.exit(1)

    data, title = _read_data(
        csv_path, min_version=args.min_version, threshold=args.threshold
    )
    versions = sorted(data.keys(), key=lambda v: int(v) if v.isdigit() else float("inf"))
    percentages = [data[v] for v in versions]

    fig, ax = plt.subplots()
    ax.pie(percentages, labels=versions, autopct="%1.1f%%", startangle=90)
    plt.title(title, y=1.08)
    plt.axis("equal")
    plt.subplots_adjust(top=0.85)

    if args.save:
        plt.savefig(args.save)
        log.success("chart saved to %s", args.save)
    else:
        plt.show()


if __name__ == "__main__":
    main()
