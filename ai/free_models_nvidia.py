#!/usr/bin/env python3
"""List all free endpoint models from build.nvidia.com in a table format."""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request


def fetch_page(url: str) -> str:
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} {e.reason}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Network Error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def extract_models(html: str) -> list[dict]:
    scripts = re.finditer(
        r'<script[^>]*>self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>',
        html,
        re.DOTALL,
    )

    largest = max(scripts, key=lambda m: len(m.group(1)), default=None)
    if not largest:
        return []

    raw_data = largest.group(1)
    unescaped = raw_data.replace('\\"', '"')

    model_starts = re.finditer(
        r'\{"orgName":"[^"]+","resourceId":"([^"]+)"',
        unescaped,
    )

    free_models = []
    seen_ids = set()

    for start_match in model_starts:
        rid_full = start_match.group(1)
        rid = rid_full.split("/")[-1]

        if rid in seen_ids:
            continue

        obj_start = start_match.start()
        remaining = unescaped[obj_start:]

        depth = 0
        obj_end = -1
        in_string = False
        escape_next = False
        for i, c in enumerate(remaining):
            if escape_next:
                escape_next = False
                continue
            if c == "\\":
                escape_next = True
                continue
            if c == '"':
                in_string = not in_string
                continue
            if not in_string:
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        obj_end = i
                        break

        if obj_end < 0:
            continue

        obj_str = remaining[: obj_end + 1]

        if "Free Endpoint" not in obj_str:
            continue

        try:
            obj = json.loads(obj_str)
        except json.JSONDecodeError:
            continue

        labels = obj.get("labels", [])
        is_free = False
        for label in labels:
            if label.get("key") == "nimType":
                if "Free Endpoint" in label.get("values", []):
                    is_free = True
                    break

        if not is_free:
            continue

        seen_ids.add(rid)

        publisher = "unknown"
        usecase = ""
        for label in labels:
            if label.get("key") == "publisher":
                vals = label.get("values", [])
                if vals:
                    publisher = vals[0]
            if label.get("key") == "general":
                vals = label.get("values", [])
                if vals:
                    usecase = vals[0]

        free_models.append(
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

    return free_models


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List free endpoint models from build.nvidia.com in a table.",
    )
    parser.add_argument(
        "--sort",
        choices=["date", "name", "popular"],
        default="date",
        help="Sort order (default: date).",
    )
    args = parser.parse_args()

    url = "https://build.nvidia.com/models"
    html = fetch_page(url)

    models = extract_models(html)

    if args.sort == "date":
        models.sort(key=lambda m: m["date"], reverse=True)
    elif args.sort == "popular":
        models.sort(key=lambda m: m["weight"], reverse=True)
    else:
        models.sort(key=lambda m: m["name"])

    col_name = "Model"
    col_id = "ID"
    col_publisher = "Publisher"
    col_usecase = "Use Case"
    col_desc = "Description"
    col_date = "Modified"

    rows = []
    for model in models:
        desc = model["description"]
        if len(desc) > 80:
            desc = desc[:77] + "..."
        date_short = model["date"][:10] if model["date"] else "-"
        rows.append(
            [
                model["name"],
                model["id"],
                model["publisher"],
                model["usecase"],
                desc,
                date_short,
            ]
        )

    col_widths = [
        len(col_name),
        len(col_id),
        len(col_publisher),
        len(col_usecase),
        len(col_desc),
        len(col_date),
    ]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))

    header = "  ".join(
        s.ljust(w)
        for s, w in zip(
            [col_name, col_id, col_publisher, col_usecase, col_desc, col_date],
            col_widths,
        )
    )
    separator = "  ".join("-" * w for w in col_widths)

    print(header)
    print(separator)
    for row in rows:
        print("  ".join(s.ljust(w) for s, w in zip(row, col_widths)))


if __name__ == "__main__":
    main()
