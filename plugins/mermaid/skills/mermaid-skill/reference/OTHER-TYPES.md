# Other Diagram Types

## State Diagram

```mermaid
stateDiagram-v2
  [*] --> Pending
  Pending --> Processing : payment_received
  Processing --> Shipped : packed
  Shipped --> Delivered : received
  Processing --> Cancelled : cancel
  Pending --> Cancelled : cancel
  Delivered --> [*]
  Cancelled --> [*]
```

### Composite States

```mermaid
stateDiagram-v2
  [*] --> Active

  state Active {
    [*] --> Idle
    Idle --> Running : start
    Running --> Idle : stop
  }

  Active --> Terminated : shutdown
  Terminated --> [*]
```

---

## Git Graph

```mermaid
gitGraph
  commit id: "Initial commit"
  branch develop
  checkout develop
  commit id: "Add feature A"
  commit id: "Add feature B"
  checkout main
  merge develop id: "Release v1.0"
  branch hotfix
  checkout hotfix
  commit id: "Fix critical bug"
  checkout main
  merge hotfix id: "Hotfix v1.0.1"
```

---

## Gantt Chart

```mermaid
gantt
  title Project Timeline
  dateFormat YYYY-MM-DD

  section Planning
  Requirements     :a1, 2024-01-01, 7d
  Design           :a2, after a1, 5d

  section Development
  Backend API      :b1, after a2, 14d
  Frontend UI      :b2, after a2, 14d

  section Testing
  Integration Test :c1, after b1, 7d
```

---

## Pie Chart

```mermaid
pie title Language Distribution
  "JavaScript" : 45
  "Python" : 30
  "Go" : 15
  "Other" : 10
```

---

## Mind Map

```mermaid
mindmap
  root((Project))
    Frontend
      React
      CSS
      TypeScript
    Backend
      Node.js
      PostgreSQL
      Redis
    DevOps
      Docker
      Kubernetes
      CI/CD
```

---

## C4 Context Diagram

```mermaid
C4Context
  title System Context Diagram

  Person(user, "User", "A user of the system")
  System(system, "Main System", "The core application")
  System_Ext(external, "External API", "Third-party service")

  Rel(user, system, "Uses")
  Rel(system, external, "Calls")
```

---

## Tree View Diagram

Shows hierarchical / file-tree data with indentation (v11.14+, `treeView-beta`). Directories end with `/`; box-drawing input (`├──`, `└──`, `│`) is auto-detected (v11.16+).

```mermaid
treeView-beta
  my-project/
    src/
      index.js
    package.json
    README.md
```

---

## Event Modeling Diagram

Describes information flow over time with swimlane time frames (`eventmodeling`, v11.15+). `tf` = compact, `timeframe` = relaxed. Relations are inferred by default.

```mermaid
eventmodeling
  tf 01 ui CartUI
  tf 02 cmd AddItem
  tf 03 evt ItemAdded
```

Entity kinds: `ui` (UI), `cmd` (command), `evt` (event), plus view / automation / translation patterns. Each time frame needs a unique number.

---

## Cynefin Diagram

Sense-making framework with five complexity domains (`cynefin-beta`, v11.16+): clear, complicated, complex, chaotic, confusion.

```mermaid
cynefin-beta
  title Incident Response

  complex
    "Investigate root cause"
    "Run chaos experiment"

  complicated
    "Analyze performance data"

  clear
    "Restart service"

  chaotic
    "Page on-call immediately"

  confusion
    "Unknown failure mode"

  complex --> complicated : "Pattern identified"
  clear --> chaotic : "Complacency"
```

Keep per-domain item lists short — the quadrants have fixed layout and long lists can overflow. The confusion ellipse caps at 3 items (+N more badge).

---

## Wardley Maps

Business strategy maps positioning components on visibility (Y) × evolution (X) axes (`wardley-beta`, v11.14+).

```mermaid
wardley-beta
  title Tea Shop Value Chain

  anchor Business [0.95, 0.63]
  component Cup of Tea [0.79, 0.61]
  component Hot Water [0.52, 0.80]

  Business -> Cup of Tea
  Cup of Tea -> Hot Water

  evolve Kettle 0.62
```

- Coordinates are `[visibility, evolution]` (0.0–1.0) — **not** (x, y)
- `component Name [v, e]` — a component node; `anchor Name [v, e]` — user/customer node (bold)
- `name -> name` — dependency link; `evolve Name 0.62` — mark evolution movement
- Optional: `size [1100, 600]` canvas, `(inertia)` decorator for legacy components
