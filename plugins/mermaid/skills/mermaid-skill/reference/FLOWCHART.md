# Flowchart Syntax

## Basic Structure

```mermaid
flowchart TD
  A[Client] --> B[API Gateway]
  B --> C[Auth Service]
  B --> D[Order Service]
  D --> E[(Order DB)]
  C --> F[(User DB)]

  subgraph Services
    C
    D
  end
```

## Direction

| Keyword | Direction |
|---------|-----------|
| `TD` / `TB` | Top to bottom |
| `LR` | Left to right |
| `RL` | Right to left |
| `BT` | Bottom to top |

## Node Shapes

| Syntax | Shape | Use for |
|--------|-------|---------|
| `[text]` | Rectangle | Default nodes |
| `(text)` | Rounded rectangle | Processes |
| `{text}` | Diamond | Decisions |
| `[(text)]` | Cylinder | Databases |
| `[[text]]` | Subroutine | External calls |
| `((text))` | Circle | Start/end points |
| `>text]` | Flag | Async events |
| `{{text}}` | Hexagon | Preparation steps |

## Arrow Types

| Syntax | Style | Use for |
|--------|-------|---------|
| `-->` | Arrow | Normal flow |
| `---` | Line | Connection (no direction) |
| `-.->` | Dashed arrow | Optional/async |
| `==>` | Thick arrow | Important flow |
| `--x` | X end | Termination |
| `--o` | Circle end | Reference |

## Labels on Arrows

```mermaid
flowchart LR
  A -->|yes| B
  A -->|no| C
  B -->|"with quotes"| D
```

## Subgraphs

```mermaid
flowchart TD
  subgraph "Frontend Layer"
    A[Web App]
    B[Mobile App]
  end

  subgraph "Backend Layer"
    C[API Server]
    D[Worker]
  end

  A & B --> C
  C --> D
```

## Special Characters

Wrap in quotes for special characters:
```mermaid
flowchart LR
  A["Node: with colon"]
  B["Node (with parens)"]
  A --> B
```
