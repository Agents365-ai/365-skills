# Features & Comparison

[← Back to README](https://github.com/Agents365-ai/365-skills/blob/main/plugins/plantuml/README.md)

## Comparison

### vs No Skill (native agent)

| Feature | Native agent | This skill |
| --------- | -------------- | ------------ |
| Generate PlantUML source | Yes — LLMs know the syntax | Yes |
| Export to PNG/SVG | No — outputs text only | Yes — one `curl` POST to Kroki |
| Renderer choice | None | Public Kroki / local Kroki / `plantuml.jar` |
| Proactive triggers | No — only when explicitly asked | Yes — auto-suggests when 3+ components, APIs, class hierarchies, state machines |
| Diagram-type catalog | Implicit | 10+ types with shape vocabulary, arrow vocabulary, multiplicity notation |
| Theme defaults | Random per run | `!theme plain` baseline + curated palette of pastel colors |
| C4 diagrams via cloud | Often broken (`!include` 404s) | Uses Kroki `c4plantuml` endpoint with stitched includes |
| Common-mistake table | None | 9 known pitfalls (arrow direction, layout overflow, label escaping, ordering, etc.) |
| Offline support | No | Yes — local Kroki Docker container or local jar |

### vs Other PlantUML approaches

| Approach | Install footprint | Offline | LLM-aware | Notes |
| ---------- | ------------------- | --------- | ----------- | ------- |
| **This skill (Kroki API)** | `curl` only | Optional via Docker | Yes | Default; zero-install |
| **This skill (local Kroki)** | Docker | Yes | Yes | One container, no Java needed |
| **This skill (`plantuml.jar`)** | Java + Graphviz + jar | Yes | Yes | Heaviest, but offline by default |
| Public PlantUML web server | Browser only | No | Manual | Not scriptable from agents |
| `node-plantuml` / npm wrappers | Node + Java | Yes | No | Wrappers around the same jar |
| VS Code PlantUML extension | Editor + Java | Yes | No | Author-time, not agent-time |

## Key advantages

1. **Zero-install default** — `curl` is everywhere; the skill works out of the box on macOS, Linux, and Windows (Git Bash / WSL)
2. **Three rendering paths** — pick public Kroki for speed, local Kroki for offline/privacy, or the jar for air-gapped deployments
3. **Diagram-type playbook** — each of 10+ diagram types has a copy-paste syntax template, shape vocabulary, and arrow conventions
4. **Mistake-aware** — the SKILL.md ships with a curated "Common Mistakes" table covering arrow direction, layout overflow, label escaping, participant ordering, and the C4-include trap
5. **Multi-agent, single file** — one `SKILL.md` runs across Claude Code, Opencode, OpenClaw, Hermes, Codex, and SkillsMP

## Supported diagram types

- **Sequence**: API calls, OAuth flows, protocol traces — with lifelines, activation boxes, async arrows
- **Component / Architecture**: services, modules, queues, databases, clouds — with package/rectangle grouping
- **Class**: OOP models — inheritance, composition, aggregation, multiplicities (`"1" --> "*"`)
- **ER / Entity**: database schemas — `<<PK>>` / `<<FK>>` notation, crow's-foot relationships
- **Activity**: workflows, business processes, decision branches — `if/then/else/endif` syntax
- **Use Case**: actors, system boundaries, user stories
- **State**: state machines, lifecycle flows, `[*] -->` start/end markers
- **C4**: Context, Container, Component diagrams via Kroki's `c4plantuml` endpoint
- **Other**: mind maps (`@startmindmap`), gantt (`@startgantt`)
