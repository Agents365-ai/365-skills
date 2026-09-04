# Use Case Diagram Syntax

Use case diagrams (UML) show how actors interact with a system and its use cases. Available as `usecase-beta` (v11.17+).

## Basic Structure

```mermaid
usecase-beta
direction LR
actor Customer("Customer")
systemBoundary "Order system"
  Checkout("Place order")
end
Customer --> Checkout
```

- `usecase-beta` — required first line
- `direction` — `TD`, `TB`, `BT`, `LR`, or `RL`
- Actors: `actor Name("Display label")` — stick figure by default
- Use cases: `Name("label")` = ellipse, `Name[label]` = rectangle
- `systemBoundary id["Title"] ... end` — groups actors/use cases (default `rect`, or `@{ type: package }`)

## Actor Variants

```mermaid
usecase-beta
actor Normal("Normal actor")
actor Hollow("Hollow actor")@{ type: hollow }
actor Awesome("Awesome actor")@{ type: awesome }
actor Icon("Icon actor")@{ icon: "fa:user" }
actor B2B("Sales agent")@{ business: true } <<Employee>>
Normal --> Manage
```

- `type`: `hollow` | `awesome` (icon actors via `icon: "fa:name"`)
- `business: true` adds the conventional business slash
- `<<stereotype>>` adds a visible stereotype above the label

## Relationships

```mermaid
usecase-beta
actor Admin
actor Person
Checkout
Payment
ApplyCoupon
Admin --|> Person                %% generalization
Checkout ..> : include Payment   %% include
ApplyCoupon ..> : extend Checkout %% extend
User --> Start                   %% plain association
User --o Start                   %% circle (aggregation-like)
User --x Finish                  %% cross
```

| Operator | Meaning |
| ---------- | --------- |
| `-->`, `--`, `<--` | Association |
| `--o`, `o--` | Circle-end association |
| `--x`, `x--` | Cross-end association |
| `..>` `: include X` | Include (source includes target) |
| `..>` `: extend X` | Extend (source extends target) |
| `--\|>` | Generalization (specialized → general) |

## Notes and JSON Tables

```mermaid
usecase-beta
note for Login "`Requires an **active session**`"
actor User
Login("Sign in")
User --> Login

json Payload@{
  "status": "pending",
  "items": [{ "name": "Book" }]
}:::data
Inspect --> Payload
```

- `note for <target> "text"` — attaches to an actor or use case
- `json <id>@{ ... }` — renders a JSON object as a table node
- Nested values use paths: `address.city`, `items[0].name`

## Styling

Classes and direct styles work like other Mermaid types: `classDef`, `class`, `style`, or `:::` suffix on declarations. Use `%%` for comments; `//` and `#` are NOT comments in usecase diagrams.
