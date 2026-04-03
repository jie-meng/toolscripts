#!/usr/bin/env python3
"""List all free models from OpenRouter."""

import json
import sys
import urllib.request
import urllib.error


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
            free_models.append(model["id"])

    for model_id in free_models:
        print(model_id)


if __name__ == "__main__":
    main()
