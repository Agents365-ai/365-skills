# 功能特性与对比

[← 返回 README](https://github.com/Agents365-ai/365-skills/blob/main/plugins/plantuml/README_CN.md)

## 对比

### 与无 skill 的原生智能体对比

| 功能 | 原生智能体 | 本 skill |
| ------ | ----------- | --------- |
| 生成 PlantUML 源码 | 是 — LLM 本身了解语法 | 是 |
| 导出为 PNG/SVG | 否 — 仅输出文本 | 是 — 一次 `curl` POST 到 Kroki |
| 渲染器选择 | 无 | 公共 Kroki / 本地 Kroki / `plantuml.jar` |
| 主动触发 | 否 — 仅在明确要求时 | 是 — 3+ 组件、API、类层次、状态机时自动建议 |
| 图表类型目录 | 隐式 | 10+ 种,附形状词汇、箭头词汇、多重性标记 |
| 主题默认值 | 每次随机 | `!theme plain` 基线 + 精选低饱和度配色 |
| 云端 C4 图 | 经常失效(`!include` 404) | 使用 Kroki 的 `c4plantuml` 端点(已预合并 includes) |
| 常见错误清单 | 无 | 9 类已知坑(箭头方向、布局溢出、标签转义、参与者顺序等) |
| 离线支持 | 否 | 是 — 本地 Kroki Docker 或本地 jar |

### 与其他 PlantUML 方案对比

| 方案 | 安装体积 | 离线 | 智能体感知 | 备注 |
| ------ | --------- | ------ | ----------- | ------ |
| **本 skill(Kroki API)** | 仅 `curl` | 可选(Docker) | 是 | 默认方案,零安装 |
| **本 skill(本地 Kroki)** | Docker | 是 | 是 | 单容器,无需 Java |
| **本 skill(`plantuml.jar`)** | Java + Graphviz + jar | 是 | 是 | 体积最大但默认离线 |
| 公共 PlantUML 网站 | 仅浏览器 | 否 | 手动 | 智能体无法脚本化调用 |
| `node-plantuml` / npm 包装 | Node + Java | 是 | 否 | 仍是同一个 jar 的封装 |
| VS Code PlantUML 扩展 | 编辑器 + Java | 是 | 否 | 编写时使用,不适合智能体 |

## 核心优势

1. **零安装默认值** — `curl` 无处不在;macOS、Linux、Windows(Git Bash / WSL)开箱即用
2. **三种渲染路径** — 公共 Kroki 求快、本地 Kroki 求离线/隐私、jar 包应对气隙环境
3. **图表类型剧本** — 10+ 种图表都有可复制的语法模板、形状词汇、箭头规范
4. **常见错误规避** — SKILL.md 内置精选"Common Mistakes"表,覆盖箭头方向、布局溢出、标签转义、参与者顺序、C4 includes 等坑
5. **多智能体单文件** — 一个 `SKILL.md` 跑通 Claude Code、Opencode、OpenClaw、Hermes、Codex、SkillsMP

## 支持的图表类型

- **时序图**:API 调用、OAuth 流程、协议追踪 — 含生命线、激活框、异步箭头
- **组件 / 架构图**:服务、模块、队列、数据库、云 — 含 package/rectangle 分组
- **类图**:OOP 模型 — 继承、组合、聚合、多重性(`"1" --> "*"`)
- **ER / 实体图**:数据库 schema — `<<PK>>` / `<<FK>>` 标记,crow's-foot 关系
- **活动图**:工作流、业务流程、决策分支 — `if/then/else/endif` 语法
- **用例图**:参与者、系统边界、用户故事
- **状态图**:状态机、生命周期 — `[*] -->` 起止标记
- **C4**:Context、Container、Component 图 — 通过 Kroki `c4plantuml` 端点
- **其他**:思维导图(`@startmindmap`)、Gantt(`@startgantt`)
