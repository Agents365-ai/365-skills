# zenodo-skill

一个用于 [Zenodo REST API](https://developers.zenodo.org) 的 Claude Code / OpenClaw 技能。在 Zenodo 上提交、发布、版本化和检索研究产出 —— 每次发布都获得一个可引用的 DOI。

[English](README.md) | 中文

## 功能特性

- **完整的 deposit 生命周期** —— 创建 deposition → 通过 bucket API 上传文件 → 设置元数据 → 发布
- **新版本工作流** —— 在同一个 concept-DOI 下发布更新后的数据 / 代码
- **检索** —— 对已发布记录使用 Elasticsearch 风格的查询(无需鉴权)
- **沙箱优先** —— 默认使用 `sandbox.zenodo.org`,避免误将不可逆的内容发布到生产环境
- **Bucket 文件上传** —— 使用新版 files API(单条记录最多 50 GB / 100 个文件),而非 100 MB 上限的旧接口
- **元数据参考** —— 完整的 `upload_type`、license、条件字段、related_identifiers schema
- **端到端 Shell 示例** —— 数据集上传、软件发布、新版本、批量下载等可直接复用的脚本

## 安装

skill 位于 Agents365-ai 的 skills monorepo；clone 整个 monorepo，再把 skill 目录
链接到 agent 的 skills 路径：

### Claude Code

```bash
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/zenodo/skills/zenodo-skill" ~/.claude/skills/zenodo-skill
```

或按项目维度安装，链接到 `.claude/skills/zenodo-skill/`。

### OpenClaw

```bash
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/zenodo/skills/zenodo-skill" ~/.openclaw/skills/zenodo-skill
```

### SkillsMP

仓库带上标准 topics 后会被自动索引 —— 可直接通过 SkillsMP 市场安装。

## 前置条件

- `curl`(示例脚本推荐配合 `jq`)
- 一个具有 `deposit:write` 与 `deposit:actions` 权限的 Zenodo 个人访问令牌
  - **Sandbox**(测试):https://sandbox.zenodo.org/account/settings/applications/tokens/new/
  - **生产环境**:https://zenodo.org/account/settings/applications/tokens/new/

使用前先设置环境变量:

```bash
export ZENODO_TOKEN=...
export ZENODO_BASE=https://sandbox.zenodo.org/api   # 或 https://zenodo.org/api
```

## 使用方法

直接用自然语言描述需求即可触发本技能:

- "把这个数据集上传到 Zenodo,给我一个 DOI"
- "为我的 Zenodo 记录 1234567 发布一个包含这些文件的新版本"
- "在 Zenodo 上检索今年发布的单细胞 RNA 数据集"
- "先把这个代码 release 提交到 Zenodo 沙箱"

技能会按 创建 → 上传 → 元数据 → 发布 的流程推进 deposit;在执行任何不可逆的生产环境发布前都会请求确认,最终返回 DOI 与记录链接。

## 文件结构

| 文件 | 用途 |
|---|---|
| `SKILL.md` | 工作流、配置与核心 API 调用 |
| `references/metadata.md` | 完整元数据 schema、`upload_type` 取值、license 代码、示例 |
| `references/search.md` | Elasticsearch 查询语法与检索参数 |
| `references/examples.md` | 端到端 Shell 脚本(上传+发布、新版本、列出草稿、下载) |

## 安全策略

- 默认使用 sandbox;生产环境发布需要显式确认
- Token 从 `$ZENODO_TOKEN` 读取 —— 不会内联到任何命令中
- 调用 `actions/publish` 之前会与你一起核对元数据和文件
- 生产环境的发布操作不可逆 —— 文件不能删除,记录也不能撤销

## License

MIT

## 支持作者

如果这个技能对你有帮助,欢迎请作者喝杯咖啡:

<table>
  <tr>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/wechat-pay.png" width="180" alt="WeChat Pay">
      <br>
      <b>微信支付</b>
    </td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/alipay.png" width="180" alt="Alipay">
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

- Bilibili:https://space.bilibili.com/441831884
- GitHub:https://github.com/Agents365-ai
