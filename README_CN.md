# 365 Skills

[![GitHub stars](https://img.shields.io/github/stars/Agents365-ai/365-skills?style=flat&logo=github)](https://github.com/Agents365-ai/365-skills/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Agents365-ai/365-skills?style=flat&logo=github)](https://github.com/Agents365-ai/365-skills/network/members)
[![Last Commit](https://img.shields.io/github/last-commit/Agents365-ai/365-skills?logo=github)](https://github.com/Agents365-ai/365-skills/commits/main)

[![SkillsMP](https://img.shields.io/badge/SkillsMP-listed-1f6feb)](https://skillsmp.com)
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-plugin-8a2be2)](https://github.com/Agents365-ai/365-skills)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-2ea44f)](https://agentskills.io)

[Agents365-ai](https://github.com/Agents365-ai) 出品，面向各类 AI 编码智能体的生产级技能集合。与 Agent 无关，兼容 Claude Code、Cursor、Copilot、OpenClaw 等。

[English](README.md) | 中文

## 安装

```bash
# 任意 Agent 工具（Claude Code、Cursor、Copilot 等）—— 与 Agent 无关
npx skills add Agents365-ai/365-skills -g

# Claude Code 插件市场（可选）
/plugin marketplace add Agents365-ai/365-skills
```

单插件的 Claude Code 安装：`/plugin install <插件名>`，例如 `/plugin install drawio`。

## 可用插件

### 开发与 CLI 设计

| 插件 | 说明 |
| --- | --- |
| `agent-native-design` | AI 智能体 CLI 设计 —— 评估、设计和重构 CLI，使其能同时服务人类、AI 智能体和编排系统 |
| `pi-plugin-cc` | 从 Claude Code 驱动 Pi coding agent —— 模型无关的任务委派与代码审查。`/pi:review` 结构化发现、`/pi:adversarial-review`、`/pi:rescue`、`/pi:parallel-rescue`，跨 provider 竞速/回退，增量审查 |

### 绘图与图表

| 插件 | 说明 |
| --- | --- |
| `drawio` | Draw.io 流程图 —— 支持 PNG/SVG/PDF 导出与可视化审阅闭环 |
| `mermaid` | Mermaid 图表 —— 文本驱动、GitHub 原生支持、自动布局 |
| `excalidraw` | Excalidraw —— 手绘白板风格 |
| `plantuml` | PlantUML —— UML、C4、时序图、类图 |
| `tldraw` | Tldraw —— 无限画布、草图风格 |

### 科研

| 插件 | 说明 |
| --- | --- |
| `semanticscholar` | Semantic Scholar —— 学术论文检索、引文图谱、推荐、BibTeX 导出 |
| `paper-fetch` | 按 DOI / 标题下载论文 PDF —— 7 源回退链（Unpaywall、S2、arXiv、PMC、bioRxiv、出版商直链、Sci-Hub），支持批量与幂等重试 |
| `scholar-deep-research` | 端到端文献综述流水线 —— 8 阶段脚本驱动工作流，跨 7 个数据源（OpenAlex、arXiv、Crossref、PubMed、DBLP、bioRxiv、Exa）联邦检索、去重、双 backend 引用追溯、并行精读派发、强制自我批判，输出 5 种原型的带引用报告 |
| `asta` | Ai2 Asta MCP —— Semantic Scholar 学术图谱以 MCP 暴露（无需 Python）。意图到工具的路由、安全 `fields` 默认值（避免上下文炸开）、引文遍历、片段证据检索，并通过 `externalIds` 获取 DOI / arXiv / PMID |
| `journal-abbrev` | 期刊名称缩写查询 —— 支持 ISO 4 与 MEDLINE 两种标准，多源级联（JabRef → AbbrevISO → NLM）、BibTeX 字段批量重写并支持 `--idempotency-key` 幂等重试、原子缓存重建，agent-native JSON 信封带稳定错误码与 dry-run |
| `journal-if` | 期刊影响因子（JCR IF）查询 —— 按名称查期刊 IF、跨期刊比较、评估投稿期刊档次，内置 `journals_if.csv` 数据集 |
| `target-prioritization` | 多源药物靶点尽职调查 —— 将排序基因列表（如 scRNA-seq 差异表达输出）转化为逐基因档案（UniProt、OpenTargets、PubMed），叠加本地跨谱系差异表达扫描，再按可配置综合评分（跨谱系趋同 + 成药性 + 疾病遗传学 + 可开发性 + 新颖性）重排。疾病无关，可配置靶疾病与细胞上下文查询 |
| `figshare` | Figshare v2 REST API —— 搜索公开数据集/文章、按 ID/DOI/URL 批量下载文件，并可对自己账号的文章进行创建、更新、发布与多分片上传（大文件三步上传流程） |

### 知识与笔记

| 插件 | 说明 |
|---|---|
| `obsidian-organizer` | 让庞大的 Obsidian 仓库保持整洁 —— 把新笔记归入最合适的文件夹，并按需审计/重组已有结构，以仓库内的唯一权威地图笔记（`00_Index/Folder_Map.md`）为准。设计上保证链接安全（移动/重命名都走 `obsidian` CLI，wikilink 自动修复，禁止裸 shell），批量重组先出方案再确认 |

### 媒体与创意

| 插件 | 说明 |
| --- | --- |
| `ttscn` | 多平台中文语音合成 —— 14 个后端（Edge/豆包/CosyVoice/通义千问/StepFun/智谱/Azure/腾讯/百度/MiniMax/讯飞/ElevenLabs/OpenAI/Google），agent-native CLI 带 JSON 信封、schema 自省、音色克隆、SSML、情感、方言、可过滤 HTML 对比页 |
| `imagencn` | AI 图像生成，接入阿里百炼、字节火山方舟与腾讯混元 —— 23 个模型，中文文字出图表现优秀，富终端 UI，智能配置 |
| `videogencn` | 中国视频模型 AI 视频片段生成 —— 文生视频、图生视频、首尾帧与参考图生视频，覆盖百炼（Wan/PixVerse/Kling/Vidu）、即梦（doubao-seedance）、MiniMax（海螺）、混元 |
| `assetseeker` | 免费商用创意素材检索 —— 照片、插画、图标、视频片段、音乐、音效与字体，覆盖 Pexels、Unsplash、Pixabay、Iconify、Freesound、Google Fonts 等 |
| `video-podcast-maker` | 自动化主题驱动视频播客制作 —— 选题研究 → 脚本 → TTS（7 后端）→ 4K Remotion 渲染 → BGM 混音 → Remotion 原生字幕。多平台输出（B 站 / YouTube / 小红书 / 抖音 / 视频号），横版长视频（16:9 4K）与竖版 shorts（9:16），15 步工作流强制 Studio 预览 |
| `bangumi-frames` | B 站番剧帧与角色整理 —— 下载番剧/UP 主视频（或本地文件），抽取场景切换关键帧，拆分风景与角色裁剪，按 CCIP 身份聚类或通过参考文件夹提取单个角色；可选 OCR+LaMa 去字幕/水印 |
| `yt2bb` | YouTube 视频搬运至 B 站 —— yt-dlp 下载、whisper 转写、生成中英双语 SRT 字幕并用 ffmpeg 硬编码 |

## 开发

各插件下的 skills 是源仓库的直接拷贝（非 submodule）。本仓库是集中分发点：先更新源 skill 仓库，再把更新拷贝到这里，并在 `.claude-plugin/marketplace.json` 中 bump 对应插件的 `version`：

```bash
cp -r ../drawio-skill/skills/drawio-skill/* plugins/drawio/skills/drawio-skill/
# 在 .claude-plugin/marketplace.json 中 bump 对应插件版本
git add plugins/drawio && git commit -m "chore: sync drawio-skill"
```

多数源仓库现已转为私有；对这部分插件而言，本 marketplace 是唯一分发渠道。

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

- Bilibili: <https://space.bilibili.com/441831884>
- GitHub: <https://github.com/Agents365-ai>
