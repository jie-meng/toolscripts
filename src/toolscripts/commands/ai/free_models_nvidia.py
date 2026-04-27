"""``free-models-nvidia`` - scrape build.nvidia.com free endpoint models."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)


def _fetch(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        log.error("network error: %s", exc)
        sys.exit(1)


def _extract(html: str) -> list[dict]:
    scripts = re.finditer(
        r'<script[^>]*>self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>',
        html,
        re.DOTALL,
    )
    largest = max(scripts, key=lambda m: len(m.group(1)), default=None)
    if not largest:
        return []
    raw = largest.group(1).replace('\\"', '"')
    starts = re.finditer(r'\{"orgName":"[^"]+","resourceId":"([^"]+)"', raw)

    out: list[dict] = []
    seen: set[str] = set()
    for start in starts:
        rid_full = start.group(1)
        rid = rid_full.split("/")[-1]
        if rid in seen:
            continue

        depth = 0
        in_string = False
        escape = False
        end = -1
        chunk = raw[start.start():]
        for i, ch in enumerate(chunk):
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if not in_string:
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
        if end < 0:
            continue
        body = chunk[: end + 1]
        if "Free Endpoint" not in body:
            continue
        try:
            obj = json.loads(body)
        except json.JSONDecodeError:
            continue

        labels = obj.get("labels", [])
        is_free = any(
            label.get("key") == "nimType" and "Free Endpoint" in label.get("values", [])
            for label in labels
        )
        if not is_free:
            continue

        publisher = next(
            (label.get("values", [None])[0] for label in labels if label.get("key") == "publisher"),
            "unknown",
        ) or "unknown"
        usecase = next(
            (label.get("values", [None])[0] for label in labels if label.get("key") == "general"),
            "",
        ) or ""

        seen.add(rid)
        out.append(
            {
                "name": obj.get("displayName", ""),
                "id": rid,
                "description": obj.get("description", ""),
                "date": obj.get("dateModified", ""),
                "publisher": publisher,
                "usecase": usecase,
                "weight": obj.get("weightPopular", 0),
            }
        )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="free-models-nvidia",
        description="List free endpoint models from build.nvidia.com.",
    )
    parser.add_argument(
        "--sort",
        choices=("date", "name", "popular"),
        default="date",
        help="sort order (default: date)",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    models = _extract(_fetch("https://build.nvidia.com/models"))
    if args.sort == "date":
        models.sort(key=lambda m: m["date"], reverse=True)
    elif args.sort == "popular":
        models.sort(key=lambda m: m["weight"], reverse=True)
    else:
        models.sort(key=lambda m: m["name"])

    headers = ["Model", "ID", "Publisher", "Use Case", "Description", "Modified"]
    rows = []
    for m in models:
        desc = m["description"]
        if len(desc) > 80:
            desc = desc[:77] + "..."
        rows.append([
            m["name"], m["id"], m["publisher"], m["usecase"], desc,
            (m["date"][:10] if m["date"] else "-"),
        ])

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    print("  ".join(h.ljust(w) for h, w in zip(headers, widths, strict=False)))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print("  ".join(cell.ljust(w) for cell, w in zip(row, widths, strict=False)))


if __name__ == "__main__":
    main()
