---
name: tldraw-skill
description: Use when user requests diagrams, flowcharts, architecture charts, or visualizations. Also use proactively when explaining systems with 3+ components, complex data flows, or relationships that benefit from visual representation. Generates .tldr JSON files and exports to PNG/SVG locally using @kitschpatrol/tldraw-cli.
license: MIT
homepage: https://github.com/Agents365-ai/tldraw-skill
compatibility: Requires Node.js + @kitschpatrol/tldraw-cli on PATH (macOS/Linux/Windows). Self-check step requires a vision-enabled model (e.g., Claude Sonnet/Opus); gracefully skipped if unavailable.
platforms: [macos, linux, windows]
metadata: {"openclaw":{"requires":{"bins":["tldraw"]},"emoji":"📝","os":["darwin","linux","win32"],"install":[{"id":"npm-tldraw","kind":"npm","package":"@kitschpatrol/tldraw-cli","global":true,"bins":["tldraw"],"label":"Install tldraw-cli via npm"}]},"hermes":{"tags":["tldraw","diagram","flowchart","architecture","whiteboard","visualization"],"category":"design","requires_tools":["tldraw"],"related_skills":["drawio","mermaid","excalidraw","plantuml"]},"author":"Agents365-ai","version":"1.1.0"}
---

# tldraw Whiteboard Diagrams

## Overview

Generate modern whiteboard-style diagrams as `.tldr` JSON files and export to PNG/SVG using `@kitschpatrol/tldraw-cli`. tldraw produces clean hand-drawn aesthetic diagrams with rich shape libraries and smooth arrow routing — well-suited for casual or whiteboard-style visualizations.

**Format:** `.tldr` JSON
**Export:** PNG, SVG (via `@kitschpatrol/tldraw-cli`)
**Aesthetic:** Hand-drawn whiteboard style by default; switchable to clean fonts via `font` prop.

## When to Use

**Explicit triggers:** user says "diagram", "flowchart", "draw", "visualize", "whiteboard diagram", "tldraw diagram", "architecture diagram", "sketch this out".

**Proactive triggers:**
- Explaining a system with 3+ interacting components
- Describing a multi-step process, data flow, or pipeline
- Showing relationships between services/modules
- Architecture overviews, sequence flows, decision trees, ML model layers

**Skip when:** a simple list or table suffices, the user wants a polished business-presentation diagram (prefer drawio-skill), or the user is in a quick Q&A flow.

## Prerequisites

```bash
# Install tldraw-cli
npm install -g @kitschpatrol/tldraw-cli

# Verify
tldraw --version
```

Works identically on macOS, Windows, and Linux — no extra setup required.

## Workflow

Before starting, assess whether the user's request is specific enough. If key details are missing, ask 1-3 focused questions:
- **Diagram type** — which preset? (Architecture, Flowchart, Sequence, ML/DL, ERD, UML, or general)
- **Output format** — PNG (default), SVG?
- **Output location** — default is the user's working dir; honor any explicit path the user gives (e.g. "put it in `./artifacts/`"). Don't ask if they didn't mention one.
- **Scope/fidelity** — how many components? Any specific technologies or labels?

Skip clarification if the request already specifies these details or is clearly simple (e.g., "draw a flowchart of X").

0. **Update check (notify, don't pull)** — first use per conversation. Throttle to once per 24 h via `<this-skill-dir>/.last_update`; never mutate the skill directory without explicit user consent.

   - If `.last_update` exists and is <24 h old, skip this step entirely.
   - Otherwise, fetch the latest tag from upstream:
     ```bash
     git -C <this-skill-dir> ls-remote --tags origin 'v*' 2>/dev/null \
       | awk '{print $2}' | sed 's|refs/tags/||' | sort -V | tail -1
     ```
   - Compare with this skill's `metadata.version` from the frontmatter. If the upstream tag is strictly newer (semver), tell the user one line and ask:
     > "A newer version of this skill is available: vX.Y.Z → vA.B.C. Want me to `git pull`?"

     If they say yes, run `git -C <this-skill-dir> pull --ff-only`. Refresh `.last_update` either way so the prompt doesn't repeat for 24 hours.
   - If upstream is the same or older, refresh `.last_update` silently and continue.
   - On any failure (offline, not a git checkout — e.g. ClawHub-installed copy, read-only path, no permission), swallow the error silently and continue with the user's task. Do not mention the failure.

1. **Check deps** — verify `tldraw --version` succeeds; if missing, run `npm install -g @kitschpatrol/tldraw-cli`.
2. **Plan** — identify shapes (geo type per node), connections (arrows with source/target), and layout (TB or LR, group by tier/role). Sketch a coordinate grid before writing JSON.
3. **Generate** — write the `.tldr` JSON file. Default output dir is the user's working dir; if the user specified a path or directory (e.g. `./artifacts/`), `mkdir -p` it first and write there. Apply the same dir choice to PNG/SVG exports in steps 4 and 7.
4. **Export draft** — run CLI to produce a PNG for preview.
5. **Self-check** — use the agent's built-in vision capability to read the exported PNG, catch obvious issues, auto-fix before showing the user (requires a vision-enabled model such as Claude Sonnet/Opus). If vision is unavailable, skip this step.
6. **Review loop** — show image to user, collect feedback, apply targeted JSON edits, re-export, repeat until approved.
7. **Final export** — export the approved version to all requested formats; report file paths for both the `.tldr` source and exported image(s).

### Step 5: Self-Check

After exporting the draft PNG, use the agent's vision capability (e.g., Claude's image input) to read the image and check for these issues before showing the user. If the agent does not support vision, skip self-check and show the PNG directly:

| Check | What to look for | Auto-fix action |
|-------|-----------------|-----------------|
| Overlapping shapes | Two or more shapes stacked on top of each other | Shift shapes apart by ≥200px |
| Clipped labels | Text cut off at shape boundaries | Increase shape `w`/`h` to fit label |
| Missing arrows | Arrows that don't visually connect to shapes | Verify `boundShapeId` matches an existing shape's id |
| Off-canvas shapes | Shapes at negative coordinates or far from the main group | Move to positive coordinates near the cluster |
| Arrow-shape overlap | An arrow visually crosses through an unrelated shape | Adjust `bend` value or move endpoints to a different `normalizedAnchor` side |
| Stacked arrows | Multiple arrows overlap each other on the same path | Distribute `normalizedAnchor` across the shape perimeter (use different x/y values) |

- Max **2 self-check rounds** — if issues remain after 2 fixes, show the user anyway.
- Re-export after each fix and re-read the new PNG.

### Step 6: Review Loop

After self-check, show the exported image and ask the user for feedback.

**Targeted edit rules** — for each type of feedback, apply the minimal JSON change:

| User request | JSON edit action |
|-------------|-----------------|
| Change color of X | Find shape by `props.text` matching X, update `props.color` |
| Add a new node | Append a new shape record with next available index, position near related nodes |
| Remove a node | Delete the shape record and any arrow records bound to it |
| Move shape X | Update the shape's `x`/`y` fields |
| Resize shape X | Update `props.w`/`props.h` |
| Add arrow from A to B | Append a new arrow record binding to A and B's shape ids |
| Change label text | Update `props.text` on the matching shape or arrow |
| Change layout direction | **Full regeneration** — replan the grid and rebuild |

**Rules:**
- For single-element changes: edit the existing JSON in place — preserves layout tuning from prior iterations.
- For layout-wide changes (e.g., swap LR↔TB, "start over"): regenerate full JSON.
- Overwrite the same `{name}.png` each iteration — do not create `v1`, `v2`, `v3` files.
- After applying edits, re-export and show the updated image.
- Loop continues until user says approved / done / LGTM.
- **Safety valve:** after 5 iteration rounds, suggest the user open the `.tldr` file in tldraw.com or the desktop app for fine-grained adjustments.

---

## File Format

### Complete .tldr Skeleton

```json
{
  "tldrawFileFormatVersion": 1,
  "schema": {
    "schemaVersion": 1,
    "storeVersion": 4,
    "recordVersions": {
      "asset": {"version": 1, "subTypeKey": "type", "subTypeVersions": {"image": 2, "video": 2, "bookmark": 0}},
      "camera": {"version": 1},
      "document": {"version": 2},
      "instance": {"version": 17},
      "instance_page_state": {"version": 3},
      "page": {"version": 1},
      "shape": {"version": 3, "subTypeKey": "type", "subTypeVersions": {"group": 0, "embed": 4, "bookmark": 1, "image": 2, "text": 1, "draw": 1, "geo": 7, "line": 0, "note": 4, "frame": 0, "arrow": 1, "highlight": 0, "video": 1}},
      "instance_presence": {"version": 4},
      "pointer": {"version": 1}
    }
  },
  "records": [
    {"id": "document:document", "typeName": "document", "gridSize": 10, "name": "", "meta": {}},
    {"id": "page:page1", "typeName": "page", "name": "Page 1", "index": "a1", "meta": {}}
    /* shapes and arrows go here */
  ]
}
```

**Critical rules:**
- `document:document` and `page:page1` records are ALWAYS required.
- All shapes go in the `records` array after the page record.
- All shapes have `"parentId": "page:page1"`.
- Shape IDs use format `"shape:xxx"` with unique suffix (e.g., `"shape:s1"`, `"shape:a1"`).
- `index` values MUST start with `"a"` followed by digits or uppercase letters: `"a1"`, `"a2"`, ..., `"a9"`, `"aA"`, `"aB"`, ..., `"aZ"`, `"a10"`, etc.
- **Never use `"b1"`, `"c1"` etc. as indices** — only `"a*"` format is valid for shapes.

---

## Geo Shape Record

```json
{
  "id": "shape:s1",
  "typeName": "shape",
  "type": "geo",
  "parentId": "page:page1",
  "index": "a1",
  "x": 100,
  "y": 100,
  "rotation": 0,
  "isLocked": false,
  "opacity": 1,
  "meta": {},
  "props": {
    "w": 180,
    "h": 60,
    "geo": "rectangle",
    "color": "blue",
    "labelColor": "black",
    "fill": "semi",
    "dash": "draw",
    "size": "m",
    "font": "draw",
    "text": "API Gateway",
    "align": "middle",
    "verticalAlign": "middle",
    "growY": 0,
    "url": ""
  }
}
```

### Geo Types

| `geo` value | Use for |
|-------------|---------|
| `rectangle` | services, modules, components |
| `ellipse` | databases, start/end nodes |
| `diamond` | decision points |
| `cloud` | external services, infrastructure |
| `hexagon` | event hubs, message buses |
| `triangle` | gateways, load balancers |
| `star` | highlights, key features |

### Color Palette

| `color` | Use for |
|---------|---------|
| `blue` | clients, core services |
| `green` | success, databases, storage |
| `orange` | queues, event buses, warnings |
| `red` | external APIs, errors, alerts |
| `light-red` | soft alerts, secondary warnings |
| `violet` | gateways, security, auth |
| `yellow` | decisions, caches |
| `grey` | neutral, background, legacy |
| `light-blue` | secondary services, metadata |
| `black` | titles, emphasis |

### Style Options

| Property | Values | Notes |
|----------|--------|-------|
| `fill` | `semi`, `solid`, `none`, `pattern` | `semi` = tinted fill (recommended) |
| `dash` | `draw`, `solid`, `dashed`, `dotted` | `draw` = hand-drawn default |
| `size` | `s`, `m`, `l`, `xl` | `m` = default |
| `font` | `draw`, `sans`, `serif`, `mono` | `draw` = default whiteboard style |

---

## Arrow Record

```json
{
  "id": "shape:a1",
  "typeName": "shape",
  "type": "arrow",
  "parentId": "page:page1",
  "index": "aG",
  "x": 0,
  "y": 0,
  "rotation": 0,
  "isLocked": false,
  "opacity": 1,
  "meta": {},
  "props": {
    "dash": "draw",
    "size": "m",
    "fill": "none",
    "color": "black",
    "labelColor": "black",
    "bend": 0,
    "start": {
      "type": "binding",
      "boundShapeId": "shape:s1",
      "normalizedAnchor": {"x": 0.5, "y": 1},
      "isExact": false
    },
    "end": {
      "type": "binding",
      "boundShapeId": "shape:s2",
      "normalizedAnchor": {"x": 0.5, "y": 0},
      "isExact": false
    },
    "arrowheadStart": "none",
    "arrowheadEnd": "arrow",
    "text": "",
    "font": "draw"
  }
}
```

### Arrow Connection Rules

- Arrow record `x` and `y` are always `0, 0`.
- Use `"type": "binding"` with `boundShapeId` to connect to a specific shape.
- `normalizedAnchor` specifies WHERE on the target shape the arrow connects (0–1 range):
  - `{x: 0.5, y: 0}` = top center
  - `{x: 0.5, y: 1}` = bottom center
  - `{x: 0, y: 0.5}` = left center
  - `{x: 1, y: 0.5}` = right center
  - `{x: 0.5, y: 0.5}` = center
- Add `"text": "label"` in arrow props for labeled connections.
- Use `"bend": 20` (or `-20`) for slight curves to avoid overlap with other arrows.
- For dashed/dotted arrows (e.g., async flows, optional links), set `"dash": "dashed"` or `"dotted"`.

### Distributing Arrows on a Shape

When multiple arrows connect to the same shape, assign different `normalizedAnchor` points to prevent stacking:

| Position | x | y | Use when |
|----------|---|---|----------|
| Top center | 0.5 | 0 | connecting to node above |
| Top-left | 0.25 | 0 | 2nd connection from top |
| Top-right | 0.75 | 0 | 3rd connection from top |
| Right center | 1 | 0.5 | connecting to node on right |
| Bottom center | 0.5 | 1 | connecting to node below |
| Left center | 0 | 0.5 | connecting to node on left |

**Rule:** if a shape has N connections on one side, space them evenly (e.g., 3 connections on bottom → x = 0.25, 0.5, 0.75).

---

## Index Ordering Rules

Indices control z-order (stacking). Use this sequence:
```
a1, a2, a3, a4, a5, a6, a7, a8, a9,
aA, aB, aC, aD, aE, aF, aG, aH, aI, aJ, aK, aL, aM,
aN, aO, aP, aQ, aR, aS, aT, aU, aV, aW, aX, aY, aZ
```
- Geo shapes first: `a1` through `aF` (or as many as needed).
- Arrow shapes after: `aG`, `aH`, etc.
- Every shape must have a **unique** index.

---

## Layout Tips

**Spacing — scale with complexity:**

| Diagram complexity | Nodes | Horizontal gap | Vertical gap |
|-------------------|-------|----------------|--------------|
| Simple | ≤5 | 200px | 150px |
| Medium | 6–10 | 280px | 200px |
| Complex | >10 | 350px | 250px |

**Routing corridors:** between shape rows/columns, leave an extra ~80px empty corridor where arrows can route without crossing other shapes. Never place a shape in a gap that arrows need to traverse.

**Grid alignment:** snap all `x`, `y`, `w`, `h` values to **multiples of 10** — this matches tldraw's default `gridSize: 10` and makes manual editing easier.

**General rules:**
- Plan the grid before assigning x/y coordinates — sketch node positions mentally first.
- Group related nodes in the same horizontal or vertical band.
- Place heavily-connected "hub" nodes centrally so arrows radiate outward instead of crossing.
- For wide shapes (like an API Gateway spanning multiple downstream services), set `w` to cover the full span.
- Center-align a child node under its parent (same center x) to avoid diagonal routing.
- **Event bus pattern**: place the bus (hexagon) in the **center of the service row**, not below — services on either side reach it with short horizontal arrows (`normalizedAnchor.x = 1` left side, `0` right side), eliminating crossings.
- Horizontal connections never cross vertical nodes in the same row; use them for peer-to-peer and publish connections.

**Avoiding arrow-shape overlap:**
- Before finalizing coordinates, trace each arrow path mentally — if it must cross an unrelated shape, either move the shape or use `bend` to curve around.
- For tree/hierarchical layouts: assign nodes to layers (rows), connect only between adjacent layers to minimize crossings.
- For star/hub layouts: place the hub center, satellites around it — arrows stay short and radial.

---

## Diagram Type Presets

When the user requests a specific diagram type, apply the matching preset below for shapes, colors, and layout conventions.

### Architecture Diagram

| Element | `geo` | `color` | Notes |
|---------|-------|---------|-------|
| Client (web/mobile) | `rectangle` | `blue` | Top row, label by client type |
| Service / module | `rectangle` | `blue` | Mid rows, group by tier |
| Database | `ellipse` | `green` | Bottom row, one per service |
| Cache | `ellipse` | `yellow` | Sits beside its owning service |
| Queue / event bus | `hexagon` | `orange` | **Center of service row** for hub pattern |
| Gateway / load balancer | `triangle` | `violet` | Above services |
| External API | `cloud` | `red` | Edge of canvas, dashed arrows in |
| Auth / security | `rectangle` | `violet` | Often near gateway |

**Layout:** TB or LR by tier count; ≥4 tiers → TB. Hub nodes centered. Spacing scales with complexity (see table above).

### Flowchart

| Element | `geo` | `color` | Notes |
|---------|-------|---------|-------|
| Start / End | `ellipse` | `green` | Always at top and bottom |
| Process step | `rectangle` | `blue` | Default action box |
| Decision | `diamond` | `yellow` | Always label outgoing arrows (Yes / No) |
| I/O | `rectangle` (with `dash: dashed`) | `orange` | Distinguish from process via dashed border |
| Subprocess | `rectangle` | `violet` | Indicates a callable sub-flow |

**Layout:** TB, ~200px vertical gap. Decisions branch left/right, then merge back to center. Always label decision branches in the arrow's `props.text`.

### Sequence Diagram

tldraw doesn't have native lifeline shapes. Approximate with:

| Element | `geo` | `color` | Notes |
|---------|-------|---------|-------|
| Actor / object header | `rectangle` | `blue` | Top of column |
| Lifeline | `rectangle` (`w: 2`, `fill: solid`, `color: grey`) | `grey` | Thin vertical line under each actor header |
| Sync message | arrow with `arrowheadEnd: arrow` | `black` | Solid horizontal arrow |
| Async message | arrow with `dash: dashed` | `black` | Dashed horizontal arrow |
| Return message | arrow with `dash: dashed`, `color: grey` | `grey` | Grey dashed |

**Layout:** LR for actors (200–280px apart), TB for time. Each message is a horizontal arrow between two lifelines at increasing `y`.

### ML / Deep Learning Model Diagram

For neural network architecture diagrams — useful for paper figures and explainers.

| Element | `geo` | `color` | Notes |
|---------|-------|---------|-------|
| Input / Output | `rectangle` | `green` | Top and bottom of stack |
| Conv / Pooling | `rectangle` | `blue` | Standard layer block |
| Attention / Transformer | `rectangle` | `violet` | Distinct color for self-attention blocks |
| RNN / LSTM / GRU | `rectangle` | `yellow` | Recurrent layers |
| FC / Linear | `rectangle` | `orange` | Dense projection layers |
| Loss / Activation | `rectangle` | `red` | Final loss / softmax / activation |
| Skip connection | arrow with `bend: 30`, `dash: dashed` | `grey` | Curved dashed bypass |

**Tensor shape annotation:** include the dimensions in `props.text` on a second line. tldraw renders `\n` literally inside JSON strings, so use a real newline (the JSON encoder will write `\n`):

```
"text": "Conv2D\n(B, 64, 32, 32)"
```

**Layout:** TB (data flows top → bottom), layers ~150px apart. Skip connections curve around the main stack.

### ER Diagram (ERD)

tldraw lacks native table/row shapes. Approximate each entity as a tall rectangle with multi-line text.

| Element | `geo` | `color` | Notes |
|---------|-------|---------|-------|
| Entity | `rectangle` (`fill: solid`, `color: light-blue`) | `light-blue` | Title + columns as one multi-line text label |
| Column list | embedded in `props.text` with `\n` between rows | — | Mark PK with `*` prefix, FK with `>` |
| Relationship | arrow with `arrowheadStart: arrow`, `arrowheadEnd: arrow` | `black` | Both ends arrowed for many-to-many |
| Optional / weak relationship | arrow with `dash: dashed` | `grey` | Dashed for optional FK |

Label the arrow with cardinality (e.g., `1..*`, `0..1`) via `props.text`.

**Layout:** TB or grid; entities spaced ≥300px apart to leave room for column lists.

### UML Class Diagram

| Element | `geo` | `color` | Notes |
|---------|-------|---------|-------|
| Class | `rectangle` (`fill: solid`, `color: light-blue`) | `light-blue` | Title + attributes + methods as one multi-line `text` |
| Inheritance | arrow with `arrowheadEnd: triangle` (open) | `black` | Use a single arrow shape; tldraw doesn't natively render hollow triangles, so suggest user open in editor for true UML notation if needed |
| Composition | arrow with `bend: 0`, label `◆` in `text` | `black` | Add diamond glyph in arrow text as a workaround |
| Association | arrow with `arrowheadEnd: arrow` | `black` | Standard arrow |

**Note:** tldraw's arrowheads are limited compared to UML — for strict UML class diagrams, drawio-skill (separate skill) is a better fit. Use this preset for sketches and high-level explainers.

**Layout:** TB, classes ~250px apart, interfaces above implementations.

---

## Export Commands

```bash
# Check CLI version
tldraw --version

# PNG at 2x scale (recommended) — outputs diagram.png in ./
tldraw export diagram.tldr -f png --scale 2 -o ./

# SVG — outputs diagram.svg in ./
tldraw export diagram.tldr -f svg -o ./

# Transparent background
tldraw export diagram.tldr -f png --scale 2 --transparent -o ./

# Dark theme
tldraw export diagram.tldr -f png --scale 2 --dark -o ./

# Custom output directory (e.g. CI artifacts dir) — create if missing, then export there
mkdir -p ./artifacts && tldraw export diagram.tldr -f png --scale 2 -o ./artifacts/
```

**Note:** `-o` is an output **directory**, not a file path. The output file is named after the input file (`diagram.tldr` → `diagram.png`).

### Auto-launch after export

Offer to open the `.tldr` file in the user's default tldraw viewer/editor:

| OS | Command |
|----|---------|
| macOS | `open diagram.tldr` |
| Linux | `xdg-open diagram.tldr` |
| Windows | `start diagram.tldr` |

Or upload to https://tldraw.com (drag-and-drop the `.tldr` file) for browser editing.

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| `tldraw` command not found | Run `npm install -g @kitschpatrol/tldraw-cli` |
| `invalidRecords` on export | Check: index values must start with `a` (e.g., `a1`, `aA`) — never `b1`, `c1` |
| Blank/empty export | Verify `document:document` and `page:page1` records are present |
| Output file not found | `-o` is a directory; file name matches input: `tldraw export foo.tldr -o ./` → `./foo.png` |
| Arrow doesn't appear | Use `"type": "binding"` with `boundShapeId`; set arrow `x`/`y` to `0,0` |
| Shapes overlap | Plan a 200px+ grid before assigning x/y; scale spacing with complexity |
| Text not visible | Check `props.text` is set; if `fill: "none"`, ensure text color contrasts |
| Index collision | All shapes must have unique `index` values |
| Shape ID clash | Use unique IDs: `"shape:s1"`, `"shape:s2"`, `"shape:a1"`, etc. |
| Export fails | Ensure the `.tldr` file is valid JSON: `python3 -m json.tool file.tldr > /dev/null` |
| Multi-line label | Use a real newline character inside the JSON string (`"text": "Line1\nLine2"`); tldraw respects `\n` |
| Arrow crosses shape | Use `bend` to curve around, or move endpoint to a different `normalizedAnchor` |
| Iteration loop never ends | After 5 rounds, suggest the user open `.tldr` in tldraw.com for fine-tuning |

---

## Fallback Chain

When tools are unavailable, degrade gracefully:

| Scenario | Behavior |
|----------|----------|
| `tldraw-cli` missing | Generate `.tldr` JSON only; instruct user to drag-and-drop into https://tldraw.com or install the CLI |
| Vision unavailable for self-check | Skip self-check (step 5); proceed directly to showing user the exported PNG |
| Export fails | Validate JSON with `python3 -m json.tool`; deliver the `.tldr` file and suggest opening in tldraw.com |
