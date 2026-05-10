# 365 Skills

[Agents365-ai](https://github.com/Agents365-ai) 出品的生产级 Claude Code 技能集合。

[English](README_EN.md) | 中文

## 安装

```bash
# Claude Code 插件市场
/plugin marketplace add Agents365-ai/365-skills

# 任意 Agent 工具（Claude Code、Cursor、Copilot 等）
npx skills add Agents365-ai/365-skills -g
```

## 可用插件

| 插件 | 说明 |
|---|---|
| `drawio` | Draw.io 流程图 —— 支持 PNG/SVG/PDF 导出与可视化审阅闭环 |
| `mermaid` | Mermaid 图表 —— 文本驱动、GitHub 原生支持、自动布局 |
| `excalidraw` | Excalidraw —— 手绘白板风格 |
| `plantuml` | PlantUML —— UML、C4、时序图、类图 |
| `tldraw` | Tldraw —— 无限画布、草图风格 |
| `semanticscholar` | Semantic Scholar —— 学术论文检索、引文图谱、推荐、BibTeX 导出 |

## 安装插件

```
/plugin install drawio mermaid excalidraw plantuml tldraw semanticscholar
```

## 开发

各插件下的 skills 是源仓库的直接拷贝（非 submodule）。更新某个插件的方式：

```bash
cp -r ../drawio-skill/skills/drawio-skill/* plugins/drawio/skills/drawio-skill/
git add plugins/drawio && git commit -m "chore: sync drawio-skill"
```

### 自动同步（semanticscholar）

`semanticscholar-skill` 仓库中带有一个 GitHub Actions workflow（`.github/workflows/sync-365-skills.yml`），任何对 `skills/semanticscholar-skill/**` 的改动会自动推送到本仓库，并更新 `marketplace.json` 中的版本号。需要源仓库配置 `SYNC_365_SKILLS_TOKEN` secret，并对本仓库具有 `Contents: write` 权限。

## 社区与交流

- **Issue 与功能建议**：[github.com/Agents365-ai/365-skills/issues](https://github.com/Agents365-ai/365-skills/issues)
- **讨论区**：[github.com/Agents365-ai/365-skills/discussions](https://github.com/Agents365-ai/365-skills/discussions)
- **组织主页**：[github.com/Agents365-ai](https://github.com/Agents365-ai)
- **联系邮箱**：niehu2025@gmail.com

### 源仓库

每个插件都对应一个独立的 skill 仓库 —— 与具体插件相关的 bug 请到对应仓库提交 issue：

| 插件 | 源仓库 |
|---|---|
| `drawio` | [Agents365-ai/drawio-skill](https://github.com/Agents365-ai/drawio-skill) |
| `mermaid` | [Agents365-ai/mermaid-skill](https://github.com/Agents365-ai/mermaid-skill) |
| `excalidraw` | [Agents365-ai/excalidraw-skill](https://github.com/Agents365-ai/excalidraw-skill) |
| `plantuml` | [Agents365-ai/plantuml-skill](https://github.com/Agents365-ai/plantuml-skill) |
| `tldraw` | [Agents365-ai/tldraw-skill](https://github.com/Agents365-ai/tldraw-skill) |
| `semanticscholar` | [Agents365-ai/semanticscholar-skill](https://github.com/Agents365-ai/semanticscholar-skill) |
