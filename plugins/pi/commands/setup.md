---
description: Check whether the local Pi CLI is ready and optionally toggle the stop-time review gate
argument-hint: '[--enable-review-gate|--disable-review-gate]'
allowed-tools: Bash(node:*), Bash(npm:*), AskUserQuestion
---

Run:

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/pi-companion.mjs" setup --json $ARGUMENTS
```

If the result says Pi is unavailable and npm is available:
- Use `AskUserQuestion` exactly once to ask whether Claude should install Pi now.
- Put the install option first and suffix it with `(Recommended)`.
- Use these two options:
  - `Install Pi (Recommended)`
  - `Skip for now`
- If the user chooses install, run:

```bash
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
```

- Then rerun:

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/pi-companion.mjs" setup --json $ARGUMENTS
```

If Pi is already installed or npm is unavailable:
- Do not ask about installation.

Output rules:
- Present the final setup output to the user.
- If installation was skipped, present the original setup output.
- If Pi is installed but no provider is configured, preserve the guidance to set a provider API key (e.g. `DEEPSEEK_API_KEY`) or write `~/.pi/agent/models.json` per pi's `providers.md`.
