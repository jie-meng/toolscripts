# Figma REST API Reference

> **Official spec**: [github.com/figma/rest-api-spec](https://github.com/figma/rest-api-spec)  
> OpenAPI YAML: `openapi/openapi.yaml` · TypeScript types: `dist/api_types.ts`

Base URL: `https://api.figma.com`

**Authentication** (one of):
- `X-Figma-Token: <personal_access_token>` — Personal access token from Figma Settings → Security
- `Authorization: Bearer <oauth_token>` — OAuth2 token

---

## Endpoints

### Files

#### `GET /v1/files/:file_key`

Returns the complete document tree for a file.

**Query parameters**

| Parameter | Type | Description |
|---|---|---|
| `version` | string | Return a specific version ID |
| `ids` | string | Comma-separated node IDs to return (restricts tree to ancestors + specified nodes) |
| `depth` | integer | Traversal depth from root (1 = pages only, 2 = top-level frames, etc.) |
| `geometry` | `paths` | Adds `fillGeometry`, `strokeGeometry`, `relativeTransform`, and `size` to all nodes |
| `plugin_data` | string | Plugin IDs whose data should be included |
| `branch_data` | boolean | Include branch metadata |

**Response** (`GetFileResponse`)

```json
{
  "name": "My Design File",
  "lastModified": "2024-01-15T10:00:00Z",
  "thumbnailUrl": "https://...",
  "version": "1234567890",
  "document": { /* DOCUMENT node — see Node Types */ },
  "components": { "<nodeId>": { "key": "...", "name": "...", "description": "..." } },
  "componentSets": { "<nodeId>": { "key": "...", "name": "..." } },
  "styles": { "<nodeId>": { "key": "...", "name": "...", "styleType": "FILL|TEXT|EFFECT|GRID" } },
  "schemaVersion": 0,
  "mainFileKey": "..."
}
```

---

#### `GET /v1/files/:file_key/nodes`

Returns specific nodes (by ID) instead of the full tree. More efficient for targeted lookups.

**Query parameters**

| Parameter | Type | Description |
|---|---|---|
| `ids` | string | **Required.** Comma-separated node IDs |
| `version` | string | Specific version |
| `depth` | integer | Depth from each requested node |
| `geometry` | `paths` | Same as `/files` |
| `plugin_data` | string | Plugin IDs |

**Response**

```json
{
  "name": "My Design File",
  "nodes": {
    "1:2": {
      "document": { /* node object */ },
      "components": {},
      "componentSets": {},
      "schemaVersion": 0,
      "styles": {}
    },
    "3:4": null
  }
}
```

> Node values can be `null` if the ID doesn't exist in the file.

---

#### `GET /v1/files/:file_key/images`

Returns download URLs for all **image fills** (user-uploaded images) referenced in the file. Maps `imageRef` IDs to temporary CDN URLs.

**Response**

```json
{
  "error": false,
  "status": 200,
  "meta": {
    "images": {
      "<imageRef>": "https://s3.amazonaws.com/..."
    }
  }
}
```

URLs expire after **14 days**.

---

#### `GET /v1/images/:file_key`

**Renders** nodes as raster/vector images (not to be confused with `/files/:key/images`).

**Query parameters**

| Parameter | Type | Description |
|---|---|---|
| `ids` | string | **Required.** Comma-separated node IDs to render |
| `scale` | number | 0.01–4 (default 1) |
| `format` | `jpg\|png\|svg\|pdf` | Output format (default `png`) |
| `svg_include_id` | boolean | Include node IDs as SVG attributes |
| `svg_simplify_stroke` | boolean | Simplify strokes in SVG |
| `contents_only` | boolean | Crop to node contents, not bounding box |
| `use_absolute_bounds` | boolean | Use full bounding box even if empty space |
| `version` | string | Specific version |

**Response**

```json
{
  "err": null,
  "images": {
    "1:2": "https://s3.amazonaws.com/...",
    "3:4": null
  }
}
```

Rendered images expire after **30 days**. Max **32 megapixels** per image.

---

#### `GET /v1/files/:file_key/meta`

Returns file metadata without the full node tree. Lightweight alternative to `/files`.

**Response**

```json
{
  "name": "My File",
  "lastModified": "2024-01-15T10:00:00Z",
  "thumbnailUrl": "https://...",
  "version": "...",
  "role": "owner|editor|viewer",
  "editorType": "figma|figjam"
}
```

---

#### `GET /v1/files/:file_key/versions`

Returns the version history of a file.

**Response**

```json
{
  "versions": [
    {
      "id": "1234567890",
      "created_at": "2024-01-15T10:00:00Z",
      "label": "v2.0 — header redesign",
      "description": "...",
      "user": { "id": "...", "handle": "...", "img_url": "..." }
    }
  ],
  "pagination": { "cursor": { "before": 123, "after": 456 } }
}
```

---

### Components & Component Sets

#### `GET /v1/files/:file_key/components`

Returns published component metadata within a file.

**Response**

```json
{
  "error": false,
  "status": 200,
  "meta": {
    "components": [
      {
        "key": "abc123",
        "file_key": "...",
        "node_id": "1:2",
        "thumbnail_url": "https://...",
        "name": "Button/Primary",
        "description": "...",
        "created_at": "...",
        "updated_at": "...",
        "user": { "id": "...", "handle": "..." },
        "containing_frame": { "name": "...", "node_id": "..." }
      }
    ],
    "cursor": { "before": 0, "after": 1 }
  }
}
```

#### `GET /v1/components/:key`

Returns metadata for a single published component by its key (not node ID).

#### `GET /v1/teams/:team_id/components`

Paginated list of all published components across a team.

**Query parameters**: `page_size` (default 30, max 1000), `after` / `before` cursors.

#### `GET /v1/files/:file_key/component_sets`

Returns published component set (variant group) metadata within a file. Same response structure as `/components`.

#### `GET /v1/component_sets/:key`

Returns metadata for a single published component set.

#### `GET /v1/teams/:team_id/component_sets`

Paginated list of all published component sets across a team.

#### `GET /v1/files/:file_key/styles`

Returns published style metadata within a file.

**Response**: Same structure as `/components` but with `styleType`: `FILL`, `TEXT`, `EFFECT`, or `GRID`.

#### `GET /v1/styles/:key`

Returns metadata for a single published style.

#### `GET /v1/teams/:team_id/styles`

Paginated list of all published styles across a team.

---

### Variables (Enterprise only)

#### `GET /v1/files/:file_key/variables/local`

Returns all local variables (design tokens) and variable collections in a file.

**Response**

```json
{
  "status": 200,
  "error": false,
  "meta": {
    "variables": {
      "<variableId>": {
        "id": "VariableID:1:1",
        "name": "color/primary/500",
        "key": "...",
        "variableCollectionId": "...",
        "resolvedType": "COLOR|FLOAT|STRING|BOOLEAN",
        "valuesByMode": {
          "<modeId>": { "r": 0.2, "g": 0.4, "b": 1.0, "a": 1.0 }
        },
        "remote": false,
        "description": ""
      }
    },
    "variableCollections": {
      "<collectionId>": {
        "id": "...",
        "name": "Primitives",
        "modes": [{ "modeId": "...", "name": "Light" }, { "modeId": "...", "name": "Dark" }],
        "defaultModeId": "...",
        "remote": false
      }
    }
  }
}
```

#### `GET /v1/files/:file_key/variables/published`

Returns variables published to the team library (visible to other files).

#### `POST /v1/files/:file_key/variables`

Bulk create/update/delete variables and variable collections. Each item requires an `action` property (`CREATE`, `UPDATE`, or `DELETE`).

---

### Dev Resources

#### `GET /v1/files/:file_key/dev_resources`

External links (Jira, GitHub, Confluence, etc.) attached to nodes in Dev Mode.

| Parameter | Description |
|---|---|
| `node_ids` | Comma-separated node IDs — filter to resources on those nodes only |

**Response**

```json
{
  "dev_resources": [{
    "id": "...",
    "name": "Ticket #123",
    "url": "https://jira.example.com/...",
    "file_key": "...",
    "node_id": "1:2"
  }]
}
```

---

### Comments

#### `GET /v1/files/:file_key/comments`

Returns all comments on a file.

#### `POST /v1/files/:file_key/comments`

Posts a new comment. Body: `{ "message": "...", "client_meta": { "node_id": "1:2", "node_offset": { "x": 0, "y": 0 } } }`

#### `DELETE /v1/files/:file_key/comments/:comment_id`

Deletes a comment (must be the comment author).

---

### Teams & Projects

#### `GET /v1/teams/:team_id/projects`

Returns all projects in a team.

#### `GET /v1/projects/:project_id/files`

Returns all files in a project.

---

### Library Analytics (Enterprise)

Usage data for published library items. All endpoints are paginated with `cursor`.

| Endpoint | Description |
|---|---|
| `GET /v1/analytics/libraries/:file_key/component/actions` | Insert/detach actions for components |
| `GET /v1/analytics/libraries/:file_key/component/usages` | Usage counts per component |
| `GET /v1/analytics/libraries/:file_key/style/actions` | Apply/remove actions for styles |
| `GET /v1/analytics/libraries/:file_key/style/usages` | Usage counts per style |
| `GET /v1/analytics/libraries/:file_key/variable/actions` | Bind/unbind actions for variables |
| `GET /v1/analytics/libraries/:file_key/variable/usages` | Usage counts per variable |

---

### Webhooks (v2)

#### `GET /v2/webhooks`

List webhooks.

#### `POST /v2/webhooks`

Create a webhook. Body: `{ "event_type": "...", "team_id": "...", "endpoint": "https://...", "passcode": "..." }`

#### `GET /v2/webhooks/:webhook_id`

Single webhook.

#### `GET /v2/teams/:team_id/webhooks`

All webhooks for a team.

#### `GET /v2/webhooks/:webhook_id/requests`

Recent delivery attempts for a webhook.

---

### User

#### `GET /v1/me`

Returns the authenticated user's info: `{ "id", "email", "handle", "img_url" }`.

---

## Node Types

All nodes are composed of shared "traits". Properties are emitted only when non-default.

### Universal properties (all nodes)

| Property | Present | Description |
|---|---|---|
| `id` | ✅ always | Node ID (e.g. `"1:2"`) |
| `name` | ✅ always | Layer name |
| `type` | ✅ always | Node type enum |
| `visible` | omitted when `true` | Hidden layers |
| `locked` | optional | Layer lock state |
| `rotation` | optional | Rotation degrees (positive = clockwise) |
| `blendMode` | optional | See Blend Modes below |
| `opacity` | optional | 0–1, omitted when 1.0 |
| `isMask` | optional | Whether this layer is a clipping mask |
| `absoluteBoundingBox` | Rectangle\|null | Layout bounds in absolute canvas coords |
| `absoluteRenderBounds` | Rectangle\|null | Visual bounds incl. effect overflow (shadows, blur) |
| `constraints` | optional | `{ horizontal, vertical }` resize behavior |
| `layoutAlign` | optional | `INHERIT\|STRETCH\|MIN\|CENTER\|MAX` — child sizing in parent auto-layout |
| `layoutGrow` | optional | `0` or `1` — whether child fills remaining space (flex-grow) |
| `layoutPositioning` | optional | `AUTO` (default) or `ABSOLUTE` — taken out of auto-layout flow (CSS `position: absolute`) |
| `minWidth/maxWidth` | optional | Width constraints |
| `minHeight/maxHeight` | optional | Height constraints |
| `effects` | optional | Shadows and blurs |
| `exportSettings` | optional | Configured export formats for this node |
| `boundVariables` | optional | Maps property names to Variable aliases (design tokens) |
| `devStatus` | optional | `{ type: "NONE"\|"READY_FOR_DEV"\|"COMPLETED" }` |
| `interactions` | optional | Prototype triggers + actions array |
| `pluginData` | optional | Data written by a specific plugin |
| `sharedPluginData` | optional | Data shared across all plugins |

### Containers (FRAME, COMPONENT, COMPONENT_SET, INSTANCE)

| Property | Description |
|---|---|
| `children` | Child nodes |
| `clipsContent` | Whether content outside bounds is clipped |
| `fills`, `strokes` | Background and border paints |
| `strokeWeight` | Stroke width in px |
| `strokeAlign` | `INSIDE\|OUTSIDE\|CENTER` |
| `strokeCap` | `NONE\|ROUND\|SQUARE\|LINE_ARROW\|TRIANGLE_ARROW\|CIRCLE_FILLED\|DIAMOND_FILLED\|ARROW_LINES\|ARROW_EQUILATERAL` |
| `strokeJoin` | `MITER\|BEVEL\|ROUND` |
| `strokesIncludedInLayout` | `true` = CSS `box-sizing: border-box` |
| `cornerRadius` | Uniform border radius |
| `rectangleCornerRadii` | Per-corner `[TL, TR, BR, BL]` |
| `cornerSmoothing` | 0–1; 0.6 = iOS "squircle" |
| `layoutMode` | `NONE\|HORIZONTAL\|VERTICAL\|GRID` |
| `itemSpacing` | Gap between children (can be negative) |
| `counterAxisSpacing` | Gap between wrapped rows/columns (when `layoutWrap: WRAP`) |
| `paddingTop/Right/Bottom/Left` | Inner padding |
| `primaryAxisAlignItems` | `MIN\|CENTER\|MAX\|SPACE_BETWEEN` |
| `counterAxisAlignItems` | `MIN\|CENTER\|MAX\|BASELINE` |
| `primaryAxisSizingMode` | `FIXED\|AUTO` |
| `counterAxisSizingMode` | `FIXED\|AUTO` |
| `layoutSizingHorizontal` | `FIXED\|HUG\|FILL` |
| `layoutSizingVertical` | `FIXED\|HUG\|FILL` |
| `layoutWrap` | `NO_WRAP\|WRAP` |
| `itemReverseZIndex` | If `true`, first child drawn on top (reverses default z-order) |

INSTANCE additionally: `componentId`, `componentProperties`, `exposedInstances`  
COMPONENT/COMPONENT_SET additionally: `componentPropertyDefinitions`

### GROUP

`children` only. No fills. Bounds are derived from children.

### SECTION

`children`, `fills`, `sectionContentsHidden`, `devStatus`

### TEXT

| Property | Description |
|---|---|
| `characters` | Full text string |
| `style` | TypeStyle object (see below) |
| `characterStyleOverrides` | Array mapping char indices to `styleOverrideTable` keys |
| `styleOverrideTable` | Map of TypeStyle objects for mixed-style text spans |
| `textTruncation` | `DISABLED\|ENDING` (ellipsis on overflow) |
| `maxLines` | Max lines before truncation |
| `lineTypes` | Per-line type: `NONE\|ORDERED\|UNORDERED` |
| `lineIndentations` | Per-line indent levels |

### RECTANGLE

`fills`, `strokes`, `cornerRadius`, `rectangleCornerRadii`, `cornerSmoothing`

### ELLIPSE

`fills`, `strokes`, `arcData` (start/end/innerRadius angles for arcs/donuts)

### VECTOR, LINE, STAR, REGULAR_POLYGON

`fills`, `strokes`, `strokeCap`, `strokeJoin`, `strokeMiterAngle`  
With `geometry=paths`: `fillGeometry`, `strokeGeometry` (SVG path data)

### BOOLEAN_OPERATION

`children`, `booleanOperation`: `UNION\|INTERSECT\|SUBTRACT\|EXCLUDE`

### Other (FigJam)

`STICKY`, `SHAPE_WITH_TEXT`, `CONNECTOR`, `WIDGET`, `TABLE`, `TABLE_CELL`, `SLICE`

---

## Object Schemas

### Rectangle

```json
{ "x": 100.0, "y": 200.0, "width": 320.0, "height": 48.0 }
```

### Constraints

```json
{
  "horizontal": "LEFT|RIGHT|CENTER|SCALE|STRETCH",
  "vertical": "TOP|BOTTOM|CENTER|SCALE|STRETCH"
}
```

### Paint (fills / strokes)

All paint objects have `type`, `visible` (default `true`), and `opacity` (default 1.0).

| `type` | Additional fields |
|---|---|
| `SOLID` | `color` (RGBA) |
| `GRADIENT_LINEAR` | `gradientHandlePositions` (Vector[3]), `gradientStops` (ColorStop[]) |
| `GRADIENT_RADIAL` | Same as LINEAR |
| `GRADIENT_ANGULAR` | Same as LINEAR |
| `GRADIENT_DIAMOND` | Same as LINEAR |
| `IMAGE` | `imageRef` (string), `scaleMode` (`FILL\|FIT\|CROP\|TILE`), `imageTransform` (2×3 matrix) |
| `PATTERN` | `sourceNodeId`, `tileType`, `scalingFactor` |

**RGBA color:**

```json
{ "r": 0.2, "g": 0.4, "b": 1.0, "a": 1.0 }
```

**ColorStop:**

```json
{ "position": 0.0, "color": { "r": 0.2, "g": 0.4, "b": 1.0, "a": 1.0 } }
```

---

### TypeStyle (TEXT nodes — `node.style`)

| Property | Description |
|---|---|
| `fontFamily` | e.g. `"Inter"` |
| `fontWeight` | 100–900 |
| `fontSize` | px |
| `italic` | boolean |
| `letterSpacing` | px (can be negative) |
| `lineHeightPx` | px |
| `lineHeightPercent` | % of font size |
| `lineHeightUnit` | `PIXELS\|FONT_SIZE_%\|INTRINSIC_%` |
| `textAlignHorizontal` | `LEFT\|RIGHT\|CENTER\|JUSTIFIED` |
| `textAlignVertical` | `TOP\|CENTER\|BOTTOM` |
| `textCase` | `ORIGINAL\|UPPER\|LOWER\|TITLE\|SMALL_CAPS` |
| `textDecoration` | `NONE\|STRIKETHROUGH\|UNDERLINE` |
| `paragraphSpacing` | px between paragraphs |
| `paragraphIndent` | px first-line indent |
| `hyperlink` | `{ type: "URL"\|"NODE", url?: string, nodeID?: string }` |

---

### Effect

| `type` | Fields |
|---|---|
| `DROP_SHADOW` | `color` (RGBA), `offset` (Vector), `radius` (blur), `spread`, `visible`, `blendMode` |
| `INNER_SHADOW` | Same as DROP_SHADOW |
| `LAYER_BLUR` | `radius`, `visible` |
| `BACKGROUND_BLUR` | `radius`, `visible` |

---

### ExportSetting

```json
{
  "suffix": "@2x",
  "format": "PNG|JPG|SVG|PDF",
  "constraint": { "type": "SCALE|WIDTH|HEIGHT", "value": 2.0 }
}
```

---

### Blend Modes

`PASS_THROUGH` (groups), `NORMAL`, `DARKEN`, `MULTIPLY`, `LINEAR_BURN`, `COLOR_BURN`, `LIGHTEN`, `SCREEN`, `LINEAR_DODGE`, `COLOR_DODGE`, `OVERLAY`, `SOFT_LIGHT`, `HARD_LIGHT`, `DIFFERENCE`, `EXCLUSION`, `HUE`, `SATURATION`, `COLOR`, `LUMINOSITY`

---

### Auto-layout properties (FRAME with `layoutMode`)

| Property | Values | Description |
|---|---|---|
| `layoutMode` | `HORIZONTAL\|VERTICAL\|GRID` | Enables auto-layout |
| `itemSpacing` | number | Gap between children (can be negative) |
| `counterAxisSpacing` | number | Gap between wrapped rows/columns (`layoutWrap: WRAP` only) |
| `paddingTop/Right/Bottom/Left` | number | Inner padding |
| `primaryAxisAlignItems` | `MIN\|CENTER\|MAX\|SPACE_BETWEEN` | Main axis alignment |
| `counterAxisAlignItems` | `MIN\|CENTER\|MAX\|BASELINE` | Cross axis alignment |
| `primaryAxisSizingMode` | `FIXED\|AUTO` | Whether main axis is fixed or hugs content |
| `counterAxisSizingMode` | `FIXED\|AUTO` | Whether cross axis is fixed or hugs content |
| `layoutSizingHorizontal` | `FIXED\|HUG\|FILL` | Width behavior |
| `layoutSizingVertical` | `FIXED\|HUG\|FILL` | Height behavior |
| `layoutWrap` | `NO_WRAP\|WRAP` | Flex-wrap (multi-line) |
| `itemReverseZIndex` | boolean | First child drawn on top if `true` |
| `strokesIncludedInLayout` | boolean | `box-sizing: border-box` behavior |
| `clipsContent` | boolean | Whether content is clipped at frame bounds |

---

## Rate Limits

Updated November 2025. Limits are per-minute per token (or per-month for Viewer seats on Tier 1).

| Tier | Endpoints | Developer seat |
|---|---|---|
| **Tier 1** | GET /files, GET /files/nodes | 10–20/min (Professional–Enterprise) |
| **Tier 2** | Metadata, components, styles | 25–100/min |
| **Tier 3** | Comments, images | 50–150/min |

**Pagination**: Use `page_size` (max 1000) + `cursor` (`before`/`after`) for list endpoints.

---

## `geometry=paths` parameter

When passed to `/files` or `/files/nodes`, adds the following to every node:

| Field | Description |
|---|---|
| `size` | `{ "x": width, "y": height }` — explicit dimensions (distinct from bounding box) |
| `relativeTransform` | 2×3 affine transform matrix relative to parent |
| `fillGeometry` | Array of SVG-like path objects for fills |
| `strokeGeometry` | Array of SVG-like path objects for strokes |
| `fillOverrideTable` | Per-region fill overrides (for complex vector shapes) |

Use this when you need exact path data for SVG generation or rotation-aware dimensions. Omit it otherwise — it significantly increases response size.
