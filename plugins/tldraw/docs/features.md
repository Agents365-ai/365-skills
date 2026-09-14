# Features & Comparison

[← Back to README](https://github.com/Agents365-ai/365-skills/blob/main/plugins/tldraw/README.md)

## What it does

- Generates `.tldr` JSON files from natural language descriptions
- Exports diagrams to PNG or SVG using `@kitschpatrol/tldraw-cli`
- **6 diagram type presets**: Architecture, Flowchart, Sequence, ML/Deep Learning, ERD, UML — with preset shape vocabulary and layout conventions
- **Self-check loop** — uses vision to read the exported PNG and auto-fix overlaps, clipped labels, and missing arrows before showing you
- **Iterative review loop** — collect feedback, apply targeted JSON edits, re-export until approved (5-round safety valve)
- **Complexity-scaled layout** — spacing automatically grows with node count to prevent overlaps
- **Custom output directory** — ask for any output path (e.g. `./artifacts/`) and the skill will `mkdir -p` and export there
- Triggers automatically when diagrams would help explain complex systems
- Hand-drawn whiteboard aesthetic by default; switchable to clean fonts

## Comparison

### vs Native Agent (no skill)

| Feature | Native agent | This skill |
| --------- | ------------- | ------------ |
| Generate `.tldr` JSON | Partial — LLMs often produce schema-invalid records | Yes — schema-correct skeleton + record templates |
| Self-check after export | No | Yes — reads PNG and auto-fixes 6 issue types |
| Iterative review loop | No — must manually re-prompt | Yes — targeted edits, 5-round safety valve |
| Proactive triggers | No — only when explicitly asked | Yes — auto-suggests when 3+ components |
| Layout guidelines | None — varies by run | Complexity-scaled spacing, routing corridors, hub placement |
| Diagram type presets | No | Yes — 6 presets (Architecture, Flowchart, Sequence, ML/DL, ERD, UML) |
| Color palette | Random / inconsistent | 13-color semantic system (blue=services, green=DB, violet=auth...) |
| Arrow distribution rules | Basic | Distribute `normalizedAnchor` across shape perimeter to prevent stacking |
| Index ordering rules | Often wrong (uses `b1`, `c1`) | Strict `a*` format with z-order conventions |
| Multi-platform metadata | No | Yes — OpenClaw, Hermes, SkillsMP namespaces |

### vs Other Diagram Skills

| Feature | tldraw-skill | drawio-skill | mermaid-skill | excalidraw-skill |
| --------- | -------------- | -------------- | --------------- | ------------------ |
| **Aesthetic** | Hand-drawn whiteboard | Clean professional | Auto-layout text | Sketchy informal |
| **Format** | `.tldr` JSON | `.drawio` XML | text DSL | `.excalidraw` JSON |
| **Export formats** | PNG, SVG | PNG, SVG, PDF, JPG | PNG, SVG, PDF | PNG, SVG |
| **Manual layout control** | x/y coords | x/y coords | auto-layout only | x/y coords |
| **Self-check loop** | vision-based | vision-based | partial | partial |
| **Diagram presets** | 6 types | 6 types | text-syntax driven | None |
| **Style presets** | — | user-learnable | — | — |
| **Best for** | Whiteboard sketches, casual explainers, internal docs | Polished business / academic figures | Quick text-to-diagram for docs | Hand-drawn presentations |

## Supported diagram types

- **Architecture**: microservices, cloud, deployment — with tier-based color coding and hub placement
- **Flowcharts**: business processes, decision trees, state machines — with semantic shape types
- **Sequence**: actor-message flows approximated with rectangles + horizontal arrows
- **ML / Deep Learning**: layer-type color coding, tensor shape annotations
- **ERD**: entities as multi-line text rectangles with cardinality on arrows
- **UML Class**: classes as multi-line text rectangles with relationship arrows
