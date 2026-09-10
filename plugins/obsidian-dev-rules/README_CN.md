# obsidian-dev-rules

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/Agents365-ai/365-skills?style=flat&logo=github)](https://github.com/Agents365-ai/365-skills/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Agents365-ai/365-skills?style=flat&logo=github)](https://github.com/Agents365-ai/365-skills/network/members)
[![Last Commit](https://img.shields.io/github/last-commit/Agents365-ai/365-skills?logo=github)](https://github.com/Agents365-ai/365-skills/commits/main)

[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-2ea44f)](https://agentskills.io)

[English](README.md) · **中文**

一个 Claude Code / OpenClaw / Pi 技能，把 **Obsidian 开发者文档**（https://docs.obsidian.md）
打包成按需参考，让 agent 无需反复抓取文档即可构建和审查 Obsidian 插件与主题。

镜像 Obsidian 开发者文档，抓取于 2026-05-24。

## 内容结构

- `SKILL.md` — 概览、适用场景、速查表、硬性规则、参考索引。
- `references/plugin-basics.md` — 项目搭建、`manifest.json`、Plugin 生命周期、资源
  注册与清理、事件系统、开发工作流 / 热重载、调试。
- `references/vault-and-editor.md` — Vault API（read/cachedRead/create/modify/process/delete、
  TFile/TFolder、adapter、normalizePath）、Editor API、Markdown 后处理与代码块处理器、
  CodeMirror 6 编辑器扩展。
- `references/ui.md` — 命令（callback 变体、快捷键）、设置（PluginSettingTab、load/saveData、
  Setting 控件）、模态框（Modal/SuggestModal/FuzzySuggestModal）、视图（ItemView、
  registerView、workspace leaves）、ribbon/状态栏。
- `references/themes-and-release.md` — 主题（CSS 变量、theme.css/manifest、body 类、
  snippets）、插件与主题的提交发布、开发者政策与准则。

## 安装

| 平台 | 路径 |
|----------|------|
| Claude Code（全局） | `~/.claude/skills/obsidian-dev-rules/` |
| Claude Code（项目级） | `.claude/skills/obsidian-dev-rules/` |
| OpenClaw（全局） | `~/.openclaw/skills/obsidian-dev-rules/` |
| Pi（全局） | `~/.pi/agent/skills/obsidian-dev-rules/` |
| Pi（项目级） | `.pi/skills/obsidian-dev-rules/` |

```bash
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/obsidian-dev-rules/skills/obsidian-dev-rules" ~/.claude/skills/obsidian-dev-rules
```

## 相关技能

与 Obsidian *使用类*技能（obsidian-cli、obsidian-markdown、json-canvas、obsidian-bases）互补；
本技能面向 Plugin/Vault/Editor API、主题与社区提交流程的**开发参考**。

## 更新

重新抓取 https://docs.obsidian.md 下的页面并重新生成 `references/`；同步更新
`SKILL.md` 中的 `metadata.fetched`。

## 支持

如果这个技能对你有帮助，欢迎支持作者：

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

**Agents365-ai** &mdash; 为 AI 编码代理构建开源技能。

- Bilibili：<https://space.bilibili.com/441831884>
- GitHub：<https://github.com/Agents365-ai>

## 许可证

[MIT](LICENSE)（本技能的打包）。Obsidian 文档内容版权归 Dynalist Inc. / Obsidian 团队所有。