---
description: Delegate multiple independent tasks to Pi for parallel execution via pi-subagents
argument-hint: '"task1" "task2" ... [--model <model>] [--effort <off|minimal|low|medium|high|xhigh|max>]'
allowed-tools: Bash(node:*), AskUserQuestion
---

Run multiple independent tasks in parallel through Pi using pi-subagents.

First, check that pi-subagents is installed:
```bash
test -d ~/.pi/agent/extensions/subagent && echo "installed" || echo "not-installed"
```

If the output is "not-installed", tell the user:
"pi-subagents is not installed. Run `pi install npm:pi-subagents` to enable parallel subagent execution."
Then STOP — do not proceed.

Read the parallel-rescue prompt template:
```bash
cat "${CLAUDE_PLUGIN_ROOT}/prompts/parallel-rescue.md"
```

Parse $ARGUMENTS into individual tasks. Each shell-quoted string is one task. Strip any runtime flags (--model, --effort) from the task list — those go to the pi-companion invocation, not the prompt.

Construct the prompt by replacing `{{TASKS_LIST}}` in the template with an enumerated list:

```
Task 1: <first task text>
Task 2: <second task text>
...
```

Run the task through the companion:
```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/pi-companion.mjs" task --write "${PROMPT}"
```

Return the stdout verbatim — do not paraphrase, summarize, or add commentary.
