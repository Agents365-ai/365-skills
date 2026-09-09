# tldraw-skill — From Text to Whiteboard Diagrams

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/Agents365-ai/tldraw-skill?style=flat&logo=github)](https://github.com/Agents365-ai/tldraw-skill/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Agents365-ai/tldraw-skill?style=flat&logo=github)](https://github.com/Agents365-ai/tldraw-skill/network/members)
[![Latest Release](https://img.shields.io/github/v/release/Agents365-ai/tldraw-skill?logo=github)](https://github.com/Agents365-ai/tldraw-skill/releases/latest)
[![Last Commit](https://img.shields.io/github/last-commit/Agents365-ai/tldraw-skill?logo=github)](https://github.com/Agents365-ai/tldraw-skill/commits/main)

[![SkillsMP](https://img.shields.io/badge/SkillsMP-listed-1f6feb)](https://skillsmp.com/skills/agents365-ai-tldraw-skill-skills-tldraw-skill-skill-md)
[![ClawHub](https://img.shields.io/badge/ClawHub-listed-ff6b35)](https://clawhub.ai/agents365-ai/tldraw-pro-skill)
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-plugin-8a2be2)](https://github.com/Agents365-ai/365-skills)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-2ea44f)](https://agentskills.io)
**English** · [中文](README_CN.md) · [📖 Online Docs](https://agents365-ai.github.io/tldraw-skill/)

A skill that turns natural-language descriptions into hand-drawn-style `.tldr` whiteboard diagrams and exports them to PNG / SVG via [`@kitschpatrol/tldraw-cli`](https://github.com/kitschpatrol/tldraw-cli). Works with **Claude Code, Cursor, Copilot, OpenClaw, Codex, Hermes**, and any agent compatible with the [Agent Skills](https://agentskills.io) format.

<p align="center">
  <img src="assets/example.png" width="900" alt="Microservices Architecture — generated from a single natural-language prompt">
</p>

## ✨ Highlights

- **6 diagram type presets** — Architecture, Flowchart, Sequence, ML/Deep Learning, ERD, UML
- **Vision-based self-check + auto-fix** — reads its own PNG output and auto-fixes overlaps, clipped labels, missing arrows, off-canvas shapes, and stacked edges (up to 2 rounds; requires a vision-enabled model)
- **Iterative review loop** — targeted JSON edits, up to 5 rounds, then suggests opening in tldraw.com for fine-tuning
- **Complexity-scaled layout** — spacing (200 / 280 / 350px) grows with node count; routing corridors and hub placement built in
- **Semantic 13-color palette** — `blue` services, `green` databases, `violet` auth, `orange` queues, `yellow` decisions, etc. — consistent across runs
- **Zero browser automation** — `tldraw-cli` runs anywhere Node runs; identical setup on macOS, Linux, Windows (no Chromium, no Playwright)

## 🖼️ Examples

> [!TIP]
> **The hero image above was generated from this single prompt:**

```
Create a microservices e-commerce architecture with Mobile/Web/Admin clients,
API Gateway, User/Order/Product/Payment services, Kafka event bus, Notification
service, and User DB / Order DB / Product DB / Redis Cache / Stripe API
```

The skill plans shape positions on a 10px grid, distributes arrow endpoints around each node's perimeter, and re-checks the exported PNG to catch overlaps before showing you the result.

### More diagram styles

Each of these was generated from a single natural-language prompt and exported through the same self-check pipeline:

<table>
  <tr>
    <td align="center" width="50%"><img src="assets/example-flowchart.png" width="240" alt="Flowchart with a decision branch and a retry loop"></td>
    <td align="center" width="50%"><img src="assets/example-sequence.png" width="460" alt="Sequence diagram of a login API flow"></td>
  </tr>
  <tr>
    <td align="center"><b>Flowchart</b> — <code>diamond</code> decisions, auto Yes/No labels, dashed retry loop</td>
    <td align="center"><b>Sequence</b> — dotted lifelines, solid calls vs. dashed returns</td>
  </tr>
  <tr>
    <td align="center"><img src="assets/example-ml.png" width="165" alt="Transformer encoder block with residual skip-connections"></td>
    <td align="center"><img src="assets/example-erd.png" width="340" alt="Entity-relationship diagram for an e-commerce schema"></td>
  </tr>
  <tr>
    <td align="center"><b>ML / Transformer</b> — tensor-shape labels, residual skip-connections</td>
    <td align="center"><b>ERD</b> — PK <code>*</code> / FK <code>&gt;</code> markers, cardinality on relationships</td>
  </tr>
</table>

<details>
<summary>Prompts used for these four</summary>

- **Flowchart:** `Draw a login flowchart: Start → Enter Credentials → decision "Valid?"; Yes → Load Dashboard → Success; No → Show Error, then loop back to Enter Credentials.`
- **Sequence:** `Sequence diagram for a login API: Client → API → Auth → DB, with POST /login, validate, query user, and dashed return messages (user row, 200 OK, session).`
- **ML / Transformer:** `Sketch a Transformer encoder block: input embedding [B,512,768], positional encoding, multi-head attention, add & norm, feed forward [768→3072→768], add & norm, encoder output — with residual skip-connections.`
- **ERD:** `E-commerce ERD with User, Order, Product, OrderItem entities; mark PK with * and FK with >; show 1:N relationships places / contains / in.`

</details>

### It's a whiteboard — it can sketch, too

tldraw isn't only boxes and arrows. Because it's a hand-drawn **whiteboard** with a freehand `draw` shape, the skill can also draw figuratively — geo primitives (ellipse / triangle / heart) plus freehand strokes, or pure freehand curves generated from parametric equations:

<table>
  <tr>
    <td align="center"><img src="assets/example-cat.png" width="150" alt="A cat from ellipses, triangles, a heart nose, with freehand whiskers and a curled tail"></td>
    <td align="center"><img src="assets/example-dog.png" width="160" alt="A dog with floppy ears, a tongue, and a freehand wagging tail"></td>
    <td align="center"><img src="assets/example-spiral.png" width="195" alt="A hand-drawn Archimedean spiral"></td>
  </tr>
  <tr>
    <td align="center"><img src="assets/example-flower.png" width="125" alt="A flower whose petals are a rose curve, with stem and leaves"></td>
    <td align="center"><img src="assets/example-butterfly.png" width="215" alt="A butterfly traced by the Temple Fay butterfly curve"></td>
    <td align="center"><img src="assets/example-tree.png" width="150" alt="A stylized tree with a wobbly freehand canopy"></td>
  </tr>
</table>

<sub><b>Cat / dog</b> — geo primitives + freehand whiskers and tails. <b>Spiral / flower / butterfly / tree</b> — pure freehand <code>draw</code> strokes generated from parametric curves (the butterfly is a single 1,400-point stroke). Not what the skill is <i>for</i> — it's a diagram tool — but a fun demonstration of the freehand <code>draw</code> shape and the hand-drawn aesthetic. Sources under <a href="assets/">assets/</a> (<code>example-cat/dog/spiral/flower/butterfly/tree.tldr</code>).</sub>

Full feature breakdown in [docs/features.md](docs/features.md). Known limitations (strict UML notation, PDF export, vision requirement) in [docs/limitations.md](docs/limitations.md).

## 🚀 Installation

### 1. Install `@kitschpatrol/tldraw-cli`

| Platform | Command |
|----------|---------|
| **macOS / Linux / Windows** | `npm install -g @kitschpatrol/tldraw-cli` |

Verify with `tldraw --version`. Requires Node.js (npm). No browser automation, no Playwright — `tldraw-cli` runs identically everywhere Node runs.

### 2. Install the skill

```bash
# Any agent (Claude Code, Cursor, Copilot, ...)
npx skills add Agents365-ai/365-skills -g
```

```text
# Claude Code plugin marketplace
> /plugin marketplace add Agents365-ai/365-skills
> /plugin install tldraw
```

```bash
# Manual install
git clone https://github.com/Agents365-ai/tldraw-skill.git \
  ~/.claude/skills/tldraw-skill
```

Also indexed on [SkillsMP](https://skillsmp.com/skills/agents365-ai-tldraw-skill-skills-tldraw-skill-skill-md) and [ClawHub](https://clawhub.ai/agents365-ai/tldraw-pro-skill).

**Updating:** `/plugin update tldraw` (Claude Code), `skills update tldraw-skill` (SkillsMP), `clawhub update tldraw-pro-skill` (OpenClaw), or `git pull` for manual installs.

## ⚡ Quick Start

After installation, just describe what you want. For example, an ML model sketch:

```
Sketch a Transformer encoder-decoder on a whiteboard: 6-layer encoder with
self-attention, 6-layer decoder with cross-attention, input embeddings
(batch × 512 × 768), positional encoding, and a final output projection.
Annotate tensor shapes between layers and color-code by layer type.
```

The skill plans the layout, generates the `.tldr` JSON, exports to PNG/SVG, self-checks the result, and lets you iterate.

## 🧩 Supported Diagram Types

| Category | Examples | Notable features |
| --- | --- | --- |
| Architecture | microservices, cloud, network topology, deployment | Hub-center pattern for event buses; tier rows; `cloud`/`hexagon`/`triangle` shape vocabulary |
| Flowcharts | business processes, workflows, decision trees | `ellipse` start/end, `diamond` decisions; auto-labels Yes/No branches |
| Sequence diagrams | API call flows, request/response, async messages | Lifeline approximation (thin grey rectangles); dashed arrows for async / return |
| ML / Deep Learning | Transformer, CNN, LSTM, GRU | Tensor shape annotations in node labels; layer-type color coding; skip-connection bends |
| ERD | entity relationships, schemas | Multi-line entity labels (PK `*` / FK `>`); cardinality on arrow labels |
| UML Class | high-level class diagrams | Multi-line class labels (attributes + methods); inheritance / association arrows (see [limitations](docs/limitations.md) for strict UML notation) |

## 🔄 How it works

<p align="center">
  <img src="assets/workflow.png" width="380" alt="The skill's 7-step pipeline: check deps → plan layout → generate .tldr → export PNG → self-check → review loop → final export, with a refine-and-repeat loop from review back to generate">
</p>

<p align="center"><sub><i>This diagram was drawn by the skill itself — see <a href="assets/workflow.tldr">assets/workflow.tldr</a>.</i></sub></p>

1. **Check deps** — verifies `tldraw --version`; offers `npm install -g @kitschpatrol/tldraw-cli` if missing.
2. **Plan layout** — picks geo shapes, assigns node positions on a 10px grid, spaces according to node count.
3. **Generate `.tldr` JSON** — writes shape + arrow records with bound anchors and distributed `normalizedAnchor` points.
4. **Export draft PNG** — `tldraw export diagram.tldr -f png --scale 2 -o ./`.
5. **Self-check** — vision-enabled model reads the PNG, auto-fixes overlaps / clipped labels / arrow crossings (max 2 rounds). Skipped if vision isn't available.
6. **Review loop** — shows the image, applies your targeted edits (color, label, add/remove node, move shape), re-exports — up to 5 rounds before suggesting tldraw.com for hand-tuning.
7. **Final export** — re-exports the approved version to all requested formats and reports file paths.

## 🆚 Comparison

### vs Native Agent (no skill)

| Feature | Native agent | tldraw-skill |
| --- | --- | --- |
| Self-check after export | ❌ | ✅ vision-based, 2-round auto-fix |
| Iterative review loop | ❌ manual re-prompt | ✅ targeted JSON edits, 5-round safety valve |
| Diagram type presets | ❌ | ✅ 6 presets (Arch, Flow, Seq, ML, ERD, UML) |
| Complexity-scaled spacing | ❌ | ✅ 200 / 280 / 350px tiers by node count |
| Color palette | random / inconsistent | ✅ 13-color semantic system |
| Arrow distribution on shape | random anchors → stacked | ✅ even spacing around perimeter |
| Grid alignment | ❌ | ✅ 10px snap matches tldraw default |
| Multi-line tensor / column labels | ad-hoc | ✅ embedded `\n` formatting baked in |

## 🎯 When to use (and when not to)

**Good fit:**

- Whiteboard / hand-drawn-style diagrams — architecture, flowcharts, sequence, ERD, UML *sketches*, mind maps
- A casual, sketchy aesthetic; freehand strokes and figurative doodles (the `draw` shape)
- Quick visual explainers where a polished, pixel-precise look isn't the goal

**Reach for a sibling skill instead when you need:**

- **Logos, solid-color graphics, or filled icons** — tldraw has no opaque fill (`solid` renders as a light tint, so white-on-dark artwork can't be reproduced) → [drawio-skill](https://github.com/Agents365-ai/drawio-skill) or your original vector source
- **Precise angular geometry / strict vector shapes** → [drawio-skill](https://github.com/Agents365-ai/drawio-skill)
- **Strict, publication-grade UML** (hollow inheritance arrows, etc.) → [plantuml-skill](https://github.com/Agents365-ai/plantuml-skill) or [drawio-skill](https://github.com/Agents365-ai/drawio-skill)
- **Automatic layout of many nodes** (tldraw needs manual coordinates) → [mermaid-skill](https://github.com/Agents365-ai/mermaid-skill)
- **Pixel-faithful reproduction of an existing image** — not what any diagram skill is for

## 🔗 Related Skills

Part of the [Agents365-ai diagram-skill family](https://github.com/Agents365-ai) — pick the right tool for the job:

| Skill | Style | Best for |
| --- | --- | --- |
| [drawio-skill](https://github.com/Agents365-ai/drawio-skill) | Polished business diagrams | Stakeholder decks, strict UML, ML papers, network topologies |
| [excalidraw-skill](https://github.com/Agents365-ai/excalidraw-skill) | Hand-drawn / sketchy | Whiteboard mockups, informal diagrams |
| [mermaid-skill](https://github.com/Agents365-ai/mermaid-skill) | Text-based, auto-layout | README-embeddable, version-control friendly |
| [plantuml-skill](https://github.com/Agents365-ai/plantuml-skill) | UML-focused | Class / sequence diagrams in CI pipelines |

## ❤️ Support

If this skill helps you, consider supporting the author:

<table>
  <tr>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/wechat-pay.png" width="180" alt="WeChat Pay">
      <br>
      <b>WeChat Pay</b>
    </td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/alipay.png" width="180" alt="Alipay">
      <br>
      <b>Alipay</b>
    </td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/buymeacoffee.png" width="180" alt="Buy Me a Coffee">
      <br>
      <b>Buy Me a Coffee</b>
    </td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/awarding/award.gif" width="180" alt="Give a Reward">
      <br>
      <b>Give a Reward</b>
    </td>
  </tr>
</table>

## 👤 Author

**Agents365-ai**

- GitHub: <https://github.com/Agents365-ai>
- Bilibili: <https://space.bilibili.com/441831884>

## 📄 License

[MIT](LICENSE)
