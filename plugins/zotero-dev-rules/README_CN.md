# zotero-dev-rules

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/Agents365-ai/365-skills?style=flat&logo=github)](https://github.com/Agents365-ai/365-skills/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Agents365-ai/365-skills?style=flat&logo=github)](https://github.com/Agents365-ai/365-skills/network/members)
[![Last Commit](https://img.shields.io/github/last-commit/Agents365-ai/365-skills?logo=github)](https://github.com/Agents365-ai/365-skills/commits/main)

[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-2ea44f)](https://agentskills.io)

[English](README.md) · **中文**

一个 Claude Code / OpenClaw / Pi 技能，把 **Zotero 开发者文档**
（<https://www.zotero.org/support/dev）打包成按需查阅的参考，让代理无需重复抓取文档即可调用>
Web API、构建插件、编写转换器（translator）和制作引文样式。

镜像 Zotero 开发文档（Web API **v3**），抓取日期 2026-08-18。

<p align="center">
  <img src="assets/workflow-cn.png" width="560" alt="zotero-dev-rules 工作流程">
</p>

## 内容

- `SKILL.md` — 概览、使用时机、速查表、硬性规则、参考索引。
- `references/web-api.md` — 基础 URL、认证/API key、版本控制、读写请求、批量操作、文件
  上传、条目类型/字段、基于版本的同步算法、流式 API、OAuth。
- `references/client-and-plugins.md` — 客户端内部 JavaScript API（Items/Search/DB/Notifier）、
  Run JavaScript、Zotero 7 引导式（bootstrapped）插件开发、Zotero 10 迁移说明。
- `references/translators.md` — 转换器元数据、detectWeb/doWeb/doImport/doExport/doSearch、
  抓取辅助函数、HTTP 请求辅助函数、调用其他转换器、Scaffold 测试。
- `references/citation-styles.md` — CSL、citeproc-js / citeproc-node、样式仓库、样式编辑、
  通过 Web API 渲染引文。
- `references/plugin-gallery.md` — zotero-chinese 插件商店注册表快照（137 个插件按标签分组 +
  废弃名单）：开发新插件前先检索相似功能的开源插件并研读其代码。

## 安装

| 平台 | 路径 |
| ------ | ------ |
| Claude Code（全局） | `~/.claude/skills/zotero-dev-rules/` |
| Claude Code（项目） | `.claude/skills/zotero-dev-rules/` |
| OpenClaw（全局） | `~/.openclaw/skills/zotero-dev-rules/` |
| Pi（全局） | `~/.pi/agent/skills/zotero-dev-rules/` |
| Pi（项目） | `.pi/skills/zotero-dev-rules/` |

```bash
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/zotero-dev-rules/skills/zotero-dev-rules" ~/.claude/skills/zotero-dev-rules   # 示例：Claude Code 全局安装
```

## 相关技能

与 [`zotero-manager`](https://github.com/Agents365-ai/zotero-manager) 和
[`zotero-research-assistant`](https://github.com/Agents365-ai/zotero-research-assistant)（工作流
技能）搭配使用；本技能是面向 API、插件、转换器和 CSL 的**开发者参考**。

## 更新

重新抓取 <https://www.zotero.org/support/dev> 下的页面并重新生成 `references/`；同时更新
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

[CC BY-NC 4.0](LICENSE) — 非商业用途免费使用，商业使用需获得授权。

Zotero 文档内容 © Corporation for Digital Scholarship；Zotero 转换器为 AGPL v3；
CSL 样式为 CC BY-SA。
