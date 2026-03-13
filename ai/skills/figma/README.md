# Figma Design Fetcher

Fetch design specs (layout, colors, typography, components) from a Figma URL and output structured markdown for AI-assisted code generation.

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

```bash
# Inspect a specific node (URL with node-id)
python3 scripts/figma_fetch.py "https://www.figma.com/design/ABC123/Name?node-id=1-2"

# File overview (URL without node-id)
python3 scripts/figma_fetch.py "https://www.figma.com/design/ABC123/Name"

# Limit tree depth (default: 5)
python3 scripts/figma_fetch.py "https://..." --depth 3
```

**Requirements**: Python 3.8+ (standard library only, zero dependencies).

**Supported URL formats**:
- `https://www.figma.com/design/FILE_KEY/Name?node-id=1-2`
- `https://www.figma.com/file/FILE_KEY/Name?node-id=1%3A2`
- `https://www.figma.com/proto/FILE_KEY/Name`

## Output Format

When a node is fetched, the script outputs structured markdown with these sections:

| Section | Content |
|---|---|
| **Layout** | Width × height, auto-layout mode, padding, gap |
| **Colors** | Fill colors as hex (#RRGGBB), opacity if < 1.0, gradient descriptions |
| **Borders** | Corner radius (uniform or per-corner), stroke color + weight + alignment |
| **Effects** | Drop/inner shadows with color, offset, blur, spread; layer/background blurs |
| **Typography** | Font family, size, weight, line height, letter spacing, alignment (TEXT nodes) |
| **Content** | Text content (truncated at 200 chars) |
| **Children** | Recursive tree of child nodes up to `--depth` levels |

### Figma API Notes

- Sizes come from `absoluteBoundingBox.width/height` (always present), not `size` (only with `geometry=paths`)
- Colors are RGBA floats (0–1), converted to hex by the script
- Auto-layout padding: `paddingTop/Right/Bottom/Left` and `itemSpacing`
- Text styles are on `node.style` (TypeStyle object), not directly on the node
- `fills` and `strokes` are arrays of Paint objects; `type: SOLID` has a `color` sub-object

## Error Handling

| Exit Code | Error | Cause | Fix |
|---|---|---|---|
| 1 | `FIGMA_ACCESS_TOKEN not set` | Token missing from env | Set `export FIGMA_ACCESS_TOKEN=xxx` |
| 1 | `Figma API 403` | Token invalid or expired | Regenerate at figma.com/settings |
| 1 | `Figma API 404` | File not found or no access | Check URL; ensure you have view access |
| 2 | `Could not parse file key` | Malformed URL | Use a URL copied directly from Figma |
| 1 | `Node not found` | node-id refers to deleted/moved node | Re-copy the link from Figma |
| — | Script hangs | Network timeout | Check internet; try again |

If the response is empty or truncated on large files, use `--depth 2` to limit traversal.
