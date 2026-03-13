#!/usr/bin/env python3

import os, sys, json, re, argparse
import urllib.request
import urllib.error
from urllib.parse import urlencode, unquote


def get_token():
    token = os.environ.get("FIGMA_ACCESS_TOKEN", "").strip()
    if not token:
        print("ERROR: FIGMA_ACCESS_TOKEN not set.", file=sys.stderr)
        print("Add to ~/.zshrc:  export FIGMA_ACCESS_TOKEN=your_token", file=sys.stderr)
        print(
            "Get token: https://www.figma.com/settings → Security → Personal access tokens",
            file=sys.stderr,
        )
        sys.exit(1)
    return token


def parse_figma_url(url):
    m = re.search(r"figma\.com/(?:design|file|proto)/([A-Za-z0-9_-]+)", url)
    if not m:
        print(f"ERROR: Could not parse file key from URL: {url}", file=sys.stderr)
        sys.exit(2)
    file_key = m.group(1)

    node_id = None
    nid_m = re.search(r"node[-_]id=([^&]+)", url)
    if nid_m:
        raw = unquote(nid_m.group(1))  # decode %3A → :
        node_id = raw.replace("-", ":")  # normalize 1-2 → 1:2
    return file_key, node_id


def figma_get(path, token, **params):
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


def rgba_to_hex(color):
    r = round(color.get("r", 0) * 255)
    g = round(color.get("g", 0) * 255)
    b = round(color.get("b", 0) * 255)
    return f"#{r:02X}{g:02X}{b:02X}"


def format_paint(paint):
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
        stop_strs = [
            f"{rgba_to_hex(s['color'])} at {s['position']:.0%}" for s in stops[:3]
        ]
        return f"{t}: {', '.join(stop_strs)}"
    elif t == "IMAGE":
        image_ref = paint.get("imageRef", "")
        scale_mode = paint.get("scaleMode", "FILL")
        suffix = f" (ref: {image_ref}, scale: {scale_mode})" if image_ref else ""
        return f"image fill{suffix}"
    elif t == "PATTERN":
        source = paint.get("sourceNodeId", "")
        return f"pattern fill (source: {source})" if source else "pattern fill"
    return t.lower().replace("_", " ")


def simplify_node(node, depth=0, max_depth=5):
    if node is None:
        return None

    if not node.get("visible", True):
        return None

    result = {
        "id": node.get("id"),
        "name": node.get("name", ""),
        "type": node.get("type", ""),
    }

    blend = node.get("blendMode")
    if blend and blend != "NORMAL" and blend != "PASS_THROUGH":
        result["blendMode"] = blend
    opacity = node.get("opacity")
    if opacity is not None and opacity != 1.0:
        result["opacity"] = round(opacity, 3)

    if node.get("isMask"):
        result["isMask"] = True

    dev_status = node.get("devStatus")
    if dev_status and dev_status.get("type") not in (None, "NONE"):
        result["devStatus"] = dev_status.get("type")

    # absoluteBoundingBox: layout bounds in absolute canvas coords (always present on visible nodes)
    # absoluteRenderBounds: actual visual bounds incl. shadow/blur overflow
    # "size" only exists when geometry=paths is passed — not used here
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
    render_bounds = node.get("absoluteRenderBounds")
    if render_bounds and render_bounds != bbox:
        result["renderBounds"] = {
            "width": round(render_bounds["width"], 2),
            "height": round(render_bounds["height"], 2),
            "x": round(render_bounds["x"], 2),
            "y": round(render_bounds["y"], 2),
        }

    rotation = node.get("rotation")
    if rotation:
        result["rotation"] = round(rotation, 3)

    # layoutPositioning: ABSOLUTE means this node is taken out of auto-layout flow (like CSS position:absolute)
    layout_pos = node.get("layoutPositioning")
    if layout_pos == "ABSOLUTE":
        result["layoutPositioning"] = "ABSOLUTE"

    # layoutAlign / layoutGrow: how this child behaves inside a parent auto-layout frame
    layout_align = node.get("layoutAlign")
    if layout_align and layout_align != "INHERIT":
        result["layoutAlign"] = layout_align
    layout_grow = node.get("layoutGrow")
    if layout_grow:
        result["layoutGrow"] = layout_grow

    constraints = node.get("constraints")
    if constraints:
        result["constraints"] = constraints

    for key in ("minWidth", "maxWidth", "minHeight", "maxHeight"):
        val = node.get(key)
        if val is not None:
            result[key] = val

    fills = node.get("fills", [])
    parsed_fills = [f for f in (format_paint(p) for p in fills) if f]
    if parsed_fills:
        result["fills"] = parsed_fills

    strokes = node.get("strokes", [])
    parsed_strokes = [f for f in (format_paint(p) for p in strokes) if f]
    if parsed_strokes:
        result["strokes"] = parsed_strokes
        weight = node.get("strokeWeight")
        if weight:
            result["strokeWeight"] = weight
        result["strokeAlign"] = node.get("strokeAlign", "CENTER")
        stroke_cap = node.get("strokeCap")
        if stroke_cap and stroke_cap != "NONE":
            result["strokeCap"] = stroke_cap
        stroke_join = node.get("strokeJoin")
        if stroke_join and stroke_join != "MITER":
            result["strokeJoin"] = stroke_join
        if node.get("strokesIncludedInLayout"):
            result["strokesIncludedInLayout"] = True

    cr = node.get("cornerRadius")
    if cr:
        result["cornerRadius"] = cr
    per_corner = node.get("rectangleCornerRadii")
    if per_corner and per_corner != [cr, cr, cr, cr]:
        result["rectangleCornerRadii"] = per_corner
    corner_smoothing = node.get("cornerSmoothing")
    if corner_smoothing:
        result["cornerSmoothing"] = round(corner_smoothing, 3)

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
        layout_wrap = node.get("layoutWrap")
        if layout_wrap and layout_wrap != "NO_WRAP":
            result["layoutWrap"] = layout_wrap
            counter_spacing = node.get("counterAxisSpacing")
            if counter_spacing:
                result["counterAxisSpacing"] = counter_spacing
        result["layoutSizingHorizontal"] = node.get("layoutSizingHorizontal")
        result["layoutSizingVertical"] = node.get("layoutSizingVertical")
        if node.get("itemReverseZIndex"):
            result["itemReverseZIndex"] = True
        primary_sizing = node.get("primaryAxisSizingMode")
        if primary_sizing:
            result["primaryAxisSizingMode"] = primary_sizing

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
                    f"color={rgba_to_hex(c)} offset=({off.get('x', 0)},{off.get('y', 0)}) "
                    f"blur={e.get('radius', 0)} spread={e.get('spread', 0)}"
                )
            elif "BLUR" in etype:
                formatted.append(
                    f"{etype.lower().replace('_', ' ')}: radius={e.get('radius', 0)}"
                )
        if formatted:
            result["effects"] = formatted

    if node.get("type") == "TEXT":
        style = node.get("style", {})
        typo = {
            "fontFamily": style.get("fontFamily"),
            "fontWeight": style.get("fontWeight"),
            "fontSize": style.get("fontSize"),
            "italic": style.get("italic", False),
            "textAlignHorizontal": style.get("textAlignHorizontal"),
            "textAlignVertical": style.get("textAlignVertical"),
        }
        if style.get("lineHeightPx"):
            typo["lineHeightPx"] = style["lineHeightPx"]
        if style.get("letterSpacing"):
            typo["letterSpacing"] = style["letterSpacing"]
        if style.get("textCase") and style["textCase"] != "ORIGINAL":
            typo["textCase"] = style["textCase"]
        if style.get("textDecoration") and style["textDecoration"] != "NONE":
            typo["textDecoration"] = style["textDecoration"]
        if style.get("paragraphSpacing"):
            typo["paragraphSpacing"] = style["paragraphSpacing"]
        if style.get("paragraphIndent"):
            typo["paragraphIndent"] = style["paragraphIndent"]
        truncation = node.get("textTruncation")
        if truncation and truncation != "DISABLED":
            typo["textTruncation"] = truncation
            max_lines = node.get("maxLines")
            if max_lines:
                typo["maxLines"] = max_lines
        result["typography"] = typo
        chars = node.get("characters", "")
        result["characters"] = chars[:200] + ("…" if len(chars) > 200 else "")

    comp_id = node.get("componentId")
    if comp_id:
        result["componentId"] = comp_id
    comp_props = node.get("componentProperties")
    if comp_props:
        result["componentProperties"] = comp_props

    export_settings = node.get("exportSettings", [])
    if export_settings:
        result["exportSettings"] = [
            {
                "format": s.get("format"),
                "suffix": s.get("suffix", ""),
                "scale": s.get("constraint", {}).get("value", 1),
            }
            for s in export_settings
        ]

    # boundVariables: which property names are driven by design tokens/Variables
    # Variable IDs are not shown — too noisy; use /variables/local to resolve them
    bound_vars = node.get("boundVariables")
    if bound_vars:
        result["boundVariables"] = list(bound_vars.keys())

    children = node.get("children", [])
    if children:
        if depth >= max_depth:
            result["_children_truncated"] = len(children)
        else:
            simplified_children = [
                simplify_node(c, depth + 1, max_depth)
                for c in children
                if c is not None
            ]
            visible_children = [c for c in simplified_children if c is not None]
            if visible_children:
                result["children"] = visible_children

    return result


def render_node_markdown(node_data, file_name):
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

    dev_status = node.get("devStatus")
    if dev_status:
        lines.append(f"{prefix}- Dev status: {dev_status}")

    size = node.get("size")
    pos = node.get("position")
    if size or pos:
        if top_level:
            lines.append(f"{prefix}### Layout")
        if size:
            lines.append(f"{prefix}- Size: {size['width']} × {size['height']}px")
        if pos and not top_level:
            lines.append(f"{prefix}- Position: x={pos['x']}, y={pos['y']}")
    render_bounds = node.get("renderBounds")
    if render_bounds:
        lines.append(
            f"{prefix}- Render bounds: {render_bounds['width']} × {render_bounds['height']}px "
            f"(x={render_bounds['x']}, y={render_bounds['y']})"
        )

    rotation = node.get("rotation")
    if rotation:
        lines.append(f"{prefix}- Rotation: {rotation}°")

    layout_pos = node.get("layoutPositioning")
    if layout_pos:
        lines.append(f"{prefix}- Layout positioning: {layout_pos}")

    layout_align = node.get("layoutAlign")
    layout_grow = node.get("layoutGrow")
    if layout_align or layout_grow is not None:
        parts = []
        if layout_align:
            parts.append(f"align={layout_align}")
        if layout_grow:
            parts.append(f"grow={layout_grow}")
        lines.append(f"{prefix}- Layout (child): {', '.join(parts)}")

    constraints = node.get("constraints")
    if constraints:
        h = constraints.get("horizontal", "")
        v = constraints.get("vertical", "")
        lines.append(f"{prefix}- Constraints: horizontal={h}, vertical={v}")

    size_constraints = []
    for key in ("minWidth", "maxWidth", "minHeight", "maxHeight"):
        val = node.get(key)
        if val is not None:
            size_constraints.append(f"{key}={val}")
    if size_constraints:
        lines.append(f"{prefix}- Size constraints: {', '.join(size_constraints)}")

    layout = node.get("layoutMode")
    if layout:
        gap_str = f", gap: {node.get('itemSpacing', 0)}px"
        wrap = node.get("layoutWrap")
        wrap_str = f", wrap: {wrap}" if wrap else ""
        lines.append(f"{prefix}- Auto-layout: {layout}{gap_str}{wrap_str}")
        if wrap:
            counter_spacing = node.get("counterAxisSpacing")
            if counter_spacing:
                lines.append(f"{prefix}- Row gap: {counter_spacing}px")
        pt = node.get("paddingTop", 0)
        pr = node.get("paddingRight", 0)
        pb = node.get("paddingBottom", 0)
        pl = node.get("paddingLeft", 0)
        if any([pt, pr, pb, pl]):
            lines.append(
                f"{prefix}- Padding: top={pt} right={pr} bottom={pb} left={pl}"
            )
        h_sizing = node.get("layoutSizingHorizontal")
        v_sizing = node.get("layoutSizingVertical")
        if h_sizing or v_sizing:
            lines.append(
                f"{prefix}- Sizing: horizontal={h_sizing}, vertical={v_sizing}"
            )
        lines.append(
            f"{prefix}- Align (primary): {node.get('primaryAxisAlignItems')}, counter: {node.get('counterAxisAlignItems')}"
        )
        if node.get("itemReverseZIndex"):
            lines.append(f"{prefix}- Item reverse z-index: true")

    fills = node.get("fills")
    if fills:
        if top_level:
            lines.append(f"{prefix}### Colors")
        for fill in fills:
            lines.append(f"{prefix}- Fill: {fill}")

    strokes = node.get("strokes")
    if strokes:
        if top_level:
            lines.append(f"{prefix}### Borders")
        for stroke in strokes:
            weight = node.get("strokeWeight", "")
            align = node.get("strokeAlign", "")
            cap = node.get("strokeCap", "")
            join = node.get("strokeJoin", "")
            stroke_parts = [f"{stroke}", f"{weight}px", align]
            if cap:
                stroke_parts.append(f"cap={cap}")
            if join:
                stroke_parts.append(f"join={join}")
            lines.append(f"{prefix}- Stroke: {', '.join(stroke_parts)}")
        if node.get("strokesIncludedInLayout"):
            lines.append(f"{prefix}- Strokes included in layout (border-box)")

    cr = node.get("cornerRadius")
    if cr:
        if top_level and not strokes:
            lines.append(f"{prefix}### Borders")
        cs = node.get("cornerSmoothing")
        cs_str = f", smoothing: {cs}" if cs else ""
        lines.append(f"{prefix}- Corner radius: {cr}px{cs_str}")
    per_corner = node.get("rectangleCornerRadii")
    if per_corner:
        lines.append(f"{prefix}- Corner radii (TL TR BR BL): {per_corner}")

    opacity = node.get("opacity")
    if opacity is not None:
        lines.append(f"{prefix}- Opacity: {opacity}")

    blend = node.get("blendMode")
    if blend:
        lines.append(f"{prefix}- Blend mode: {blend}")

    if node.get("isMask"):
        lines.append(f"{prefix}- Is mask: true")

    effects = node.get("effects")
    if effects:
        if top_level:
            lines.append(f"{prefix}### Effects")
        for e in effects:
            lines.append(f"{prefix}- {e}")

    typo = node.get("typography")
    if typo:
        if top_level:
            lines.append(f"{prefix}### Typography")
        lines.append(
            f"{prefix}- Font: {typo.get('fontFamily')}, {typo.get('fontSize')}px, weight {typo.get('fontWeight')}"
        )
        style_parts = []
        if typo.get("italic"):
            style_parts.append("italic")
        if typo.get("textCase"):
            style_parts.append(f"case: {typo['textCase']}")
        if typo.get("textDecoration"):
            style_parts.append(f"decoration: {typo['textDecoration']}")
        if style_parts:
            lines.append(f"{prefix}- Style: {', '.join(style_parts)}")
        lh = typo.get("lineHeightPx")
        if lh:
            lines.append(f"{prefix}- Line height: {lh}px")
        ls = typo.get("letterSpacing")
        if ls:
            lines.append(f"{prefix}- Letter spacing: {ls}px")
        align_h = typo.get("textAlignHorizontal")
        align_v = typo.get("textAlignVertical")
        if align_h or align_v:
            align_str = f"{align_h or ''}"
            if align_v:
                align_str += f" / {align_v}" if align_h else align_v
            lines.append(f"{prefix}- Text align: {align_str}")
        if typo.get("paragraphSpacing"):
            lines.append(f"{prefix}- Paragraph spacing: {typo['paragraphSpacing']}px")
        if typo.get("paragraphIndent"):
            lines.append(f"{prefix}- Paragraph indent: {typo['paragraphIndent']}px")
        if typo.get("textTruncation"):
            max_l = typo.get("maxLines")
            trunc_str = f" (max {max_l} lines)" if max_l else ""
            lines.append(f"{prefix}- Truncation: {typo['textTruncation']}{trunc_str}")

    chars = node.get("characters")
    if chars:
        if top_level:
            lines.append(f"{prefix}### Content")
        lines.append(f'{prefix}- Text: "{chars}"')

    comp_id = node.get("componentId")
    if comp_id:
        lines.append(f"{prefix}- Component ID: {comp_id}")

    export_settings = node.get("exportSettings")
    if export_settings:
        exports = ", ".join(
            f"{s['format']}@{s['scale']}x{('/' + s['suffix']) if s.get('suffix') else ''}"
            for s in export_settings
        )
        lines.append(f"{prefix}- Export: {exports}")

    bound_vars = node.get("boundVariables")
    if bound_vars:
        lines.append(
            f"{prefix}- Bound variables (token fields): {', '.join(bound_vars)}"
        )

    trunc = node.get("_children_truncated")
    if trunc:
        lines.append(
            f"{prefix}- ... ({trunc} children truncated — use --depth to go deeper)"
        )
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
    lines.append(
        "To inspect a specific element, open the file in Figma, right-click a layer → 'Copy link to selection', then run this skill again with that URL."
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Figma design specs and output structured markdown."
    )
    parser.add_argument("url", help="Figma URL (design/file/proto)")
    parser.add_argument(
        "--depth", type=int, default=5, help="Max tree depth (default: 5)"
    )
    args = parser.parse_args()

    token = get_token()
    file_key, node_id = parse_figma_url(args.url)

    if node_id:
        data = figma_get(f"/v1/files/{file_key}/nodes", token, ids=node_id)
        nodes = data.get("nodes", {})
        node_entry = nodes.get(node_id)
        if node_entry is None:
            # Figma sometimes normalizes the node_id key differently; fall back to first entry
            node_entry = next(iter(nodes.values()), None) if nodes else None
        if node_entry is None:
            print(
                f"ERROR: Node '{node_id}' not found in file '{file_key}'.",
                file=sys.stderr,
            )
            print(
                "The node may be on a different page or the ID may be wrong.",
                file=sys.stderr,
            )
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
