---
description: Run a Pi code review against local git state
argument-hint: '[--base <ref>] [--scope auto|working-tree|branch] [--incremental] [--models <m1,m2,...>|--shards <N>] [--out-file <path>]'
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Bash(node:*), Bash(git:*), AskUserQuestion
---

Run a Pi review through the shared plugin runtime.

Raw slash-command arguments:
`$ARGUMENTS`

Core constraint:
- This command is review-only.
- Do not fix issues, apply patches, or suggest that you are about to make changes.
- Your only job is to run the review and return Pi's output verbatim to the user.

Execution:
- Run the review in the foreground.
- If there is nothing to review (empty working tree and no base branch diff), say so and skip the review.
- `/pi:review` does not accept extra focus text. If the user needs custom review instructions or more adversarial framing, they should use `/pi:adversarial-review`.
- `--incremental` only reviews commits since the last review on the current branch (cached per branch); falls back to a full review when there is no valid cache (no prior review, or the cached commit is no longer an ancestor of HEAD, e.g. after a rebase). Not combinable with `--base`. Composes with `--models`/`--shards`.
- `--models <m1,m2,...>` (2+ models) runs a multi-model review panel: the same diff is reviewed by every listed model in parallel and the findings are merged, with consensus findings (reported by 2+ models) ranked first.
- `--shards <N>` (N >= 2, and only when more than one file changed) splits the changed files across N review jobs that run in parallel, each scoped to only its own files, then merges the findings into one result. Not combinable with `--models`.
- `--out-file <path>` writes the full review to `<path>` and returns only a short summary (verdict, finding counts, one line per finding) — this keeps a large review out of the conversation's context to save tokens. When it is used, relay the short summary verbatim; the user opens the file for the full detail.

Foreground flow:
- Run:
```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/pi-companion.mjs" review "$ARGUMENTS"
```
- Return the command stdout verbatim, exactly as-is.
- Do not paraphrase, summarize, or add commentary before or after it.
- Do not fix any issues mentioned in the review output.

