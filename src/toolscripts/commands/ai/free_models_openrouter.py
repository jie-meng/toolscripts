"""``free-models-openrouter`` - list free models from openrouter.ai in a table."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import urllib.error
import urllib.request

from toolscripts.core.log import add_logging_flags, configure_from_args, get_logger

log = get_logger(__name__)


def _format_context(length: int | None) -> str:
    if length is None:
        return "-"
    if length >= 1_000_000:
        return f"{length // 1_000_000}M"
    return f"{length // 1000}K"


def _format_modality(value: str | None) -> str:
    if value is None:
        return "-"
    return value.replace("->", " → ")


def _parse_cutoff(value: str | None) -> dt.date | None:
    if not value or value == "-":
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="free-models-openrouter",
        description="List free OpenRouter models in a plain-text table.",
    )
    parser.add_argument(
        "--sort",
        choices=("context", "knowledge", "name"),
        default="context",
        help="sort order (default: context)",
    )
    add_logging_flags(parser)
    args = parser.parse_args()
    configure_from_args(args)

    url = "https://openrouter.ai/api/v1/models"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read())
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        log.error("network error: %s", exc)
        sys.exit(1)

    free_models = []
    for model in data.get("data", []):
        pricing = model.get("pricing", {})
        if pricing.get("prompt", "0") == "0" and pricing.get("completion", "0") == "0":
            free_models.append(model)

    if args.sort == "context":
        free_models.sort(
            key=lambda m: (m.get("context_length", 0) or 0, m.get("id", "")),
            reverse=True,
        )
    elif args.sort == "knowledge":
        free_models.sort(
            key=lambda m: (
                _parse_cutoff(m.get("knowledge_cutoff")) or dt.date.min,
                m.get("id", ""),
            ),
            reverse=True,
        )
    else:
        free_models.sort(key=lambda m: m.get("id", ""))

    headers = ["Model", "Context", "MaxOut", "Modality", "Knowledge", "Mod", "Params"]
    rows = [
        [
            m["id"],
            _format_context(m.get("context_length")),
            str(m.get("top_provider", {}).get("max_completion_tokens") or "-"),
            _format_modality(m.get("architecture", {}).get("modality")),
            m.get("knowledge_cutoff", "-") or "-",
            "✓" if m.get("top_provider", {}).get("is_moderated") else "-",
            str(len(m.get("supported_parameters", []))),
        ]
        for m in free_models
    ]

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
