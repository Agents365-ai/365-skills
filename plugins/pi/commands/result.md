---
description: Show the stored final output for a finished Pi job in this repository
argument-hint: '[job-id] [--out-file <path>]'
disable-model-invocation: true
allowed-tools: Bash(node:*)
---

!`node "${CLAUDE_PLUGIN_ROOT}/scripts/pi-companion.mjs" result "$ARGUMENTS"`

Present the full command output to the user. Do not summarize or condense it. Preserve all details including:
- Job ID and status
- The complete result payload, including verdict, summary, findings, details, artifacts, and next steps
- File paths and line numbers exactly as reported
- Any error messages or parse errors
- Follow-up commands such as `/pi:status <id>` and `/pi:review`

With `--out-file <path>`, the command instead writes the full result to that file and prints only a short summary. In that case, present the short summary verbatim and tell the user the file path — do not try to reconstruct the full output.
