# 安装

[← 返回 README](../README_CN.md)

## 快速安装 —— 让任意 Agent 帮你装

最简单的方式是请任意一个具备编码能力的 Agent(Claude Code、Codex、Cursor、Aider、Gemini CLI……)把仓库克隆到你所在平台的 skills 目录。把 URL 和目标路径一起写在提示里:

```
帮我把 https://github.com/Agents365-ai/agent-native-design 克隆到 ~/.claude/skills/agent-native-design。
```

把示例中的目标路径替换为你所在平台的路径 —— 见本页末尾的 **安装路径汇总** 表。由于提示中已经写明了目标路径,这种方式对任何 Agent 都通用,无需依赖 Agent 是否内置 skills 目录约定。对于手边没有 Agent 的场景(CI、全新机器、无人值守脚本),请使用下面各小节里的手动 `git clone` 指令。

## Claude Code

```bash
# 全局安装(在所有项目中可用)
git clone https://github.com/Agents365-ai/agent-native-design.git ~/.claude/skills/agent-native-design

# 项目级安装
git clone https://github.com/Agents365-ai/agent-native-design.git .claude/skills/agent-native-design
```

## OpenClaw / ClawHub

```bash
# 通过 ClawHub
clawhub install agent-native-design

# 手动安装
git clone https://github.com/Agents365-ai/agent-native-design.git ~/.openclaw/skills/agent-native-design

# 项目级安装
git clone https://github.com/Agents365-ai/agent-native-design.git skills/agent-native-design
```

## Hermes Agent

```bash
git clone https://github.com/Agents365-ai/agent-native-design.git ~/.hermes/skills/engineering/agent-native-design
```

或在 `~/.hermes/config.yaml` 中添加:

```yaml
skills:
  external_dirs:
    - ~/myskills/agent-native-design
```

## pi-mono

```bash
git clone https://github.com/Agents365-ai/agent-native-design.git ~/.pimo/skills/agent-native-design
```

## OpenAI Codex

```bash
# 用户级安装(默认 CODEX_HOME)
git clone https://github.com/Agents365-ai/agent-native-design.git ~/.codex/skills/agent-native-design

# 项目级安装
git clone https://github.com/Agents365-ai/agent-native-design.git .codex/skills/agent-native-design
```

## SkillsMP

```bash
skills install agent-native-design
```

## 安装路径汇总

| 平台 | 全局路径 | 项目路径 |
|------|----------|----------|
| Claude Code | `~/.claude/skills/agent-native-design/` | `.claude/skills/agent-native-design/` |
| OpenClaw | `~/.openclaw/skills/agent-native-design/` | `skills/agent-native-design/` |
| Hermes Agent | `~/.hermes/skills/engineering/agent-native-design/` | 通过 `external_dirs` 配置 |
| pi-mono | `~/.pimo/skills/agent-native-design/` | — |
| OpenAI Codex | `~/.codex/skills/agent-native-design/` | `.codex/skills/agent-native-design/` |
