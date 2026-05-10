# 365 Skills

[Agents365-ai](https://github.com/Agents365-ai) 出品的生产级 Claude Code 技能集合。

[English](README.md) | 中文

## 安装

```bash
# Claude Code 插件市场
/plugin marketplace add Agents365-ai/365-skills

# 任意 Agent 工具（Claude Code、Cursor、Copilot 等）
npx skills add Agents365-ai/365-skills -g
```

## 可用插件

### 绘图与图表

| 插件 | 说明 |
|---|---|
| `drawio` | Draw.io 流程图 —— 支持 PNG/SVG/PDF 导出与可视化审阅闭环 |
| `mermaid` | Mermaid 图表 —— 文本驱动、GitHub 原生支持、自动布局 |
| `excalidraw` | Excalidraw —— 手绘白板风格 |
| `plantuml` | PlantUML —— UML、C4、时序图、类图 |
| `tldraw` | Tldraw —— 无限画布、草图风格 |

### 科研

| 插件 | 说明 |
|---|---|
| `semanticscholar` | Semantic Scholar —— 学术论文检索、引文图谱、推荐、BibTeX 导出 |
| `paper-fetch` | 按 DOI / 标题下载论文 PDF —— 7 源回退链（Unpaywall、S2、arXiv、PMC、bioRxiv、出版商直链、Sci-Hub），支持批量与幂等重试 |

## 安装插件

```
/plugin install drawio mermaid excalidraw plantuml tldraw semanticscholar paper-fetch
```

## 开发

各插件下的 skills 是源仓库的直接拷贝（非 submodule）。更新某个插件的方式：

```bash
cp -r ../drawio-skill/skills/drawio-skill/* plugins/drawio/skills/drawio-skill/
git add plugins/drawio && git commit -m "chore: sync drawio-skill"
```

### 自动同步（semanticscholar、paper-fetch）

`semanticscholar-skill` 和 `paper-fetch` 各自仓库中带有 GitHub Actions workflow（`.github/workflows/sync-365-skills.yml`），任何对各自 `skills/<name>/**` 的改动会自动推送到本仓库，并更新 `marketplace.json` 中的版本号。需要每个源仓库配置 `SYNC_365_SKILLS_TOKEN` secret，并对本仓库具有 `Contents: write` 权限。

## 源仓库

每个插件都对应一个独立的 skill 仓库 —— 与具体插件相关的 bug 请到对应仓库提交 issue：

| 插件 | 源仓库 |
|---|---|
| `drawio` | [Agents365-ai/drawio-skill](https://github.com/Agents365-ai/drawio-skill) |
| `mermaid` | [Agents365-ai/mermaid-skill](https://github.com/Agents365-ai/mermaid-skill) |
| `excalidraw` | [Agents365-ai/excalidraw-skill](https://github.com/Agents365-ai/excalidraw-skill) |
| `plantuml` | [Agents365-ai/plantuml-skill](https://github.com/Agents365-ai/plantuml-skill) |
| `tldraw` | [Agents365-ai/tldraw-skill](https://github.com/Agents365-ai/tldraw-skill) |
| `semanticscholar` | [Agents365-ai/semanticscholar-skill](https://github.com/Agents365-ai/semanticscholar-skill) |
| `paper-fetch` | [Agents365-ai/paper-fetch](https://github.com/Agents365-ai/paper-fetch) |

## Discord

加入 Discord 交流（面向海外用户）：[https://discord.gg/pCV3P9hNY](https://discord.gg/pCV3P9hNY)

## 微信交流群

扫描下方二维码加入微信交流群，获取帮助、提问和最新动态：

<p align="center">
  <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/agents365ai_wechat_1.png" width="200" alt="微信交流群">
</p>

## 支持

如果这套技能对你有帮助，欢迎打赏支持作者：

<table>
  <tr>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/wechat-pay.png" width="180" alt="微信支付">
      <br>
      <b>微信支付</b>
    </td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/alipay.png" width="180" alt="支付宝">
      <br>
      <b>支付宝</b>
    </td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/buymeacoffee.png" width="180" alt="Buy Me a Coffee">
      <br>
      <b>Buy Me a Coffee</b>
    </td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/awarding/award.gif" width="180" alt="打赏">
      <br>
      <b>打赏</b>
    </td>
  </tr>
</table>

## 作者

**Agents365-ai**

- Bilibili: https://space.bilibili.com/441831884
- GitHub: https://github.com/Agents365-ai

## 其他资源

- [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) —— 社区维护的科研类 skill 合集
- [anthropics/life-sciences](https://github.com/anthropics/life-sciences) —— Anthropic 官方的生命科学 skills
