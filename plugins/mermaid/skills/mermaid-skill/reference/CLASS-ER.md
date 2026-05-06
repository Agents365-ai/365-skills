# Class & ER Diagram Syntax

## Class Diagram

### Basic Structure

```mermaid
classDiagram
  class User {
    +String name
    +String email
    -String passwordHash
    +login() bool
    +logout()
  }

  class Order {
    +int id
    +Date createdAt
    +float total
    +place()
    +cancel()
  }

  User "1" --> "*" Order : places
```

### Visibility Modifiers

| Symbol | Meaning |
|--------|---------|
| `+` | Public |
| `-` | Private |
| `#` | Protected |
| `~` | Package/Internal |

### Relationships

| Syntax | Type | Meaning |
|--------|------|---------|
| `<\|--` | Inheritance | extends |
| `*--` | Composition | owns (lifecycle) |
| `o--` | Aggregation | has (independent) |
| `-->` | Association | uses |
| `..>` | Dependency | depends on |
| `..\|>` | Realization | implements |

### Cardinality

```mermaid
classDiagram
  User "1" --> "*" Order : places
  Order "1" --> "1..*" OrderItem : contains
  Product "0..*" --> "0..*" Category : belongs to
```

| Notation | Meaning |
|----------|---------|
| `1` | Exactly one |
| `0..1` | Zero or one |
| `*` | Many |
| `1..*` | One or more |
| `n..m` | Range |

---

## ER Diagram

### Basic Structure

```mermaid
erDiagram
  USER ||--o{ ORDER : places
  ORDER ||--|{ ORDER_ITEM : contains
  PRODUCT ||--o{ ORDER_ITEM : "included in"

  USER {
    int id PK
    string name
    string email
    datetime created_at
  }

  ORDER {
    int id PK
    int user_id FK
    float total
    string status
  }

  ORDER_ITEM {
    int order_id FK
    int product_id FK
    int quantity
  }
```

### Relationship Notation

| Left | Right | Meaning |
|------|-------|---------|
| `\|\|` | `\|\|` | One to one |
| `\|\|` | `o{` | One to zero or many |
| `\|\|` | `\|{` | One to one or many |
| `o\|` | `o{` | Zero or one to zero or many |

### Attribute Types

```mermaid
erDiagram
  PRODUCT {
    int id PK "Primary key"
    string name "Product name"
    float price
    int category_id FK "Foreign key"
    string sku UK "Unique key"
  }
```

Markers: `PK` (primary), `FK` (foreign), `UK` (unique)
