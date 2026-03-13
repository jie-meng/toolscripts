# figma skill — Implementation Plan

## Background & Decision

### Why Skill Instead of MCP?

| Dimension | MCP | Skill |
|-----------|-----|-------|
| Startup | Resident process, requires `mcp.json` config | Zero process, AI directly executes bash script |
| User Setup | Clone repo + install deps + configure paths | Just `export FIGMA_ACCESS_TOKEN=xxx` in `.zshrc` |
| Distribution | Requires repo + runtime environment | Single `SKILL.md` file |
| Best For | Persistent connections, bidirectional comms, auto tool discovery | One-time queries, context injection ✅ |
| Resource Use | Always-on process consumes idle resources | On-demand execution, exits after use |

**Core Decision**: User need is "paste a Figma URL, AI fetches design info as context"—classic one-time context injection. Skill fully covers this; MCP advantages (persistent connections, streaming) have no value here.

---

## Objectives

**Skill Trigger Scenarios**:
- User pastes a Figma URL and asks "help me implement this component"
- User says "check this design: [URL], what color is it?"
- User requests "write CSS based on Figma design, link: [URL]"

**Skill Responsibilities**:
1. Parse URL, extract `file_key` and `node_id`
2. Call Figma REST API, fetch node design data
3. Inject structured design info (dimensions, colors, typography, spacing, component tree) into AI context
4. AI uses this info to generate accurate code without screenshots or manual description

---

## Skill File Structure

```
~/.claude/skills/figma/
├── SKILL.md          ← all content (docs + embedded script)
└── scripts/
    └── figma_fetch.py   ← the actual runnable script
```

Embed a self-contained Python script with **only stdlib dependencies** (`urllib`, `json`, `re`, `os`). No `pip install` needed.

---

## SKILL.md Content Plan

### Frontmatter

```yaml
---
name: figma
description: >
  Fetch Figma design data from a URL and inject specs (layout, colors, typography,
  components) into context. Use when user shares a Figma link and asks to implement,
  inspect, or match a design. Requires FIGMA_ACCESS_TOKEN in environment.
---
```

### Trigger Conditions (Skill Documentation Section)

AI should use this skill when:
- Message contains a `figma.com` URL
- User asks about design colors, dimensions, fonts, spacing
- User requests "implement based on design" for a component

### Prerequisite Check (Script First Step)

```python
import os
token = os.environ.get("FIGMA_ACCESS_TOKEN", "")
if not token:
    print("ERROR: FIGMA_ACCESS_TOKEN not set.")
    print("Add to ~/.zshrc:  export FIGMA_ACCESS_TOKEN=your_token")
    print("Get token: https://www.figma.com/settings → Personal access tokens")
    exit(1)
```

---

## Core Python Script Design

### Module 1: URL Parsing

```
parse_figma_url(url) -> (file_key, node_id | None)
```

Supports all Figma URL formats:
- `https://www.figma.com/design/ABC123/Name?node-id=1-2`
- `https://www.figma.com/file/ABC123/Name?node-id=1%3A2`
- `https://www.figma.com/proto/ABC123/Name`

Normalize `node-id` to colon format (`1:2`), handle hyphens and `%3A` in URLs.

### Module 2: Figma API Calls (Stdlib Only)

Use `urllib.request` instead of `httpx` for zero dependencies:

```python
import urllib.request, json

def figma_get(path, token, **params):
    from urllib.parse import urlencode
    url = f"https://api.figma.com{path}"
    if params:
        url += "?" + urlencode(params)
    req = urllib.request.Request(url, headers={"X-Figma-Token": token})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())
```

API endpoints used:

| Endpoint | Purpose | Called When |
|----------|---------|------------|
| `GET /v1/files/:key?depth=1` | File overview (name, page list) | No node_id |
| `GET /v1/files/:key/nodes?ids=:id` | Complete design tree for node | Has node_id (primary path) |
| `GET /v1/files/:key/components` | Component list | User asks "what components?" |
| `GET /v1/files/:key/styles` | Styles list (colors/fonts/effects) | Supplementary info |
| `GET /v1/images/:key?ids=:id` | Node render image URL | User needs visual reference |

### Module 3: Data Simplification (simplify_node)

Raw Figma responses can reach 100MB+; must be trimmed before injection. Retained fields:

**Geometry & Layout**
- `size`: `{width, height}`
- `position`: `{x, y}`
- `constraints`
- `layoutMode` (HORIZONTAL / VERTICAL / NONE)
- `paddingLeft/Right/Top/Bottom`
- `itemSpacing` (auto-layout gap)

**Visual Styling**
- `fills` → extract hex color + opacity
- `strokes` → hex + weight
- `cornerRadius`
- `opacity`
- `effects` (shadows, blur)

**Typography** (TEXT nodes)
- `fontFamily`, `fontWeight`, `fontSize`
- `lineHeightPx`, `letterSpacing`
- `textAlignHorizontal`
- `characters` (text content, truncated to 200 chars)

**Component Info**
- `componentId`
- `componentProperties`

**Subtree**: Recursive processing, default `max_depth=5`, mark truncation beyond that.

### Module 4: Output Format

Script outputs **structured markdown** to stdout for direct AI consumption:

```
## Figma Design Specs
**File**: My Design System  
**Node**: Button / Primary / Large  
**Node ID**: 1:234

### Layout
- Size: 160 × 48px
- Padding: 16px (horizontal), 12px (vertical)
- Auto-layout: HORIZONTAL, gap: 8px

### Colors
- Fill: #3B5BDB (opacity: 1.0)
- Stroke: none

### Typography
- Font: Inter, 16px, weight 600
- Line height: 24px
- Content: "Button"

### Borders
- Corner radius: 8px

### Children (3)
- [VECTOR] icon (24×24px)
- [TEXT] label: "Button"
- ...
```

---

## Usage Instructions (Skill Documentation)

### User Setup (One-Time)

```bash
# 1. Get token: https://www.figma.com/settings → Personal access tokens
# 2. Add to shell config
echo 'export FIGMA_ACCESS_TOKEN=your_token_here' >> ~/.zshrc
source ~/.zshrc
```

### AI Script Invocation (Script Interface)

```bash
# Query specific node
python3 ~/.claude/skills/figma/scripts/figma_fetch.py "https://www.figma.com/design/ABC123/Name?node-id=1-2"

# Query file overview (no node-id)
python3 ~/.claude/skills/figma/scripts/figma_fetch.py "https://www.figma.com/design/ABC123/Name"

# Specify max_depth (default 5)
python3 ~/.claude/skills/figma/scripts/figma_fetch.py "https://..." --depth 3
```

Script accepts URL as first argument, optional `--depth N`.

---

## Complete Script Flow (Pseudocode)

```
main(url, depth=5):
  1. Read FIGMA_ACCESS_TOKEN, error if missing
  2. parse_figma_url(url) → file_key, node_id
  3. if node_id:
       data = GET /v1/files/:key/nodes?ids=:node_id
       node = data["nodes"][node_id]["document"]
       output = simplify_node(node, max_depth=depth)
       print_markdown(output, file_name=data["name"])
     else:
       data = GET /v1/files/:key?depth=1
       pages = [p["name"] for p in data["document"]["children"]]
       print_file_overview(data["name"], pages, component_count, style_count)
  4. Exit codes: 0 (success) / 1 (API error) / 2 (argument error)
```

---

## SKILL.md Structure Outline

```
---
frontmatter (name, description)
---

# When to Use This Skill
[Trigger conditions]

# Prerequisites
[FIGMA_ACCESS_TOKEN setup]

# How It Works
[How AI uses this skill: identify URL → run script → read result → generate code]

# Python Script
[Complete embedded Python script, stdlib, directly copy-paste executable]

# Output Format Reference
[Output field descriptions, helps AI understand result structure]

# Error Handling
[Common errors and solutions]
```

---

## Out of Scope (Intentionally Not Included)

The following are **beyond this skill's scope**:

- **Variables/Tokens API** (requires Enterprise account)
- **Comments API** (unrelated to code generation)
- **Webhooks** (requires server, unsuitable for skill)
- **Batch multi-file queries** (single on-demand queries more appropriate)
- **Image URL fetching** (AI can't directly display images; limited value; can be v2 addition)

---

## Success Criteria

Implementation is complete when all scenarios work:

1. User pastes URL with `node-id` → script outputs complete dimensions/colors/typography specs
2. User pastes file URL without `node-id` → script outputs file overview (page list, component count)
3. Token not configured → clear error message directs user where to configure
4. Invalid URL → clear error message
5. Script requires **no** `pip install`, runs on Python 3.8+ stdlib only
6. Output in markdown format, ready for AI code generation
