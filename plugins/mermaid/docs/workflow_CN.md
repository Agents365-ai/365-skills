# 工作流程与文件结构

[← 返回 README](https://github.com/Agents365-ai/365-skills/blob/main/plugins/mermaid/README_CN.md)

## 工作流程

本技能采用验证优先的工作流:

![技能工作流](https://raw.githubusercontent.com/Agents365-ai/365-skills/main/plugins/mermaid/assets/workflow_cn.png)

<details>
<summary>查看 Mermaid 源码</summary>

```mermaid
flowchart TD
  Start([用户请求图表]):::input --> CheckDeps{检查依赖}:::decision
  CheckDeps -->|mmdc 可用| UseMmdc[使用 mmdc 本地导出]:::process
  CheckDeps -->|mmdc 不可用| UseKroki[使用 Kroki API]:::process
  UseMmdc --> PickType
  UseKroki --> PickType
  PickType[选择图表类型]:::process --> Generate[生成 .mmd 文件]:::process
  Generate --> Validate{验证语法}:::decision
  Validate -->|错误| Fix[修复 .mmd 文件]:::warning
  Fix --> Validate
  Validate -->|通过| Export[导出 PNG/SVG/PDF]:::process
  Export --> Report([报告输出路径]):::output

  classDef input fill:#d4edda,stroke:#28a745,color:#155724
  classDef process fill:#cce5ff,stroke:#007bff,color:#004085
  classDef decision fill:#fff3cd,stroke:#ffc107,color:#856404
  classDef warning fill:#f8d7da,stroke:#dc3545,color:#721c24
  classDef output fill:#e2d5f1,stroke:#6f42c1,color:#4a235a
```

**颜色图例:** 🟢 输入 | 🔵 处理 | 🟡 决策 | 🔴 警告 | 🟣 输出

</details>

## 文件结构

```
mermaid-skill/
├── SKILL.md              # 主技能说明
├── reference/
│   ├── FLOWCHART.md      # 流程图语法和示例
│   ├── SEQUENCE.md       # 时序图语法
│   ├── CLASS-ER.md       # 类图和 ER 图语法
│   └── OTHER-TYPES.md    # 状态图、甘特图、Git图、饼图、思维导图、C4
├── assets/
│   ├── example.mmd       # 示例:微服务架构
│   ├── example.png
│   ├── workflow.mmd      # 示例:工作流(英文)
│   ├── workflow.png
│   ├── workflow_cn.mmd   # 示例:工作流(中文)
│   └── workflow_cn.png
├── README.md             # 英文文档(默认)
└── README_CN.md          # 中文文档
```
