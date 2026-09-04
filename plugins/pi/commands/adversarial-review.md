---
description: Run a Pi review that challenges the implementation approach and design choices
argument-hint: '[--base <ref>] [--scope auto|working-tree|branch] [--incremental] [--models <m1,m2,...>] [--out-file <path>] [focus ...]'
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Bash(node:*), Bash(git:*), AskUserQuestion
---

Run an adversarial Pi review through the shared plugin runtime.
Position it as a challenge review that questions the chosen implementation, design choices, tradeoffs, and assumptions.
It is not just a stricter pass over implementation defects.

Raw slash-command arguments:
`$ARGUMENTS`

Core constraint:
- This command is review-only.
- Do not fix issues, apply patches, or suggest that you are about to make changes.
- Your only job is to run the review and return Pi's output verbatim to the user.
- Keep the framing focused on whether the current approach is the right one, what assumptions it depends on, and where the design could fail under real-world conditions.

Execution:
- Run the review in the foreground.
- If there is nothing to review (empty working tree and no base branch diff), say so and skip the review.
- `/pi:adversarial-review` uses the same review target selection as `/pi:review`.
- It supports working-tree review, branch review, and `--base <ref>`.
- It does not support `--scope staged` or `--scope unstaged`.
- Unlike `/pi:review`, it can still take extra focus text after the flags.
- `--models <m1,m2,...>` (2+ models) runs the adversarial review as a multi-model panel with merged, consensus-ranked findings.

Foreground flow:
- Run:
```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/pi-companion.mjs" adversarial-review "$ARGUMENTS"
```
- Return the command stdout verbatim, exactly as-is.
- Do not paraphrase, summarize, or add commentary before or after it.
- Do not fix any issues mentioned in the review output.

