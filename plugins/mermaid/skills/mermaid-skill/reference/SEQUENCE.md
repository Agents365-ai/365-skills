# Sequence Diagram Syntax

## Basic Structure

```mermaid
sequenceDiagram
  participant C as Client
  participant G as API Gateway
  participant A as Auth Service
  participant D as Database

  C->>G: POST /login
  G->>A: validate(credentials)
  A->>D: query user
  D-->>A: user record
  A-->>G: 200 OK + token
  G-->>C: {token: "..."}
```

## Participants

Declare in desired left-to-right order:
```mermaid
sequenceDiagram
  participant A as Alice
  participant B as Bob
  actor U as User
```

- `participant` — box shape
- `actor` — stick figure

## Arrow Types

| Syntax | Style | Use for |
|--------|-------|---------|
| `->>` | Solid arrow | Sync request |
| `-->>` | Dashed arrow | Response |
| `-x` | Solid with X | Async (fire & forget) |
| `--x` | Dashed with X | Async response |
| `-)` | Open arrow | Async message |

## Activation Boxes

```mermaid
sequenceDiagram
  participant C as Client
  participant S as Server

  C->>+S: request
  S-->>-C: response
```

Or explicit:
```mermaid
sequenceDiagram
  C->>S: request
  activate S
  S-->>C: response
  deactivate S
```

## Notes

```mermaid
sequenceDiagram
  participant A
  participant B

  Note left of A: Left note
  Note right of B: Right note
  Note over A,B: Spanning note
```

## Loops and Conditionals

```mermaid
sequenceDiagram
  participant C as Client
  participant S as Server

  loop Every 5 seconds
    C->>S: heartbeat
  end

  alt success
    S-->>C: 200 OK
  else failure
    S-->>C: 500 Error
  end

  opt optional step
    C->>S: extra call
  end
```

## Parallel Execution

```mermaid
sequenceDiagram
  par Task A
    A->>B: do A
  and Task B
    A->>C: do B
  end
```
