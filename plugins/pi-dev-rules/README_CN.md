# pi-dev-rules

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/Agents365-ai/pi-dev-rules?style=flat&logo=github)](https://github.com/Agents365-ai/pi-dev-rules/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Agents365-ai/pi-dev-rules?style=flat&logo=github)](https://github.com/Agents365-ai/pi-dev-rules/network/members)
[![Latest Release](https://img.shields.io/github/v/release/Agents365-ai/pi-dev-rules?logo=github)](https://github.com/Agents365-ai/pi-dev-rules/releases/latest)
[![Last Commit](https://img.shields.io/github/last-commit/Agents365-ai/pi-dev-rules?logo=github)](https://github.com/Agents365-ai/pi-dev-rules/commits/main)

[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-2ea44f)](https://agentskills.io)

中文 · [English](README.md)

一个编程助手技能，将最新的 [Pi](https://pi.dev) 文档（`@earendil-works/pi-coding-agent`）
打包为按需参考库，让助手无需重新抓取文档即可安装、配置、运行和**扩展 Pi**。

镜像 <https://pi.dev/docs/latest（抓取日期：2026-07-26）。>

适用于 Claude Code、Cursor、Codex、Copilot、Windsurf、Cline / Roo Code、Gemini CLI、
Aider、Zed、OpenCode、OpenClaw / ClawHub、Hermes、pi-mono — 以及主流国产编程助手
（Trae、Qwen Code / 通义灵码、百度 Comate、CodeGeeX）— 和任何支持 `AGENTS.md`
或 [Agent Skills](https://agentskills.io) 格式的工具。

<p align="center">
  <img src="assets/workflow-zh.png" width="700" alt="pi-dev-rules 工作流程">
</p>

## 包含内容

- `SKILL.md` — 概述、使用时机、速查表、硬性规则、参考索引。
- `references/cli-and-usage.md` — 安装、认证、CLI 参数、斜杠命令、消息队列、上下文
  文件、环境变量、会话、快捷键。
- `references/providers-and-models.md` — 提供商（30+）、`auth.json`（+ scoped `env`）、云
  提供商、自定义 `models.json`、`compat`、自定义提供商扩展。
- `references/settings-and-compaction.md` — `settings.json`（trust/analytics/retry/transport）、
  自动/手动压缩、分支摘要。
- `references/extending-pi.md` — 扩展 API、技能（SKILL.md）、提示模板、主题、包。
- `references/tui-components.md` — 自定义扩展/工具 UI 的 TUI 组件系统。
- `references/security-and-containerization.md` — 项目信任模型、无内置沙箱、Gondolin
  微型虚拟机、Docker、OpenShell。
- `references/session-format.md` — 会话 JSONL 架构、消息/条目类型、SessionManager API。
- `references/programmatic.md` — SDK、RPC 模式、JSON 事件流模式。
- `references/platform-setup.md` — Windows、Termux、tmux、终端设置、shell 别名、
  从源码构建。
- `references/development.md` — 从源码构建 Pi、monorepo 结构、fork/重命名、
  调试。
- `references/philosophy-and-design.md`（作者的设计宣言，Mario Zechner 的博客文章，2025-11-30）：
  为何极简、4 工具哲学、默认 YOLO、明确的非功能特性（无 MCP / 无计划模式 / 无待办 / 无子代理 /
  无后台 bash）及其预期替代方案。

## 安装

| 平台 | 路径 |
| ------ | ------ |
| Claude Code（全局） | `~/.claude/skills/pi-dev-rules/` |
| Claude Code（项目） | `.claude/skills/pi-dev-rules/` |
| OpenClaw（全局） | `~/.openclaw/skills/pi-dev-rules/` |
| Pi（全局） | `~/.pi/agent/skills/pi-dev-rules/` |
| Pi（项目） | `.pi/skills/pi-dev-rules/` |

```bash
cp -r pi-dev-rules ~/.claude/skills/      # 示例：Claude Code，全局
```

## 更新

重新抓取 <https://pi.dev/docs/latest> 下的页面并重新生成 `references/` 文件；更新
`SKILL.md` 中的 `metadata.fetched`。

## 支持

如果这个项目对你有帮助，欢迎支持作者：

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
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/awarding/award.gif" width="180" alt="打赏作者">
      <br>
      <b>打赏作者</b>
    </td>
  </tr>
</table>

## 作者

**Agents365-ai**

- Bilibili: <https://space.bilibili.com/441831884>
- GitHub: <https://github.com/Agents365-ai>

## 许可证

[MIT](LICENSE)
