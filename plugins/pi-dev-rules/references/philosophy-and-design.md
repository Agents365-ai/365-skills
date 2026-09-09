# Pi: Design Philosophy and Opinionated Choices

Source: <https://mariozechner.at/posts/2025-11-30-pi-coding-agent/> (Mario Zechner, "What I learned
building an opinionated and minimal coding agent", 2025-11-30). Manually curated summary, not
auto-built; content summarized with attribution, short quotes preserved. The blog predates the move
to the `@earendil-works` org and the current docs at pi.dev.

---

> **Why this file matters.** It explains WHY Pi looks the way it does: minimal core, exactly four
> tools, YOLO by default, and deliberate non-features (no MCP, no plan mode, no to-dos, no
> sub-agents, no background bash). Read it before writing extensions or choosing a configuration so
> your customization follows the intended design instead of fighting it. When a request would add an
> MCP server, a sub-agent, or a plan-mode ceremony, check here first: the author's intended
> alternative is usually a plain file (TODO.md / PLAN.md), a CLI tool with a README, or tmux.

## Author & origin

- Mario Zechner (github.com/badlogic), published 2025-11-30.
- Path: three years of LLM-assisted coding, ChatGPT → Copilot → Cursor → coding-agent harnesses
  (Claude Code, Codex, Amp, Droid, opencode). Preferred Claude Code but found it grew into a
  "spaceship" with ~80% unused functionality; system prompt and tools changed on every release
  ("flicker").
- Built **pi** as a minimal, opinionated harness. The name is intentionally un-Google-able ("it
  will never have any users"). Code lives in the **pi-mono** repo: four packages `pi-ai`,
  `pi-agent-core`, `pi-tui`, `pi-coding-agent`.
- The project has since moved to the `@earendil-works` org (package
  `@earendil-works/pi-coding-agent`, docs at pi.dev); the rest of this skill mirrors those current
  docs.

## Core thesis

1. Context engineering is paramount, but existing harnesses make it "extremely hard or impossible"
   by injecting content behind the user's back.
2. Every aspect of model interaction must be inspectable; sessions need a cleanly documented format
   for post-processing and alternative UIs.
3. Self-hosted models work poorly through the Vercel AI SDK's tool-calling support, so build on the
   provider SDKs directly (cf. Armin Ronacher's "agents-are-hard").
4. "If I don't need it, it won't be built."

## Minimal system prompt (under 1000 tokens)

- The full system prompt starts "You are an expert coding assistant.", lists the 4 tools, adds ~5
  guidelines (e.g. "Use bash for file operations like ls, grep, find"; "Use edit for precise
  changes"; "Be concise in your responses"), and points at its own README for documentation.
- The only injected content is the user's `AGENTS.md` (global + project, hierarchical). Users can
  replace the entire system prompt.
- Combined prompt + tool definitions come in **below 1000 tokens** versus roughly 10,000 for Claude
  Code. Rationale: frontier models are "RL-trained up the wazoo" and already understand coding
  agents.

## Minimal toolset (4 tools; everything else disabled by default)

| Tool | Notes |
| -------- | -------- |
| `read` | text + images (jpg/png/gif/webp sent as attachments); defaults to first 2000 lines; offset/limit for large files |
| `write` | create/overwrite files; auto-creates parent directories |
| `edit` | exact-text replacement; `oldText` must match exactly, including whitespace |
| `bash` | returns stdout/stderr; optional timeout in seconds, no default timeout |

- Read-only tools `grep`, `find`, `ls` exist but are **disabled by default**; restrict to read-only
  via the CLI: `pi --tools read,grep,find,ls`.
- No web search or fetch tool by default. `curl` and file reads still form a prompt-injection
  surface, so run in a container if isolation is needed.

## YOLO by default

- No permission prompts, no safety rails, no pre-checking of bash commands; full filesystem access,
  any command with the user's privileges.
- Rationale: once an agent can write and run code, data exfiltration cannot be prevented without
  cutting network access entirely (which makes the agent useless); most harness security measures
  are "mostly security theater". Cites Simon Willison's "dual LLM" pattern while noting Willison
  himself admits "this solution is pretty bad".

## Explicit non-features and the intended alternatives

| Non-feature | Why | Intended alternative |
| ------------ | ----- | ---------------------- |
| Built-in to-dos | Lists "confuse models more than they help" | A `TODO.md` with checkboxes the agent reads/updates |
| Plan mode | Telling the agent to think without modifying files is sufficient; Claude Code's plan mode forces approving many command invocations | A `PLAN.md`, versioned with the code, shareable across sessions; enforce read-only via the `--tools` flag |
| MCP support | Context overhead: Playwright MCP = 21 tools / 13.7k tokens; Chrome DevTools MCP = 26 tools / 18k tokens ("7-9% of your context window gone before you even start") | CLI tools with README files the agent reads on demand (progressive disclosure); author maintains github.com/badlogic/agent-tools; `mcporter` (steipete) wraps MCP servers as CLIs |
| Background bash | Process tracking, output buffering, cleanup complexity; poor observability | tmux (dev servers, log watching, co-debugging) |
| Sub-agents | "A black box within a black box"; poor context transfer; painful to debug | Spawn pi itself via bash, optionally inside tmux for observability; a custom slash command can spawn a sub-agent via `pi --print` |

## Sub-agent and workflow guidance

- Mid-session sub-agents for context gathering are "a sign you didn't plan ahead"; gather context
  in its own session first and produce a reusable artifact.
- Models are "hesitant to read everything" (trained to read parts of files rather than full files),
  so they miss important context; this is why many pi-mono issue-tracker PRs get closed or revised.
- Parallel sub-agents implementing features simultaneously is "an anti-pattern" that turns
  codebases into "a pile of garbage".

## Multi-provider architecture (pi-ai)

- One unified API over Anthropic, OpenAI, Google, xAI, Groq, Cerebras, OpenRouter, and any
  OpenAI-compatible endpoint. Only four wire APIs are needed: OpenAI Completions, OpenAI Responses,
  Anthropic Messages, Google Generative AI.
- Streaming, tool calling with TypeBox schemas, thinking/reasoning support, best-effort token/cost
  tracking, and full abort via `AbortController` (partial results returned).
- Provider quirks are documented: Cerebras/xAI/Mistral/Chutes reject the `store` field; Mistral and
  Chutes use `max_tokens` not `max_completion_tokens`; several lack a `developer` role; Grok models
  reject `reasoning_effort`; reasoning content appears in different fields per provider
  (`reasoning_content` vs `reasoning`). Google notably does not support tool-call streaming.
- Context handoff: switching providers/models mid-session converts Anthropic thinking traces into
  `<thinking></thinking>` tagged blocks for OpenAI; providers insert signed blobs into event streams
  that must be replayed on subsequent requests; context serializes to JSON.
- Model registry is generated from OpenRouter and models.dev into `models.generated.ts` (token
  costs, image/thinking capabilities); custom models are defined manually with fields id, name, api,
  provider, baseUrl, reasoning, input, cost, contextWindow, maxTokens.

## Tool-result handling and the agent loop

- Tool results are split into two portions: text/JSON for the LLM and separate structured content
  for UI display ("I haven't seen in any unified LLM API"). Tools can return image attachments in
  native provider format; arguments are auto-validated with TypeBox + AJV; partial-JSON parsing
  during tool-call streaming enables progressive UI (e.g. streaming diffs). Missing feature:
  tool-result streaming (e.g. live ANSI output from bash), tracked as a simple future fix.
- Agent loop: process the user message, execute tool calls, feed results back, repeat until the
  model produces a response without tool calls. Message queuing via callback: after each turn the
  loop asks for queued messages and injects them before the next assistant response. Events are
  emitted for everything (reactive UI). There is deliberately **no max-steps knob**: "The loop just
  loops until the agent says it's done."

## TUI (pi-tui)

- Scrollback-based (writes to the terminal like a CLI) rather than full-screen, because coding
  agents are linear chat interfaces and native scroll/search stay intact.
- Retained-mode UI: a `Component` is an object with `render(width)` returning lines with ANSI codes
  plus optional `handleInput(data)`; a `Container` stacks components; the `TUI` class orchestrates.
- Differential rendering: first render outputs all lines; on a width change, clear and re-render
  everything; otherwise find the first differing line, move the cursor there, and re-render to the
  end. If the first changed line is above the visible viewport (user scrolled up), a full
  clear/re-render is required.
- Flicker prevention via synchronized-output escape sequences (`CSI ?2026h` / `CSI ?2026l`).
  Memory footprint: "a few hundred kilobytes for very large sessions."

## Benchmarks

- Terminal-Bench 2.0 with pi + Claude Opus 4.5, five trials per task (leaderboard-eligible);
  results submitted to the Terminal-Bench team; runner at github.com/badlogic/pi-terminal-bench.
  Error rates worsen once PST comes online, so a second run runs only during CET.
- Terminus 2 (the Terminal-Bench team's own minimal agent: just a tmux session, the model sends text
  commands and parses terminal output, no file tools) ranks competitively against far more
  elaborate agents, supporting the minimal approach.
- Anecdotal: "hundreds of exchanges" fit in a single session without compaction, which the author
  could not do with Claude Code.

## What this means when configuring or using Pi

- When in doubt, prefer the minimal path: a plain file (TODO.md / PLAN.md), a CLI tool with a
  README, or tmux, before adding an MCP server, a sub-agent, or plan-mode ceremony.
- Read-only restriction is a CLI flag, not a config: `pi --tools read,grep,find,ls`.
- No built-in sandbox (see `security-and-containerization.md`); isolate with a container/VM when
  needed.
- The package gallery ships `pi-mcp-adapter`, `pi-subagents`, `pi-web-access`, etc. as opt-in
  packages, consistent with "minimal core, extend on demand".
