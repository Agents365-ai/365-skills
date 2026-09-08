---
description: Delegate investigation, an explicit fix request, or follow-up rescue work to the Pi rescue subagent
argument-hint: "[--background|--wait] [--resume|--fresh] [--model <model>|--race <m1,m2,...>] [--effort <off|minimal|low|medium|high|xhigh|max>] [--out-file <path>] [what Pi should investigate, solve, or continue]"
allowed-tools: Bash(node:*), AskUserQuestion, Agent
---

Invoke the `pi:pi-companion-forwarder` subagent via the `Agent` tool (`subagent_type: "pi:pi-companion-forwarder"`), forwarding the raw user request as the prompt.
`pi:pi-companion-forwarder` is a subagent, not a skill — do not call `Skill(pi:pi-companion-forwarder)` (no such skill) or `Skill(pi:rescue)` (that re-enters this command and hangs the session). The command runs inline so the `Agent` tool stays in scope; forked general-purpose subagents do not expose it.
The final user-visible response must be Pi's output verbatim.

Raw user request:
$ARGUMENTS

Execution mode:

- If the request includes `--background`, run the `pi:pi-companion-forwarder` subagent in the background.
- If the request includes `--wait`, run the `pi:pi-companion-forwarder` subagent in the foreground.
- If neither flag is present, default to foreground.
- `--background` and `--wait` are execution flags for Claude Code. Do not forward them to `task`, and do not treat them as part of the natural-language task text.
- `--model`, `--effort`, and `--out-file` are runtime-selection flags. Preserve them for the forwarded `task` call, but do not treat them as part of the natural-language task text.
- `--out-file <path>` writes Pi's full output to `<path>` and returns only a short summary, keeping a large result out of the conversation to save tokens. Preserve it in the forwarded `task` call; relay the short summary verbatim.
- If the request includes `--resume`, do not ask whether to continue. The user already chose.
- If the request includes `--fresh`, do not ask whether to continue. The user already chose.
- Otherwise, before starting Pi, check for a resumable rescue session from this Claude session by running:

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/pi-companion.mjs" task-resume-candidate --json
```

- If that helper reports `available: true`, use `AskUserQuestion` exactly once to ask whether to continue the current Pi session or start a new one.
- The two choices must be:
  - `Continue current Pi session`
  - `Start a new Pi session`
- If the user is clearly giving a follow-up instruction such as "continue", "keep going", "resume", "apply the top fix", or "dig deeper", put `Continue current Pi session (Recommended)` first.
- Otherwise put `Start a new Pi session (Recommended)` first.
- If the user chooses continue, add `--resume` before routing to the subagent.
- If the user chooses a new session, add `--fresh` before routing to the subagent.
- If the helper reports `available: false`, do not ask. Route normally.

Operating rules:

- The subagent is a thin forwarder only. It should use one `Bash` call to invoke `node "${CLAUDE_PLUGIN_ROOT}/scripts/pi-companion.mjs" task ...` and return that command's stdout as-is.
- Return the Pi companion stdout verbatim to the user.
- Do not paraphrase, summarize, rewrite, or add commentary before or after it.
- Do not ask the subagent to inspect files, monitor progress, poll `/pi:status`, fetch `/pi:result`, call `/pi:cancel`, summarize output, or do follow-up work of its own.
- Leave `--effort` unset unless the user explicitly asks for a specific reasoning effort.
- Leave the model unset unless the user explicitly asks for one.
- `--race <m1,m2,...>` (2+ models) is a model race: the same task runs with every listed model in parallel and the output presents each racer's result so a winner can be picked. With `--write`, each racer runs in an isolated git worktree created from HEAD and its result is captured as a patch (`git apply <patch>` applies the winner). Preserve `--race` in the forwarded `task` call. A race cannot be combined with `--resume`.
- Leave `--resume` and `--fresh` in the forwarded request. The subagent handles that routing when it builds the `task` command.
- If the helper reports that Pi is missing or unconfigured, stop and tell the user to run `/pi:setup`.
- If the user did not supply a request, ask what Pi should investigate or fix.
