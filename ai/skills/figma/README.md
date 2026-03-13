# Figma Design Fetcher

Fetch design specs (layout, colors, typography, components) from a Figma URL and output structured markdown for AI-assisted code generation.

**Official Figma REST API spec**: [github.com/figma/rest-api-spec](https://github.com/figma/rest-api-spec) — OpenAPI YAML + TypeScript types  
**Full API reference**: See [`API_REFERENCE.md`](./API_REFERENCE.md) in this directory.

## Prerequisites

### 1. Get a Figma Personal Access Token

1. Go to [Figma Settings → Security](https://www.figma.com/settings) → **Personal access tokens**
2. Create a new token with read access

### 2. Set the Environment Variable

```bash
# Add to your shell config (~/.zshrc, ~/.bashrc, etc.)
export FIGMA_ACCESS_TOKEN=your_token_here
```

Reload your shell or run `source ~/.zshrc`.

## Usage

Two scripts are available. Both require Python 3.8+ (standard library only, zero dependencies).

### figma_fetch.py — Fetch design specs

```bash
# Inspect a specific node (URL with node-id)
python3 scripts/figma_fetch.py "https://www.figma.com/design/ABC123/Name?node-id=1-2"

# File overview (URL without node-id)
python3 scripts/figma_fetch.py "https://www.figma.com/design/ABC123/Name"

# Limit tree depth (default: 5)
python3 scripts/figma_fetch.py "https://..." --depth 3
```

Outputs structured markdown to stdout with layout, colors, typography, effects, and component data.

### figma_export.py — Export node as image

Downloads a rendered image of a specific Figma node to disk and prints the saved file path.

```bash
# Download as PNG @2x (default)
python3 scripts/figma_export.py "https://www.figma.com/design/ABC123/Name?node-id=1-2"

# SVG export
python3 scripts/figma_export.py "https://..." --format svg

# Specify output path
python3 scripts/figma_export.py "https://..." --format png --scale 1 --output /tmp/button.png
```

**Options**:

| Flag | Default | Description |
|---|---|---|
| `--format` | `png` | `png`, `jpg`, `svg`, or `pdf` |
| `--scale` | `2.0` | Export scale factor 0.01–4 (1.0 = @1x, 2.0 = @2x) |
| `--output` | `./figma_<node-id>.<format>` | Output file path |

On success, prints the **absolute path** of the saved file. Use this path to open the image or pass it to the AI for visual analysis alongside the spec output from `figma_fetch.py`.

**Supported URL formats**:
- `https://www.figma.com/design/FILE_KEY/Name?node-id=1-2`
- `https://www.figma.com/file/FILE_KEY/Name?node-id=1%3A2`
- `https://www.figma.com/proto/FILE_KEY/Name`

> `figma_export.py` requires a URL with a `node-id`. Right-click any layer in Figma → "Copy link to selection" to get one.

## Output Format

The script outputs structured markdown. Fields are emitted only when present on the node — sections that don't apply to a given node type are omitted.

### Node-level metadata (always present)

| Field | Description |
|---|---|
| `id` | Figma node ID |
| `name` | Layer name |
| `type` | Node type (FRAME, TEXT, RECTANGLE, COMPONENT, INSTANCE, etc.) |
| `devStatus` | `READY_FOR_DEV` or `COMPLETED` if set in Dev Mode |

### Visual

| Field | Description |
|---|---|
| **Opacity** | Node-level opacity (omitted when 1.0) |
| **Blend mode** | CSS mix-blend-mode equivalent (omitted when NORMAL/PASS_THROUGH) |
| **Is mask** | Whether this layer is a clipping mask |

### Layout

| Field | Description |
|---|---|
| **Size** | `width × height` from `absoluteBoundingBox` (canvas-space layout dimensions) |
| **Position** | `x, y` from `absoluteBoundingBox` (shown for child nodes) |
| **Render bounds** | Actual visual extents including overflow effects (shadows, blur). Only shown when different from layout bounds. |
| **Rotation** | Layer rotation in degrees |
| **Layout positioning** | `ABSOLUTE` = taken out of auto-layout flow (CSS `position: absolute`) |
| **Layout (child)** | `layoutAlign` + `layoutGrow` — how this child behaves inside a parent auto-layout frame |
| **Constraints** | Horizontal + vertical resize constraints (`LEFT`, `RIGHT`, `CENTER`, `SCALE`, `STRETCH`) |
| **Size constraints** | `minWidth`, `maxWidth`, `minHeight`, `maxHeight` |

### Auto-layout (FRAME nodes with `layoutMode`)

| Field | Description |
|---|---|
| `layoutMode` | `HORIZONTAL`, `VERTICAL`, or `GRID` |
| `itemSpacing` | Gap between children |
| `layoutWrap` | `WRAP` for flex-wrap behavior (omitted when `NO_WRAP`) |
| `counterAxisSpacing` | Gap between wrapped rows/columns (when WRAP) |
| `paddingTop/Right/Bottom/Left` | Inner padding |
| `primaryAxisAlignItems` | Main axis alignment (`MIN`, `CENTER`, `MAX`, `SPACE_BETWEEN`) |
| `counterAxisAlignItems` | Cross axis alignment (`MIN`, `CENTER`, `MAX`, `BASELINE`) |
| `layoutSizingHorizontal/Vertical` | `FIXED`, `HUG`, or `FILL` |
| `itemReverseZIndex` | If `true`, first child is drawn on top (CSS z-order reversal) |

### Colors & Paints

| Paint type | Output format |
|---|---|
| `SOLID` | `#RRGGBB` or `#RRGGBB (opacity: 0.XX)` |
| `GRADIENT_*` | `GRADIENT_LINEAR: #HEX at 0%, #HEX at 100%, ...` |
| `IMAGE` | `image fill (ref: <imageRef>, scale: <scaleMode>)` |
| `PATTERN` | `pattern fill (source: <nodeId>)` |

### Borders & Strokes

| Field | Description |
|---|---|
| `cornerRadius` | Uniform border radius |
| `rectangleCornerRadii` | Per-corner radii `[TL, TR, BR, BL]` (shown only when non-uniform) |
| `cornerSmoothing` | 0–1 (0.6 = iOS squircle) |
| `strokes` | Stroke paint(s) with weight, alignment, cap, join |
| `strokesIncludedInLayout` | Present when `true` — equivalent to CSS `box-sizing: border-box` |

### Effects

| Effect type | Output format |
|---|---|
| `DROP_SHADOW` / `INNER_SHADOW` | `drop shadow: color=#HEX offset=(x,y) blur=N spread=N` |
| `LAYER_BLUR` / `BACKGROUND_BLUR` | `layer blur: radius=N` |

### Typography (TEXT nodes only)

| Field | Description |
|---|---|
| `fontFamily`, `fontSize`, `fontWeight` | Core font identity |
| `italic`, `textCase`, `textDecoration` | Font style modifiers |
| `lineHeightPx` | Line height in pixels |
| `letterSpacing` | Letter spacing |
| `textAlignHorizontal` | `LEFT`, `CENTER`, `RIGHT`, `JUSTIFIED` |
| `textAlignVertical` | `TOP`, `CENTER`, `BOTTOM` |
| `paragraphSpacing`, `paragraphIndent` | Paragraph layout |
| `textTruncation` + `maxLines` | Overflow truncation (ellipsis) |
| `characters` | Text content (truncated at 200 chars) |

### Component metadata (INSTANCE nodes)

| Field | Description |
|---|---|
| `componentId` | ID of the master component |
| `componentProperties` | Override values for component props |

### Export settings

Present when a node has configured export presets: `PNG@2x`, `SVG@1x/icon`, etc.

### Design tokens

| Field | Description |
|---|---|
| `boundVariables` | List of property names driven by Figma Variables (e.g. `fills`, `paddingLeft`). Use `/v1/files/:key/variables/local` to resolve variable values. |

### Children

Rendered recursively up to `--depth` levels. Invisible nodes (`visible: false`) are excluded. When the limit is reached, a truncation note shows the child count.

### Figma API Notes

- Sizes come from `absoluteBoundingBox.width/height` (always present), not `size` (only with `geometry=paths`)
- Colors are RGBA floats (0–1), converted to hex by the script
- `absoluteRenderBounds` is the actual visual extent (includes blur/shadow overflow); differs from `absoluteBoundingBox` when effects overflow the layout box
- Text styles are on `node.style` (TypeStyle object), not directly on the node
- `fills` and `strokes` are arrays of Paint objects; `type: SOLID` has a `color` sub-object
- `layoutPositioning: ABSOLUTE` means a child is pinned inside an auto-layout frame without participating in the layout flow — equivalent to CSS `position: absolute`
- `layoutGrow: 1` on a child = CSS `flex-grow: 1` (fills remaining space)
- `constraints` define how a node resizes when its parent resizes (non-auto-layout frames)

## Error Handling

| Exit Code | Error | Cause | Fix |
|---|---|---|---|
| 1 | `FIGMA_ACCESS_TOKEN not set` | Token missing from env | Set `export FIGMA_ACCESS_TOKEN=xxx` |
| 1 | `Figma API 403` | Token invalid or expired | Regenerate at figma.com/settings |
| 1 | `Figma API 404` | File not found or no access | Check URL; ensure you have view access |
| 2 | `Could not parse file key` | Malformed URL | Use a URL copied directly from Figma |
| 1 | `Node not found` | node-id refers to deleted/moved node | Re-copy the link from Figma |
| 2 | `URL has no node-id` | figma_export.py needs a node URL | Right-click layer → "Copy link to selection" |
| 1 | `No image returned` | Node is empty or render failed | Try a different node; check it has visible content |
| — | Script hangs | Network timeout | Check internet; try again |

If the response is empty or truncated on large files, use `--depth 2` to limit traversal.
