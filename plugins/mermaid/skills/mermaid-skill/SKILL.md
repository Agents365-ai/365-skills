---
name: mermaid-skill
description: Generate Mermaid diagrams (.mmd) and export to PNG/SVG/PDF using mmdc CLI or Kroki API. USE THIS SKILL when user mentions diagram, flowchart, sequence diagram, class diagram, ER diagram, state machine, architecture, visualize, git graph, 画图, 架构图, 流程图, 时序图, 类图, ER图, 甘特图, 状态机. PROACTIVELY USE when explaining ANY system with 3+ components, API flows, authentication sequences, class hierarchies, database schemas, or state machines. Supports 17+ diagram types with fully automatic layout.
homepage: https://github.com/Agents365-ai/creating-mermaid-diagrams
version: 1.3.0
---

# Mermaid Diagrams

Generate `.mmd` text files and export to PNG/SVG/PDF using `mmdc` (local) or Kroki API (no install).

**Key advantage:** Text-based syntax with **fully automatic layout** — no x/y coordinates needed.

## When to use / when NOT to use

**Use this skill for:** diagrams-as-code with automatic layout (flowchart, sequence, class, state, ER, gantt, mindmap, architecture) — text source that lives in git and embeds in Markdown.

**Do NOT use it — route elsewhere — for:**

- Pixel-precise placement, custom layout, branded icons, or heavy styling → **drawio**.
- A hand-drawn / sketchy aesthetic → **excalidraw** or **tldraw**.
- A freeform whiteboard or freehand strokes → **tldraw**.
- Strict, conventional UML notation → **plantuml**.

## Prerequisites

**Option A: Local (mmdc)** — also needs a headless Chrome (mmdc renders via Puppeteer)

```bash
npm install -g @mermaid-js/mermaid-cli
npx puppeteer browsers install chrome-headless-shell   # required — mmdc has no bundled browser
mmdc --version
```

> `mmdc --version` succeeds even with **no** Chrome installed, but every export then fails with `Could not find Chrome`. Install the browser above (or set `PUPPETEER_EXECUTABLE_PATH` to a system Chrome). If you can't, use Kroki (Option B) — it needs no browser.

**CI / Docker:** mmdc crashes with `Running as root without --no-sandbox` in containers. Pass the bundled puppeteer config (see `scripts/puppeteer-config.json`):

```bash
mmdc -p scripts/puppeteer-config.json -i diagram.mmd -o diagram.png
```

**Option B: Kroki API (no install)**

```bash
curl --version  # Just need curl
```

## Workflow

1. **Check deps** — validate via Kroki (needs only `curl`); check `mmdc --version` and a headless Chrome only when local export (PNG quality / PDF) is wanted
2. **Pick diagram type** — choose from table below
3. **Generate** — write `.mmd` file to disk
4. **Validate** — Kroki-first (see Validation; REQUIRED before export)
5. **Export** — use `mmdc` or Kroki API to produce PNG/SVG/PDF
6. **Self-check (vision)** — read the exported PNG and fix readability/layout defects that automatic layout can't prevent (clipped labels, cramped density, wrong orientation), then re-validate + re-export. Max 2 rounds; skip if no vision. See **Self-Check (vision)** below.
7. **Review loop** — show the image to the user, apply the minimal `.mmd` edit per request, re-export until approved (5-round safety valve). See **Review Loop** below.
8. **Report** — tell user the output file paths

## Validation (Required)

**NEVER export a diagram without validating first.**

Prefer **Kroki** for validation — it needs no browser and sidesteps the `Could not find Chrome` trap entirely. Use `mmdc` for validation only when offline.

```bash
# Validate with Kroki (preferred — no browser needed)
curl -s -X POST -H "Content-Type: text/plain" --data-binary @diagram.mmd https://kroki.io/mermaid/svg -o /tmp/test.svg && echo "Valid" || echo "Invalid"

# Validate with mmdc (offline fallback — requires headless Chrome)
mmdc -i diagram.mmd -o /tmp/test.svg 2>&1

# If error, fix the .mmd file and validate again
# Only proceed to export after validation passes
```

Common validation errors:

- Missing quotes around labels with special characters
- Wrong arrow syntax (use `->>` for sequence, `-->` for flowchart)
- Undeclared participants in sequence diagrams

> A `Could not find Chrome` (or puppeteer) error from `mmdc` is a **setup** problem, not a diagram error — the `.mmd` may be perfectly valid. Validate via Kroki instead of "fixing" correct syntax.

## Self-Check (vision)

**Zero-cost pre-check:** before spending a vision call, read the PNG dimensions (`sips -g pixelWidth -g pixelHeight diagram.png` on macOS, `file diagram.png` elsewhere). An extreme aspect ratio (longer side > 8x the shorter) is a "wrong orientation" defect — fix it without vision.

Validation (above) only proves the syntax is legal — it says nothing about whether the **rendered** diagram is readable. After exporting, use the agent's vision capability to read the PNG and catch what automatic layout can't prevent. Mermaid positions everything itself, so the failures here are about content and readability, **not** overlaps:

| Check | What to look for | Fix |
| --- | --- | --- |
| Label truncation | Node / edge text clipped or cut off | Shorten the label, or wrap it with `<br/>` |
| Cramped, unreadable density | Too many nodes crammed together; tangled lines | Flip direction (`TD`↔`LR`), split into `subgraph`s, or reduce nodes |
| Wrong orientation / aspect | Diagram far too wide or too tall to read | Change `flowchart TD`↔`LR` (or set `direction` in class/state) |
| Edge spaghetti | Many edges crossing, hard to follow | Reorder node declarations so connected nodes sit adjacent; group with `subgraph` |
| Wrong diagram type | Type doesn't suit the content (e.g. flowchart for a timeline) | Switch type (`gantt`, `sequenceDiagram`, `stateDiagram-v2`, …) |
| Low contrast | Text blends into the node fill | Adjust `classDef` / theme so text contrasts the fill |

- Max **2 self-check rounds** — if issues remain after 2 fixes, show the user anyway.
- **Re-validate (syntax) and re-export after every fix.**
- If vision is unavailable, skip self-check and show the PNG directly.

## Review Loop

After self-check, show the exported image and collect feedback. Apply the **minimal `.mmd` edit** for each request, then re-validate and re-export:

| User request | Edit action |
| --- | --- |
| Change a label | Edit the node / edge text in the `.mmd` |
| Add / remove a node or edge | Add or delete the matching line |
| Change a color | Add / adjust a `classDef` and `class <node> <className>` |
| Change layout direction | Swap `TD`↔`LR` (flowchart) or set `direction` (class / state) |
| Restructure / group | Wrap related nodes in a `subgraph`, or regenerate |

- Overwrite the same `diagram.mmd` / `diagram.png` each round — don't create `v1`, `v2`, …
- **Safety valve:** after 5 rounds, generate a mermaid.live handoff link (see next section) so the user fine-tunes the current diagram in the browser.

## Mermaid.live Handoff

When the review loop ends (approved or safety-valve), generate a one-click link that opens the current `.mmd` in the [mermaid.live](https://mermaid.live) editor for interactive fine-tuning:

```bash
python3 scripts/mermaid_live_link.py diagram.mmd
# -> https://mermaid.live/edit#pako:...
```

Pure `zlib` + `base64` (raw-deflate + URL-safe base64, same encoding mermaid.live uses), works offline. The script self-verifies with a round-trip decode before printing.

## Batch Mode (Repo Survey)

When the user asks to diagram a whole repo ("survey this codebase", "map the architecture"):

1. **Scan** — locate schemas (SQL / ORM models), API routes, and state machines / lifecycle enums in the codebase
2. **Propose** — one diagram per finding: ER for the schema, sequence for a main API flow, state for a lifecycle, flowchart for overall service layout; confirm the set with the user before generating
3. **Generate + export** — run the standard workflow per diagram into one output folder
4. **Overview page** — inline every exported SVG into a single self-contained `index.html` (title + one section per diagram, no CDN), so the user opens one file

Same validation and self-check rules apply to every diagram in the batch.

## Diagram Types

| Type | Keyword | Use for |
| ------ | --------- | --------- |
| Flowchart | `flowchart TD/LR` | processes, pipelines, decisions |
| Sequence | `sequenceDiagram` | API calls, message passing |
| Class | `classDiagram` | OOP models, data structures |
| ER | `erDiagram` | database schemas |
| State | `stateDiagram-v2` | state machines, lifecycle |
| Gantt | `gantt` | project timelines |
| Pie | `pie` | proportions |
| Git Graph | `gitGraph` | branch strategies |
| C4 Context | `C4Context` | high-level system context |
| Architecture | `architecture-beta` | cloud / CI/CD service layouts |
| Mind Map | `mindmap` | topic breakdowns |
| User Journey | `journey` | user-experience flows |
| Use Case | `usecase-beta` | actor–system interactions (UML) |
| Cynefin | `cynefin-beta` | sense-making / complexity domains |
| Event Modeling | `eventmodeling` | event-driven system timelines |
| Tree View | `treeView-beta` | file / directory hierarchies |
| Wardley Maps | `wardley-beta` | business strategy / value chains |

## Syntax Reference

**Flowchart**: See [reference/FLOWCHART.md](reference/FLOWCHART.md)
**Sequence**: See [reference/SEQUENCE.md](reference/SEQUENCE.md)
**Class & ER**: See [reference/CLASS-ER.md](reference/CLASS-ER.md)
**Architecture**: See [reference/ARCHITECTURE.md](reference/ARCHITECTURE.md)
**Use Case**: See [reference/USECASE.md](reference/USECASE.md)
**Other types**: See [reference/OTHER-TYPES.md](reference/OTHER-TYPES.md)
**Themes & styling**: See [reference/THEMES.md](reference/THEMES.md)

## Examples

See [reference/EXAMPLES.md](reference/EXAMPLES.md) for four worked examples (JWT auth sequence, microservices architecture, order state machine, cloud architecture) — each with the user prompt, the generated `.mmd`, and the output files.

## Export Commands

### Option 1: Local Export (mmdc)

Requires `mmdc` installed locally. Best for offline use.

```bash
# PNG (recommended: 2048px wide, white background)
mmdc -i diagram.mmd -o diagram.png -w 2048 --backgroundColor white

# PNG with theme — valid -t values: default | dark | neutral | forest
# (`base` is NOT a valid -t value; it only works inside a %%{init: {'theme':'base'}}%% directive)
mmdc -i diagram.mmd -o diagram.png -w 2048 --backgroundColor white --theme neutral

# SVG
mmdc -i diagram.mmd -o diagram.svg

# PDF
mmdc -i diagram.mmd -o diagram.pdf
```

### Option 2: Kroki API (No Install Required)

Use [Kroki](https://kroki.io) when `mmdc` is not available. No local dependencies needed.

```bash
# SVG via Kroki
curl -X POST -H "Content-Type: text/plain" --data-binary @diagram.mmd https://kroki.io/mermaid/svg -o diagram.svg

# PNG via Kroki
curl -X POST -H "Content-Type: text/plain" --data-binary @diagram.mmd https://kroki.io/mermaid/png -o diagram.png

# PDF is NOT supported by Kroki for Mermaid — POSTing to /mermaid/pdf returns
# HTTP 400 ("Unsupported output format: pdf for mermaid. Must be one of png or svg").
# For PDF, use the local mmdc path instead:  mmdc -i diagram.mmd -o diagram.pdf
```

**Kroki advantages:**

- No local installation required
- Works on any system with `curl`
- Supports 20+ diagram types (PlantUML, GraphViz, D2, etc.)

**When to use Kroki:**

- `mmdc` installation fails
- Quick one-off diagrams
- CI/CD pipelines without Node.js

## Common Mistakes

| Mistake | Fix |
| --------- | ----- |
| `mmdc` not found | `npm install -g @mermaid-js/mermaid-cli` |
| `mmdc` error `Could not find Chrome` | Install the headless browser: `npx puppeteer browsers install chrome-headless-shell` (or use Kroki) |
| Kroki PDF fails with HTTP 400 | Kroki does PNG/SVG only for Mermaid; use local `mmdc` for PDF |
| Valid diagram reported "invalid" by `mmdc` | The error is a Chrome/puppeteer setup failure, not a syntax error — don't rewrite correct `.mmd`; fix the browser or validate via Kroki |
| Wrong arrow in sequence | Use `->>` for request, `-->>` for response |
| Special chars in label | Wrap in quotes: `A["Label: value"]` |
| Blank/small output | Add `-w 2048` flag |
| Participant order wrong | Declare `participant` explicitly at top |
| Subgraph name with spaces | Wrap in quotes: `subgraph "My Layer"` |
