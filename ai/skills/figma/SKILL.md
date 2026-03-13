---
name: figma
description: >
  Fetch Figma design data from a URL and inject specs (layout, colors, typography,
  components) into context. Use when user shares a Figma link and asks to implement,
  inspect, match, or code a design. Trigger on ANY message containing a figma.com
  URL, or when the user asks about colors/spacing/fonts from a design, or says
  "implement this design", "match this component", "what does the design look like",
  "according to Figma", "from the design file".
---

# When to Use This Skill

- A message contains a `figma.com` URL (design, file, proto)
- User asks about colors, spacing, fonts, or dimensions from a design
- User wants to implement, match, or code a component from a design
- User says "according to Figma", "from the design", "in the mockup"

# Prerequisites

Requires `FIGMA_ACCESS_TOKEN` environment variable. See `README.md` in this skill directory for setup instructions.

# Workflow

1. Extract the Figma URL from the user's message
2. Run the fetch script to get structured design specs
3. Read the markdown output
4. Use the specs (sizes, colors, fonts, layout) to generate accurate code

## Running the Script

The script is at `scripts/figma_fetch.py` relative to this skill directory. It requires only Python 3.8+ standard library (zero dependencies).

```bash
# Inspect a specific node (most common — URL contains node-id)
python3 scripts/figma_fetch.py "https://www.figma.com/design/ABC123/Name?node-id=1-2"

# File overview (no node-id in URL)
python3 scripts/figma_fetch.py "https://www.figma.com/design/ABC123/Name"

# Limit tree depth (default: 5)
python3 scripts/figma_fetch.py "https://..." --depth 3
```

Exit codes: 0 = success, 1 = API error, 2 = bad arguments. On error, surface the printed message to the user.

## Using the Output

The script outputs structured markdown covering all visual and layout properties present on each node. The exact fields vary by node type — a FRAME with auto-layout produces different output than a TEXT node. Read what's there; don't expect every section to appear on every node.

Typical sections include layout dimensions, fills/strokes, effects, typography (TEXT nodes), component metadata, and design token bindings. Use these values to generate accurate CSS or UI code matching the design. When a section is absent, the node doesn't have that property set.
