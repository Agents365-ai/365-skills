# Workflow & File Structure

[← Back to README](https://github.com/Agents365-ai/365-skills/blob/main/plugins/mermaid/README.md)

## How It Works

This skill follows a validation-first workflow:

![Skill Workflow](https://raw.githubusercontent.com/Agents365-ai/365-skills/main/plugins/mermaid/assets/workflow.png)

<details>
<summary>View Mermaid source</summary>

```mermaid
flowchart TD
  Start([User requests diagram]):::input --> CheckDeps{Check deps}:::decision
  CheckDeps -->|mmdc available| UseMmdc[Use mmdc locally]:::process
  CheckDeps -->|mmdc unavailable| UseKroki[Use Kroki API]:::process
  UseMmdc --> PickType
  UseKroki --> PickType
  PickType[Pick diagram type]:::process --> Generate[Generate .mmd file]:::process
  Generate --> Validate{Validate syntax}:::decision
  Validate -->|Error| Fix[Fix .mmd file]:::warning
  Fix --> Validate
  Validate -->|Pass| Export[Export PNG/SVG/PDF]:::process
  Export --> Report([Report output paths]):::output

  classDef input fill:#d4edda,stroke:#28a745,color:#155724
  classDef process fill:#cce5ff,stroke:#007bff,color:#004085
  classDef decision fill:#fff3cd,stroke:#ffc107,color:#856404
  classDef warning fill:#f8d7da,stroke:#dc3545,color:#721c24
  classDef output fill:#e2d5f1,stroke:#6f42c1,color:#4a235a
```

**Color legend:** 🟢 Input | 🔵 Process | 🟡 Decision | 🔴 Warning | 🟣 Output

</details>

## File Structure

```
mermaid-skill/
├── SKILL.md              # Main skill instructions
├── reference/
│   ├── FLOWCHART.md      # Flowchart syntax & examples
│   ├── SEQUENCE.md       # Sequence diagram syntax
│   ├── CLASS-ER.md       # Class & ER diagram syntax
│   └── OTHER-TYPES.md    # State, Gantt, Git, Pie, Mindmap, C4
├── assets/
│   ├── example.mmd       # Example: microservices architecture
│   ├── example.png
│   ├── workflow.mmd      # Example: workflow (English)
│   ├── workflow.png
│   ├── workflow_cn.mmd   # Example: workflow (Chinese)
│   └── workflow_cn.png
├── README.md             # English docs (default)
└── README_CN.md          # Chinese docs
```
