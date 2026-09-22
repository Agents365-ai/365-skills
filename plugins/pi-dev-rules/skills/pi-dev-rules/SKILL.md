---
name: pi-dev-rules
version: 0.4.0
description: "Authoritative reference for Pi (@earendil-works/pi-coding-agent): install, configure, run, and extend. Use when the user asks about Pi CLI/flags/commands, providers/models/auth, settings/compaction/sessions, security/trust, extensions, skills, prompt templates, themes, packages, custom providers, TUI components, the SDK, RPC mode, or JSON streaming. Also use for Pi's design philosophy and opinionated choices (why minimal, 4 tools, YOLO, no MCP/plan mode/to-dos/sub-agents), the creator Mario Zechner's coding-agent blog post, Pi's internal monorepo architecture (the Chord plugin/service runtime (@earendil-works/chord), the agent harness, facets/services, delta tracking), and the repository's build, development, and contribution rules."
license: MIT
metadata: {"source":"https://pi.dev/docs/latest","docVersion":"latest","fetched":"2026-09-22","piRevision":"2c2cd63","version":"0.4.0"}
---

# Pi Dev Rules

Pi is a **minimal terminal coding harness**: lightweight core, extended through TypeScript
customizations. Package: `@earendil-works/pi-coding-agent`. Maintained by Earendil Inc. (MIT).
This skill mirrors the official docs at <https://pi.dev/docs/latest> so you can answer Pi questions
and build Pi customizations without re-fetching. Three further bundles describe material that has
no page on the website: the **internal monorepo architecture** (Chord runtime, agent harness) and
the repository's own development/contribution rules. They are built from the pi source tree.

## When to use this skill

- Installing, authenticating, or launching Pi; explaining CLI flags / slash commands.
- Configuring providers, API keys, custom models (`models.json`), or proxies.
- Editing `settings.json`, keybindings, themes; understanding sessions & compaction.
- Understanding the **project-trust security model** and running Pi in containers/sandboxes.
- **Extending Pi**: writing extensions, skills, prompt templates, packages, custom providers, TUI UI.
- Checking Pi's version history / what changed in a recent release.
- Driving Pi programmatically via the SDK, RPC mode, or JSON event-stream mode.
- Setting up Pi on Windows/Termux/tmux/specific terminals, or building it from source.
- Understanding **why Pi is designed the way it is**: the creator's philosophy (minimal core, 4
  tools, YOLO by default, no MCP/plan mode/to-dos/sub-agents) and how to configure/extend Pi along
  those lines instead of against them.
- Working **inside** the pi monorepo: the `@earendil-works/chord` runtime (plugin loading,
  service catalogue, RPC transport, delta/replicated state), the agent harness, facets/services,
  and the experimental `server`/`client`/`protocol` packages.

## Reference index: load the file you need

| File | Covers |
| ------ | -------- |
| `references/cli-and-usage.md` | Install, auth, launching, how Pi works (agent loop, context assembly, session tree), the full CLI reference (commands, flags, modes), slash commands, message queue, context files, environment variables (incl. bash-tool `PI_SESSION_*`/`PI_MODEL`), sessions, keybindings |
| `references/providers-and-models.md` | Subscription & API-key providers (30+), llama.cpp local router, `auth.json` (+ scoped `env`), cloud providers (Azure/Bedrock/Vertex/Cloudflare), custom models in `models.json`, `compat`, custom-provider extensions |
| `references/settings-and-compaction.md` | Configuration layout (agent directory vs project `.pi/`, context files), `settings.json` schema + example, trust/analytics/retry/transport keys, compaction (auto/manual) and branch summarization |
| `references/extending-pi.md` | Extension API (events, tools, commands, UI), Skills (SKILL.md), Prompt Templates, Themes, Packages |
| `references/tui-components.md` | TUI component system for custom extension/tool UIs (components, overlays, theming, custom editor) |
| `references/security-and-containerization.md` | Project-trust model (`trust.json`, `defaultProjectTrust`), no built-in sandbox, Gondolin micro-VM, Docker, OpenShell, Docker Sandboxes |
| `references/session-format.md` | Session JSONL schema: versions, content blocks, entry types, tree/context building, SessionManager API, plus the model-facing message types |
| `references/programmatic.md` | SDK, CLI integration (interactive/print/JSON/RPC mode choice, `RpcClient`, fork-and-rebrand), JSON event-stream mode, RPC protocol, RPC command reference, RPC extension UI |
| `references/platform-setup.md` | Windows, Termux, tmux, per-terminal modified-Enter setup, shell aliases |
| `references/development.md` | Monorepo package list, build-from-source and standalone-binary builds, supply-chain rules, `AGENTS.md` development rules, the `CONTRIBUTING.md` gate |
| `references/philosophy-and-design.md` | Creator Mario Zechner's design manifesto (blog, 2025-11-30): minimal prompt <1000 tokens, 4 tools, YOLO by default, non-features (no MCP/plan/to-dos/sub-agents/background bash) with their intended alternatives, multi-provider architecture, Terminal-Bench 2.0 results (manually curated, not auto-built) |
| `references/chord.md` | `@earendil-works/chord`: plugin loading/composition/bundling, the service catalogue, RPC transport, `bundleFacetPackage` + facet bundle loaders, and `chord/delta` replicated latest-value state. Built from `packages/chord/{README.md,PLANNING.md,src/delta/README.md}`; `PLANNING.md` is a plan, not a frozen API |
| `references/agent-harness.md` | Internal agent architecture: `AgentHarness` spec, application hosts & facets, typed values/lists, facet-service RPC, telemetry schema and invocation context. Built from `packages/agent/docs/`; specifications, not user docs |
| `references/changelog.md` | Release history: the last 25 versions with their headline change, extracted from `packages/coding-agent/CHANGELOG.md` (278 release sections; read the file in the checkout for the full text) |

## Starter plugins

Every Pi user should install these four (same author, battle-tested):

```bash
pi install npm:pi-mcp-adapter     # MCP server integration
pi install npm:pi-subagents       # subagents / loop / chain / parallel
pi install npm:pi-lens            # real-time LSP diagnostics
pi install npm:pi-web-access      # web search, URL fetch, YouTube, PDF
```

Then `pi list` to verify, restart Pi.

## Cheat sheet

```bash
npm install -g --ignore-scripts @earendil-works/pi-coding-agent   # install (or: curl -fsSL https://pi.dev/install.sh | sh)
export ANTHROPIC_API_KEY=sk-ant-...                               # or run /login in-session
cd /path/to/project && pi                                          # start interactive (may prompt to trust the project)

pi update                                 # update Pi itself (pi update self / pi update --self are aliases)
pi list                                   # list installed packages
pi -c                       # continue most recent session
pi -r                       # browse/resume sessions
pi --session <path|id>      # open specific session
pi --fork <path|id>         # fork a session
pi --no-session             # ephemeral (no save)
pi -a / -na                 # trust / don't trust project-local files for this run

pi -p "Summarize this codebase"                 # print mode (non-interactive)
pi @README.md "Summarize this"                  # attach files/images with @
cat file | pi -p "..."                          # pipe stdin
pi --provider openai --model gpt-4o "..."       # pick provider/model
pi --model sonnet:high "..."                    # model:thinkingLevel
pi --tools read,grep,find,ls -p "..."           # allowlist tools (-xt to exclude)
pi --mode json "..." | jq -c 'select(.type=="message_end")'   # JSON stream
pi --mode rpc                                   # JSON-RPC over stdin/stdout

# In-editor: @file (fuzzy), !cmd (run+send), !!cmd (run, hidden), /command, Ctrl+L model, Shift+Tab thinking, Ctrl+X copy
# While the agent runs: Enter queues a steering msg, Alt+Enter a follow-up, Esc aborts + restores
```

**Key locations** (global `~/.pi/agent/`, project `.pi/`):
`settings.json`, `auth.json`, `models.json`, `keybindings.json`, `trust.json`, `AGENTS.md`,
`SYSTEM.md`, `extensions/`, `skills/`, `prompts/`, `themes/`, `sessions/`.

## Hard rules

- **Install package name is exactly** `@earendil-works/pi-coding-agent` with `--ignore-scripts`.
- **Project context file is `AGENTS.md`** (Pi also reads `CLAUDE.md`); put it in the project root.
- **Extensions run with full system permissions**: treat them as trusted code; gate dangerous
  ops (`rm`, `sudo`, sensitive paths) with `ctx.ui.confirm` or a `tool_call` block handler.
- **Project trust is an input-loading guard, not a sandbox.** Pi ships no built-in sandbox; a project
  is "trusted" only to decide whether to load its `.pi/` resources (settings/extensions/skills/
  prompts/themes); decisions live in `~/.pi/agent/trust.json`, governed by `defaultProjectTrust`
  (`ask`/`always`/`never`), overridable per run with `--approve`/`--no-approve`. For untrusted repos
  or unattended runs, isolate with a container/VM (Gondolin/Docker/OpenShell); don't mount host
  `~/.pi/agent` unless the sandbox should see host credentials.
- **In extension/SDK tools: throw on error, never return an error flag.** Pi wraps a thrown error
  into an error tool result (`isError: true`); the docs defer to `ToolDefinition` in
  `packages/coding-agent/src/core/extensions/types.ts` for the exact contract. Limit tool output to
  ~50KB / 2000 lines (`DEFAULT_MAX_BYTES = 50 * 1024`). Use `StringEnum` (from
  `@earendil-works/pi-ai`) for LLM-facing enums.
- **Skill `name`**: 1–64 chars, lowercase `a-z 0-9 -`, no leading/trailing or consecutive hyphens;
  `description` ≤1024 chars and must say *when* to load it (a skill with no description won't load).
- **`chord.md` and `agent-harness.md` describe internals, not a stable contract.** Chord is
  published but application-neutral, the harness docs are implementation specifications, and
  `PLANNING.md`/`server`/`client`/`protocol` are explicitly experimental. Quote them as the
  current source tree state (pi@`2c2cd63`), not as promised API.
- **`auth.json` holds API keys and OAuth tokens**: Pi writes it `0600`, keep it private and out of
  version control. Credential priority: CLI `--api-key` → `auth.json` →
  env var → custom-provider keys in `models.json`.
- Project settings override agent-directory settings, and resource lists are combined rather than
  replaced (per-model objects such as compaction thresholds merge before the model lookup). Use
  `pi install -l` to write a package declaration to `.pi/settings.json`, which Pi reads only after
  the project is trusted.
