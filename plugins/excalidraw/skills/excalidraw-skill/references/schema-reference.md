# Excalidraw Schema Reference

On-demand depth for the `excalidraw` skill. Read this when you need a copy-paste
starting point or the full catalogue of a property's values. The core generate-time
rules (binding, endpoints, sizing, arrow labels) live in `SKILL.md` — this file is
the long tail, not a replacement.

## Copy-paste element templates

All templates use descriptive string IDs and section-namespaced seeds (100xxx).
Swap colors from the palette in `SKILL.md`.

### File skeleton

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "claude-code",
  "elements": [],
  "appState": { "viewBackgroundColor": "#ffffff" }
}
```

### Rectangle component + bound label (the workhorse)

```json
{
  "id": "auth_service", "type": "rectangle",
  "x": 100, "y": 100, "width": 160, "height": 60, "angle": 0,
  "strokeColor": "#1e40af", "backgroundColor": "#dbeafe",
  "fillStyle": "solid", "strokeWidth": 2, "roughness": 0, "opacity": 100,
  "seed": 100001,
  "boundElements": [{ "id": "label_auth", "type": "text" }]
},
{
  "id": "label_auth", "type": "text", "text": "Auth Service",
  "fontSize": 20, "fontFamily": 2, "textAlign": "center", "verticalAlign": "middle",
  "strokeColor": "#1e293b", "seed": 100002,
  "containerId": "auth_service"
}
```

### Bound arrow between two shapes

Both shapes must also list this arrow id in their own `boundElements`.

```json
{
  "id": "arrow_gw_to_auth", "type": "arrow",
  "x": 260, "y": 130, "width": 200, "height": 0, "angle": 0,
  "strokeColor": "#475569", "backgroundColor": "transparent",
  "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
  "roughness": 0, "opacity": 100, "seed": 100010,
  "points": [[0, 0], [200, 0]],
  "startBinding": { "elementId": "api_gateway", "gap": 5, "focus": 0 },
  "endBinding":   { "elementId": "auth_service", "gap": 5, "focus": 0 }
}
```

### Arrow with a bound label (Yes/No, message names)

Label `width` must fit the **text**, never the arrow — a full-width label masks the whole line.

```json
{
  "id": "arrow_valid_yes", "type": "arrow",
  "x": 200, "y": 300, "width": 0, "height": 120,
  "points": [[0, 0], [0, 120]], "seed": 100020,
  "strokeColor": "#475569", "strokeWidth": 2, "roughness": 0, "opacity": 100,
  "boundElements": [{ "id": "lbl_yes", "type": "text" }]
},
{
  "id": "lbl_yes", "type": "text", "text": "Yes",
  "fontSize": 14, "width": 36, "fontFamily": 2,
  "strokeColor": "#1e293b", "seed": 100021,
  "containerId": "arrow_valid_yes"
}
```

### Start/end ellipse and decision diamond

```json
{ "id": "start", "type": "ellipse", "x": 60, "y": 40, "width": 140, "height": 70,
  "strokeColor": "#c2410c", "backgroundColor": "#fed7aa", "fillStyle": "solid",
  "strokeWidth": 2, "roughness": 0, "opacity": 100, "seed": 100030,
  "boundElements": [{ "id": "lbl_start", "type": "text" }] },
{ "id": "decide", "type": "diamond", "x": 60, "y": 260, "width": 160, "height": 100,
  "strokeColor": "#854d0e", "backgroundColor": "#fef9c3", "fillStyle": "solid",
  "strokeWidth": 2, "roughness": 0, "opacity": 100, "seed": 100031,
  "boundElements": [{ "id": "lbl_decide", "type": "text" }] }
```

### Swimlane zone + free-standing lane label

Zone text is a **separate** top-left text element, never bound to the rectangle.

```json
{ "id": "lane_customer", "type": "rectangle", "x": 40, "y": 40,
  "width": 1000, "height": 200, "strokeColor": "#475569",
  "backgroundColor": "#f1f5f9", "fillStyle": "solid", "strokeStyle": "dashed",
  "strokeWidth": 2, "roughness": 0, "opacity": 30, "seed": 100040,
  "boundElements": null },
{ "id": "lbl_lane_customer", "type": "text", "text": "Customer",
  "x": 56, "y": 52, "fontSize": 28, "fontFamily": 2,
  "strokeColor": "#334155", "seed": 100041, "containerId": null }
```

### Mind-map line connector (not an arrow)

```json
{ "id": "line_center_a", "type": "line",
  "x": 500, "y": 300, "width": 180, "height": -120,
  "points": [[0, 0], [180, -120]],
  "strokeColor": "#475569", "strokeWidth": 2, "roughness": 0,
  "opacity": 100, "seed": 100050 }
```

## Full property catalogue

Every value below is verified to render through Kroki and the local CLI.

| Property | Valid values | Notes |
|----------|--------------|-------|
| `fillStyle` | `"solid"`, `"hachure"`, `"cross-hatch"`, `"zigzag"` | `solid` for clean diagrams; the others are sketch textures |
| `strokeStyle` | `"solid"` (or omit), `"dashed"`, `"dotted"` | dashed = response/async, dotted = optional/weak |
| `fontFamily` | `1` (Virgil, hand-drawn), `2` (Helvetica), `3` (Cascadia, code) | `2` for technical diagrams |
| `textAlign` | `"left"`, `"center"`, `"right"` | `center` for contained labels |
| `verticalAlign` | `"top"`, `"middle"`, `"bottom"` | `middle` for contained labels |
| `roughness` | `0` (clean), `1` (hand-drawn), `2` (very sketchy) | default `0` |
| `strokeWidth` | `1` (thin), `2` (standard), `3` (bold) | use width for emphasis, not color noise |
| `roundness` | `null` (sharp), `{ "type": 2 }` (rounded/curved) | `type: 2` on arrows = curved routing |

### Arrowhead catalogue (`startArrowhead` / `endArrowhead`)

| Value | Use for |
|-------|---------|
| `null` | no head (lines, mind-map connectors, `startArrowhead` of a one-way arrow) |
| `"arrow"` | standard directed flow (default `endArrowhead`) |
| `"triangle"` | UML inheritance / generalization |
| `"diamond"` | UML composition |
| `"bar"` | UML aggregation, hard stop |
| `"dot"` / `"circle"` | endpoint markers, BPMN-ish |
| `"crowfoot_many"` | ER "many" cardinality |

Arrows default to `endArrowhead: "arrow"`, `startArrowhead: null` — omit both for a
standard one-way arrow.

## JSON field rules (recap)

- `boundElements`: use `null` when empty, never `[]`.
- `updated`: always `1`, never timestamps.
- Do NOT include: `frameId`, `index`, `versionNonce`, `rawText`.
- Arrow `points` always start at `[0, 0]`; the arrow's `x`/`y` position the first point.
- `seed`: positive integer, unique per element, namespaced by section (100xxx, 200xxx…).
- Unsupported element types: `image` (needs a `files` map + `fileId`), `frame`, `embeddable`.
