# figshare-skill — 命令行下的 Figshare v2 API

[English](README.md) | [Figshare API 文档](https://docs.figshare.com/)

## 功能特性

- **搜索** Figshare 公开文章，支持字段操作符（`:title:`、`:author:`、`:tag:`、`:category:`、`:doi:`）
- **批量下载** 一篇公开文章的全部文件，支持 ID / DOI / `figshare.com` URL
- **列表 / 创建 / 更新 / 发布** 自己的文章，覆盖草稿与版本发布流程
- **多分片上传**，封装 `initiate → PUT parts → complete` 三步流程，自动处理 md5 与分片大小
- **新版本发布** —— 已发布版本不可修改，新版本通过脚本一步完成
- **Collections / Projects** 管理
- 当用户提到 Figshare、`figshare.com` 链接或 `10.6084/m9.figshare.*` DOI 时自动触发

## 多平台支持

适配所有支持 [Agent Skills](https://agentskills.io) 格式的 AI 编程助手：

| 平台 | 状态 | 说明 |
| ------ | ------ | ------ |
| **Codex** | ✅ 完全支持 | 原生 `SKILL.md` + `agents/openai.yaml` 界面元数据 |
| **Claude Code** | ✅ 完全支持 | 原生 SKILL.md 格式 |
| **OpenClaw** | ✅ 完全支持 | `metadata.openclaw` 命名空间 |
| **SkillsMP** | ✅ 已收录 | GitHub topics 已配置 |

## 对比

### vs 原生 Agent（无技能）

| 能力 | 原生 Agent | 本技能 |
| ------ | ----------- | -------- |
| 知道 Figshare 基础 URL 与认证头 | 或许 | ✅ |
| 搜索字段操作符（`:title:`、`:author:` 等） | ❌ | ✅ |
| 从 ID / DOI / URL 批量下载公开文章 | ❌ | ✅ 脚本 |
| 多分片上传（`initiate → parts → complete`） | ⚠️ 每次重写 | ✅ `upload.sh` |
| 自动处理 md5 / 大小 / 分片布局 | ❌ | ✅ |
| 新版本发布 | ❌ | ✅ `new-version.sh` |
| 发布 / 删除前确认 | ❌ | ✅ |
| 可复制即用的 `curl` + `jq` 示例 | ❌ | ✅ |

## 前置条件

- `curl`
- `jq`
- 所有涉及 `/account/...` 或上传的操作需要 [Figshare Personal Token](https://figshare.com/account/applications)：

  ```bash
  export FIGSHARE_TOKEN=xxxxxxxxxxxxxxxx
  ```

公开搜索 / 获取文章 / 下载不需要 token。

## 安装

skill 位于 Agents365-ai 的 skills monorepo；clone 整个 monorepo，再把 skill 目录
链接到 agent 的 skills 路径：

### Codex

```bash
# 全局安装（Codex 自动发现）
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/figshare/skills/figshare-skill" ~/.codex/skills/figshare-skill
```

### Claude Code

```bash
# 全局安装（所有项目可用）
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/figshare/skills/figshare-skill" ~/.claude/skills/figshare-skill

# 项目级安装
ln -s "$(pwd)/365-skills/plugins/figshare/skills/figshare-skill" .claude/skills/figshare-skill
```

### OpenClaw

```bash
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/figshare/skills/figshare-skill" ~/.openclaw/skills/figshare-skill

# 项目级
ln -s "$(pwd)/365-skills/plugins/figshare/skills/figshare-skill" skills/figshare-skill
```

### SkillsMP

在 [SkillsMP](https://skillsmp.com) 搜索或使用 CLI：

```bash
skills install figshare-skill
```

### 安装路径汇总

| 平台 | 全局路径 | 项目路径 |
| ------ | ---------- | ---------- |
| Codex | `~/.codex/skills/figshare-skill/` | N/A |
| Claude Code | `~/.claude/skills/figshare-skill/` | `.claude/skills/figshare-skill/` |
| OpenClaw | `~/.openclaw/skills/figshare-skill/` | `skills/figshare-skill/` |
| SkillsMP | N/A（CLI 安装） | N/A |

## 使用示例

直接描述你想做什么：

```
> 使用 $figshare-skill 搜索 figshare 上的 "single cell" 数据集，并返回前 10 条

> 在 figshare 上搜索 "single cell" 数据集，返回前 10 条

> 把 https://figshare.com/articles/dataset/xxx/31957606 的全部文件下载到 ./data

> 把 ./results.zip 上传到我的草稿文章 31957803

> 为已发布文章 12345678 创建并发布一个新版本，新文件是 ./v2.csv
```

技能会自动选对端点、补齐认证，并调用内置脚本完成多分片上传。

## 辅助脚本

| 脚本 | 用途 |
| ------ | ------ |
| `scripts/upload.sh <article_id> <file>` | 三步式多分片上传到草稿文章 |
| `scripts/download.sh <id_or_url> [dir]` | 公开文章批量下载 |
| `scripts/new-version.sh <article_id> <file>` | 预留、上传并发布新版本 |

全部脚本从环境变量读取 `FIGSHARE_TOKEN`，只依赖 `curl` 与 `jq`。

## 文件说明

- `SKILL.md` —— **唯一必需的文件**，所有平台都会加载它作为技能指令
- `agents/openai.yaml` —— Codex 的技能 UI 元数据，用于发现与快捷提示
- `scripts/upload.sh` —— 多分片上传
- `scripts/download.sh` —— 批量下载
- `scripts/new-version.sh` —— 新版本工作流
- `README.md` —— 英文文档（GitHub 首页展示）
- `README_CN.md` —— 本文件

## 已知限制

- **`dd bs=1` 在极大分片上偏慢**：数 GB 以内的分片没问题，单文件超大场景建议改为 `bs=1M` + `skip=`/`count=`
- **速率限制**：Figshare 未公布硬限，但建议 ≤1 req/sec，脚本未内置节流
- **已发布版本不可修改**：修改内容必须走 `new-version.sh`，不能 `update`
- **Categories / licenses 是数字 ID**：创建文章前用 `GET /v2/categories` 和 `GET /v2/licenses` 查表

## License

MIT

## 赞赏

如果这个技能对你有帮助，欢迎赞赏作者：

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
  </tr>
</table>

## 作者

**Agents365-ai**

- Bilibili: <https://space.bilibili.com/441831884>
- GitHub: <https://github.com/Agents365-ai>
