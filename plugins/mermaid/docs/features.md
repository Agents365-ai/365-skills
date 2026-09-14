# Features & Comparison

[← Back to README](https://github.com/Agents365-ai/365-skills/blob/main/plugins/mermaid/README.md)

## Why This Skill?

| Feature | This Skill | Native Claude Code | Other Skills | MCP Server |
| --------- | ----------- | ------------------- | -------------- | ------------ |
| **Write Mermaid syntax** | Guided by examples | Built-in capability | Varies | Varies |
| **Validation before export** | Required step | No validation loop | Often skipped | Varies |
| **Export to PNG/SVG/PDF** | Automatic | Manual — user must ask | Usually one method | Web only |
| **Zero-install fallback** | Kroki needs only curl | No fallback | Requires install | Requires setup |
| **Proactive triggering** | Auto-triggers for 3+ components | Only when explicitly asked | Manual only | Manual |
| **Chinese language support** | Chinese keyword triggers | No keyword triggers | English only | English only |
| **End-to-end workflow** | Generate → Validate → Export → Report | Generate only | Partial | Partial |
| **Progressive disclosure** | Syntax in separate files | N/A | All inline | N/A |

**Key advantages over native Claude Code:**

- **Complete pipeline** — Claude Code can write Mermaid, but stops at `.mmd`. This skill adds validation, export, and error recovery automatically
- **Catches errors early** — validation loop prevents broken diagrams from being exported
- **Flexible export** — local mmdc or Kroki API fallback (no install needed); validation is Kroki-first so it never needs a browser
- **Mermaid.live handoff** — review loops end with a one-click link to keep editing the diagram in the browser
- **Batch mode** — repo survey generates a diagram suite plus a self-contained HTML overview
- **Proactive diagramming** — auto-triggers when discussing architecture, not just when you ask for a diagram

## What This Skill Can Do

### Diagram Types (17+)

| Type | Use for | Example |
| ------ | --------- | --------- |
| **Flowchart** | Processes, pipelines, decision trees | CI/CD pipeline, user registration flow |
| **Sequence** | API calls, authentication flows | JWT auth, microservice communication |
| **Class** | OOP models, data structures | Domain models, inheritance hierarchies |
| **ER** | Database schemas | User-Order-Product relationships |
| **State** | State machines, lifecycles | Order status, connection states |
| **Gantt** | Project timelines | Sprint planning, release schedules |
| **Pie** | Proportions, distributions | Market share, resource allocation |
| **Git Graph** | Branch strategies | GitFlow, trunk-based development |
| **C4 Context** | High-level architecture | System context, container diagrams |
| **Architecture** | Cloud / CI-CD service layouts | API gateway, service topology |
| **Mind Map** | Topic breakdowns | Feature planning, brainstorming |
| **Use Case** | Actor–system interactions (UML) | Login flow, role permissions |
| **Cynefin** | Sense-making / complexity domains | Incident response, strategy |
| **Event Modeling** | Event-driven system timelines | Cart add-to-order flow |
| **Tree View** | File / directory hierarchies | Project structure docs |
| **Wardley Maps** | Business strategy / value chains | Build vs. buy analysis |

### Output Formats

- **PNG** — High resolution (2048px), white background, multiple themes
- **SVG** — Scalable vector, perfect for docs
- **PDF** — Print-ready documents

### Automatic Triggering

The skill activates when you:

- Ask for diagrams explicitly: *"create a flowchart"*, *"draw architecture"*
- Explain complex systems: *"how does authentication work"* (3+ components)
- Use Chinese: *"画一个时序图"*, *"架构图"*
