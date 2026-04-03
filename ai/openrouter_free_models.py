#!/usr/bin/env python3
"""List all free models from OpenRouter in a table format."""

import json
import sys
import urllib.error
import urllib.request


def format_context_length(length: int | None) -> str:
    if length is None:
        return "-"
    if length >= 1_000_000:
        return f"{length // 1_000_000}M"
    return f"{length // 1000}K"


def format_modality(modality: str | None) -> str:
    if modality is None:
        return "-"
    return modality.replace("->", " → ")


def main() -> None:
    url = "https://openrouter.ai/api/v1/models"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} {e.reason}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Network Error: {e.reason}", file=sys.stderr)
        sys.exit(1)

    free_models = []
    for model in data.get("data", []):
        pricing = model.get("pricing", {})
        if pricing.get("prompt", "0") == "0" and pricing.get("completion", "0") == "0":
            free_models.append(model)

    free_models.sort(key=lambda m: m.get("context_length", 0) or 0, reverse=True)

    col_name = "Model"
    col_context = "Context"
    col_max_out = "Max Out"
    col_modality = "Modality"
    col_params = "Params"

    rows = [
        [
            model["id"],
            format_context_length(model.get("context_length")),
            str(model.get("top_provider", {}).get("max_completion_tokens") or "-"),
            format_modality(model.get("architecture", {}).get("modality")),
            str(len(model.get("supported_parameters", []))),
        ]
        for model in free_models
    ]

    col_widths = [
        len(col_name),
        len(col_context),
        len(col_max_out),
        len(col_modality),
        len(col_params),
    ]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))

    header = "  ".join(
        s.ljust(w)
        for s, w in zip(
            [col_name, col_context, col_max_out, col_modality, col_params], col_widths
        )
    )
    separator = "  ".join("-" * w for w in col_widths)

    print(header)
    print(separator)
    for row in rows:
        print("  ".join(s.ljust(w) for s, w in zip(row, col_widths)))


if __name__ == "__main__":
    main()
