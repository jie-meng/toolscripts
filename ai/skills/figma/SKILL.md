---
name: figma
description: >
  Fetch Figma design data from a URL and inject specs (layout, colors, typography,
  components) into context. Use when user shares a Figma link and asks to implement,
  inspect, match, or code a design. Trigger on ANY message containing a figma.com
  URL, or when the user asks about colors/spacing/fonts from a design, or says
  "implement this design", "match this component", "what does the design look like",
  "according to Figma", "from the design file". Requires FIGMA_ACCESS_TOKEN in
  environment.
---

# When to Use This Skill

Use this skill whenever:

- A message contains a `figma.com` URL (design, file, proto)
- User asks about colors, spacing, fonts, or dimensions from a design
- User wants to implement, match, or code a component from a design
- User says "according to Figma", "from the design", "in the mockup"

# Prerequisites

The user needs a Figma personal access token (one-time setup):

```bash
# 1. Get token: https://www.figma.com/settings → Security → Personal access tokens
# 2. Add to shell config
echo 'export FIGMA_ACCESS_TOKEN=your_token_here' >> ~/.zshrc
source ~/.zshrc
```

# How It Works

1. Extract the Figma URL from the user's message
2. Run the embedded Python script to fetch design specs
3. Read the structured markdown output
4. Use the specs (sizes, colors, fonts, layout) to generate accurate code

```bash
# Inspect a specific node (most common)
python3 ~/.claude/skills/figma/scripts/figma_fetch.py "https://www.figma.com/design/ABC123/Name?node-id=1-2"

# File overview (no node-id in URL)
python3 ~/.claude/skills/figma/scripts/figma_fetch.py "https://www.figma.com/design/ABC123/Name"

# Limit tree depth (default: 5)
python3 ~/.claude/skills/figma/scripts/figma_fetch.py "https://..." --depth 3
```

The script exits 0 on success, 1 on API error, 2 on bad arguments. On error it prints a clear message — surface it to the user.

The script lives at `scripts/figma_fetch.py` in this skill directory. It is also embedded below for reference or if the user needs to inspect/copy it manually.

# Python Script

The script is at `scripts/figma_fetch.py`. Save this as `~/.claude/skills/figma/scripts/figma_fetch.py` if setting up manually:

```python
#!/usr/bin/env python3
"""
figma_fetch.py — Fetch Figma design specs and output structured markdown.
Zero dependencies: Python 3.8+ standard library only.
"""
import os, sys, json, re, argparse
import urllib.request
from urllib.parse import urlencode, unquote


# ── Token ──────────────────────────────────────────────────────────────────────

def get_token():
    token = os.environ.get("FIGMA_ACCESS_TOKEN", "").strip()
    if not token:
        print("ERROR: FIGMA_ACCESS_TOKEN not set.", file=sys.stderr)
        print("Add to ~/.zshrc:  export FIGMA_ACCESS_TOKEN=your_token", file=sys.stderr)
        print("Get token: https://www.figma.com/settings → Security → Personal access tokens", file=sys.stderr)
        sys.exit(1)
    return token


# ── URL Parsing ────────────────────────────────────────────────────────────────

def parse_figma_url(url):
    """
    Returns (file_key, node_id_or_None).
    Handles all URL formats:
      https://www.figma.com/design/FILE_KEY/Name?node-id=1-2
      https://www.figma.com/file/FILE_KEY/Name?node-id=1%3A2
      https://www.figma.com/proto/FILE_KEY/Name
    node_id is normalized to colon format (e.g. "1:2").
    """
    m = re.search(r'figma\.com/(?:design|file|proto)/([A-Za-z0-9_-]+)', url)
    if not m:
        print(f"ERROR: Could not parse file key from URL: {url}", file=sys.stderr)
        sys.exit(2)
    file_key = m.group(1)

    node_id = None
    nid_m = re.search(r'node[-_]id=([^&]+)', url)
    if nid_m:
        raw = unquote(nid_m.group(1))       # decode %3A → :
        node_id = raw.replace('-', ':')      # normalize 1-2 → 1:2
    return file_key, node_id


# ── API Client ─────────────────────────────────────────────────────────────────

def figma_get(path, token, **params):
    """Make a GET request to the Figma REST API."""
    url = f"https://api.figma.com{path}"
    if params:
        url += "?" + urlencode(params)
    req = urllib.request.Request(url, headers={"X-Figma-Token": token})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"ERROR: Figma API {e.code} for {path}: {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: Network error: {e.reason}", file=sys.stderr)
        sys.exit(1)


# ── Color Helpers ──────────────────────────────────────────────────────────────

def rgba_to_hex(color):
    """Convert Figma RGBA (0-1 floats) to '#RRGGBB' hex string."""
    r = round(color.get("r", 0) * 255)
    g = round(color.get("g", 0) * 255)
    b = round(color.get("b", 0) * 255)
    return f"#{r:02X}{g:02X}{b:02X}"

def format_paint(paint):
    """Summarize a Paint object to a readable string."""
    if not paint.get("visible", True):
        return None
    t = paint.get("type", "SOLID")
    opacity = paint.get("opacity", 1.0)
    if t == "SOLID":
        color = paint.get("color", {})
        hex_val = rgba_to_hex(color)
        alpha = color.get("a", 1.0) * opacity
        if alpha < 1.0:
            return f"{hex_val} (opacity: {alpha:.2f})"
        return hex_val
    elif t.startswith("GRADIENT"):
        stops = paint.get("gradientStops", [])
        stop_strs = [f"{rgba_to_hex(s['color'])} at {s['position']:.0%}" for s in stops[:3]]
        return f"{t}: {', '.join(stop_strs)}"
    elif t == "IMAGE":
        return "image fill"
    return t.lower().replace("_", " ")


# ── Node Simplifier ────────────────────────────────────────────────────────────

def simplify_node(node, depth=0, max_depth=5):
    """
    Extract the design-relevant fields from a Figma node.
    Returns a dict ready to render as markdown.
    """
    if node is None:
        return None

    result = {
        "id": node.get("id"),
        "name": node.get("name", ""),
        "type": node.get("type", ""),
    }

    # ── Geometry ──
    bbox = node.get("absoluteBoundingBox")
    if bbox:
        result["size"] = {
            "width": round(bbox["width"], 2),
            "height": round(bbox["height"], 2),
        }
        result["position"] = {
            "x": round(bbox["x"], 2),
            "y": round(bbox["y"], 2),
        }

    # ── Opacity ──
    opacity = node.get("opacity")
    if opacity is not None and opacity != 1.0:
        result["opacity"] = round(opacity, 3)

    # ── Fills ──
    fills = node.get("fills", [])
    parsed_fills = [format_paint(f) for f in fills if format_paint(f)]
    if parsed_fills:
        result["fills"] = parsed_fills

    # ── Strokes ──
    strokes = node.get("strokes", [])
    parsed_strokes = [format_paint(s) for s in strokes if format_paint(s)]
    if parsed_strokes:
        result["strokes"] = parsed_strokes
        weight = node.get("strokeWeight")
        if weight:
            result["strokeWeight"] = weight
        result["strokeAlign"] = node.get("strokeAlign", "CENTER")

    # ── Corner radius ──
    cr = node.get("cornerRadius")
    if cr:
        result["cornerRadius"] = cr
    per_corner = node.get("rectangleCornerRadii")
    if per_corner and per_corner != [cr, cr, cr, cr]:
        result["rectangleCornerRadii"] = per_corner

    # ── Auto-layout ──
    layout_mode = node.get("layoutMode", "NONE")
    if layout_mode != "NONE":
        result["layoutMode"] = layout_mode
        result["paddingTop"] = node.get("paddingTop", 0)
        result["paddingRight"] = node.get("paddingRight", 0)
        result["paddingBottom"] = node.get("paddingBottom", 0)
        result["paddingLeft"] = node.get("paddingLeft", 0)
        result["itemSpacing"] = node.get("itemSpacing", 0)
        result["primaryAxisAlignItems"] = node.get("primaryAxisAlignItems", "MIN")
        result["counterAxisAlignItems"] = node.get("counterAxisAlignItems", "MIN")
        result["layoutSizingHorizontal"] = node.get("layoutSizingHorizontal")
        result["layoutSizingVertical"] = node.get("layoutSizingVertical")

    # ── Effects (shadows, blurs) ──
    effects = node.get("effects", [])
    visible_effects = [e for e in effects if e.get("visible", True)]
    if visible_effects:
        formatted = []
        for e in visible_effects:
            etype = e.get("type", "")
            if "SHADOW" in etype:
                c = e.get("color", {})
                off = e.get("offset", {})
                formatted.append(
                    f"{etype.lower().replace('_', ' ')}: "
                    f"color={rgba_to_hex(c)} offset=({off.get('x',0)},{off.get('y',0)}) "
                    f"blur={e.get('radius',0)} spread={e.get('spread',0)}"
                )
            elif "BLUR" in etype:
                formatted.append(f"{etype.lower().replace('_', ' ')}: radius={e.get('radius',0)}")
        if formatted:
            result["effects"] = formatted

    # ── Typography (TEXT nodes) ──
    if node.get("type") == "TEXT":
        style = node.get("style", {})
        result["typography"] = {
            "fontFamily": style.get("fontFamily"),
            "fontWeight": style.get("fontWeight"),
            "fontSize": style.get("fontSize"),
            "lineHeightPx": style.get("lineHeightPx"),
            "letterSpacing": style.get("letterSpacing"),
            "textAlignHorizontal": style.get("textAlignHorizontal"),
            "italic": style.get("italic", False),
        }
        chars = node.get("characters", "")
        result["characters"] = chars[:200] + ("…" if len(chars) > 200 else "")

    # ── Component info ──
    comp_id = node.get("componentId")
    if comp_id:
        result["componentId"] = comp_id
    comp_props = node.get("componentProperties")
    if comp_props:
        result["componentProperties"] = comp_props

    # ── Children ──
    children = node.get("children", [])
    if children:
        if depth >= max_depth:
            result["_children_truncated"] = len(children)
        else:
            result["children"] = [
                simplify_node(c, depth + 1, max_depth)
                for c in children
                if c is not None
            ]

    return result


# ── Markdown Renderer ──────────────────────────────────────────────────────────

def render_node_markdown(node_data, file_name):
    """Render the simplified node dict as readable markdown for AI context."""
    lines = ["## Figma Design Specs"]
    lines.append(f"**File**: {file_name}")
    lines.append(f"**Node**: {node_data.get('name', '(unknown)')}")
    lines.append(f"**Node ID**: {node_data.get('id', '')}")
    lines.append(f"**Type**: {node_data.get('type', '')}")
    lines.append("")
    _render_node_section(lines, node_data, indent=0, top_level=True)
    return "\n".join(lines)


def _render_node_section(lines, node, indent=0, top_level=False):
    prefix = "  " * indent

    if not top_level:
        ntype = node.get("type", "")
        name = node.get("name", "")
        lines.append(f"{prefix}### [{ntype}] {name}")

    # Size & Position
    size = node.get("size")
    pos = node.get("position")
    if size or pos:
        if top_level:
            lines.append(f"{prefix}### Layout")
        if size:
            lines.append(f"{prefix}- Size: {size['width']} × {size['height']}px")
        if pos and not top_level:
            lines.append(f"{prefix}- Position: x={pos['x']}, y={pos['y']}")

    # Auto-layout
    layout = node.get("layoutMode")
    if layout:
        lines.append(f"{prefix}- Auto-layout: {layout}, gap: {node.get('itemSpacing', 0)}px")
        pt = node.get("paddingTop", 0)
        pr = node.get("paddingRight", 0)
        pb = node.get("paddingBottom", 0)
        pl = node.get("paddingLeft", 0)
        if any([pt, pr, pb, pl]):
            lines.append(f"{prefix}- Padding: top={pt} right={pr} bottom={pb} left={pl}")
        h_sizing = node.get("layoutSizingHorizontal")
        v_sizing = node.get("layoutSizingVertical")
        if h_sizing or v_sizing:
            lines.append(f"{prefix}- Sizing: horizontal={h_sizing}, vertical={v_sizing}")
        lines.append(f"{prefix}- Align (primary): {node.get('primaryAxisAlignItems')}, counter: {node.get('counterAxisAlignItems')}")

    # Fills
    fills = node.get("fills")
    if fills:
        if top_level:
            lines.append(f"{prefix}### Colors")
        for fill in fills:
            lines.append(f"{prefix}- Fill: {fill}")

    # Strokes
    strokes = node.get("strokes")
    if strokes:
        for stroke in strokes:
            weight = node.get("strokeWeight", "")
            align = node.get("strokeAlign", "")
            lines.append(f"{prefix}- Stroke: {stroke} ({weight}px, {align})")

    # Corner radius
    cr = node.get("cornerRadius")
    if cr:
        if top_level:
            lines.append(f"{prefix}### Borders")
        lines.append(f"{prefix}- Corner radius: {cr}px")
    per_corner = node.get("rectangleCornerRadii")
    if per_corner:
        lines.append(f"{prefix}- Corner radii (TL TR BR BL): {per_corner}")

    # Opacity
    opacity = node.get("opacity")
    if opacity is not None:
        lines.append(f"{prefix}- Opacity: {opacity}")

    # Effects
    effects = node.get("effects")
    if effects:
        if top_level:
            lines.append(f"{prefix}### Effects")
        for e in effects:
            lines.append(f"{prefix}- {e}")

    # Typography
    typo = node.get("typography")
    if typo:
        if top_level:
            lines.append(f"{prefix}### Typography")
        lines.append(f"{prefix}- Font: {typo.get('fontFamily')}, {typo.get('fontSize')}px, weight {typo.get('fontWeight')}")
        if typo.get("italic"):
            lines.append(f"{prefix}- Style: italic")
        lh = typo.get("lineHeightPx")
        if lh:
            lines.append(f"{prefix}- Line height: {lh}px")
        ls = typo.get("letterSpacing")
        if ls:
            lines.append(f"{prefix}- Letter spacing: {ls}px")
        align = typo.get("textAlignHorizontal")
        if align:
            lines.append(f"{prefix}- Text align: {align}")
    chars = node.get("characters")
    if chars:
        if top_level:
            lines.append(f"{prefix}### Content")
        lines.append(f'{prefix}- Text: "{chars}"')

    # Component info
    comp_id = node.get("componentId")
    if comp_id:
        lines.append(f"{prefix}- Component ID: {comp_id}")

    # Children
    trunc = node.get("_children_truncated")
    if trunc:
        lines.append(f"{prefix}- ... ({trunc} children truncated — use --depth to go deeper)")
        return

    children = node.get("children", [])
    if children:
        if top_level:
            lines.append(f"{prefix}### Children ({len(children)})")
        for child in children:
            if child:
                lines.append("")
                _render_node_section(lines, child, indent=indent + 1)


def render_file_overview(data):
    """Render a file-level overview when no node_id is provided."""
    name = data.get("name", "Unknown")
    doc = data.get("document", {})
    pages = doc.get("children", [])
    components = data.get("components", {})
    styles = data.get("styles", {})

    lines = [
        "## Figma File Overview",
        f"**File**: {name}",
        f"**Pages** ({len(pages)}):",
    ]
    for page in pages:
        lines.append(f"  - {page.get('name', '(unnamed)')}")
    lines.append(f"**Components**: {len(components)}")
    lines.append(f"**Styles**: {len(styles)}")
    if components:
        lines.append("")
        lines.append("**Component list (first 20):**")
        for i, (nid, comp) in enumerate(components.items()):
            if i >= 20:
                lines.append(f"  ... and {len(components) - 20} more")
                break
            lines.append(f"  - {comp.get('name', '(unnamed)')} (id: {nid})")
    lines.append("")
    lines.append("To inspect a specific element, open the file in Figma, right-click a layer → 'Copy link to selection', then run this skill again with that URL.")
    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fetch Figma design specs.")
    parser.add_argument("url", help="Figma URL (design/file/proto)")
    parser.add_argument("--depth", type=int, default=5, help="Max tree depth (default: 5)")
    args = parser.parse_args()

    token = get_token()
    file_key, node_id = parse_figma_url(args.url)

    if node_id:
        data = figma_get(f"/v1/files/{file_key}/nodes", token, ids=node_id)
        nodes = data.get("nodes", {})
        node_entry = nodes.get(node_id)
        if node_entry is None:
            # Figma sometimes returns the key with colon encoded; try finding any key
            node_entry = next(iter(nodes.values()), None) if nodes else None
        if node_entry is None:
            print(f"ERROR: Node '{node_id}' not found in file '{file_key}'.", file=sys.stderr)
            print("The node may be on a different page or the ID may be wrong.", file=sys.stderr)
            sys.exit(1)
        doc = node_entry.get("document")
        simplified = simplify_node(doc, max_depth=args.depth)
        file_name = data.get("name", file_key)
        print(render_node_markdown(simplified, file_name))
    else:
        data = figma_get(f"/v1/files/{file_key}", token, depth=1)
        print(render_file_overview(data))


if __name__ == "__main__":
    main()
```

# Output Format Reference

When a node is fetched, the script outputs structured markdown with these sections:

| Section | Content |
|---|---|
| **Layout** | Width × height (from `absoluteBoundingBox`), auto-layout mode, padding, gap |
| **Colors** | Fill colors as hex (#RRGGBB), with opacity if < 1.0; gradient descriptions |
| **Borders** | Corner radius (uniform or per-corner), stroke color + weight + alignment |
| **Effects** | Drop/inner shadows with color, offset, blur, spread; layer/background blurs |
| **Typography** | Font family, size, weight, line height, letter spacing, alignment (TEXT nodes only) |
| **Content** | Text content (truncated at 200 chars) |
| **Children** | Recursive tree of child nodes up to `--depth` levels |

**Key API facts:**
- Sizes come from `absoluteBoundingBox.width/height` (always present), not `size` (only with `geometry=paths`)
- Colors are RGBA floats (0–1), converted to hex by the script
- Auto-layout padding: `paddingTop/Right/Bottom/Left` and `itemSpacing`
- Text styles are on `node.style` (TypeStyle object), not directly on the node
- `fills` and `strokes` are arrays of Paint objects; `type: SOLID` has a `color` sub-object

# Error Handling

| Error | Cause | Fix |
|---|---|---|
| `FIGMA_ACCESS_TOKEN not set` | Token missing from env | Run `export FIGMA_ACCESS_TOKEN=xxx` |
| `Figma API 403` | Token invalid or expired | Regenerate at figma.com/settings |
| `Figma API 404` | File not found or no access | Check the URL; ensure you have view access |
| `Could not parse file key` | Malformed URL | Use a URL copied directly from Figma |
| `Node not found` | node-id refers to a deleted/moved node | Re-copy the link from Figma |
| Script hangs | Network timeout | Check internet connection; try again |

If the token is valid but the response is empty or truncated, the file may be very large. Use `--depth 2` to limit traversal depth.
