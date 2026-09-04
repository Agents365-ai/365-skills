---
description: Cancel an active background Pi job in this repository
argument-hint: '[job-id]'
disable-model-invocation: true
allowed-tools: Bash(node:*)
---

!`node "${CLAUDE_PLUGIN_ROOT}/scripts/pi-companion.mjs" cancel "$ARGUMENTS"`
