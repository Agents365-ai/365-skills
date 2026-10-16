---
name: pi-dev-rules
version: 0.9.0
description: "Authoritative reference for Pi (@earendil-works/pi-coding-agent): install, configure, run, and extend it. Use for the CLI and configuration, providers and models, extensions, skills, MCP, codemode, the SDK/RPC, security and trust, design philosophy, and the pi repository's internals and contribution rules."
license: MIT
metadata: {"source":"https://pi.dev/docs/latest","docVersion":"1.3.0","fetched":"2026-10-16","piRevision":"71023aec1","version":"0.9.0"}
---

# Pi Dev Rules

Pi is a **minimal terminal coding harness**: lightweight core, extended through TypeScript
customizations. Package: `@earendil-works/pi-coding-agent`. Maintained by Earendil Inc. (MIT).
This skill mirrors the official docs at <https://pi.dev/docs/latest> so you can answer Pi questions
and build Pi customizations without re-fetching. Five further bundles describe material the pi.dev
docs site does not hold: the **internal monorepo architecture** (the Chord typed host runtime, the
durable agent harness with its Pico5 specification, the agent core, telemetry), a **Pi Durable
overview** curated from the 2026-10-01 Earendil blog post (what the experimental harness is, its
version timeline, and which blog demos were removed in 1.2.0), and the repository's own
development/contribution rules.

## When to use this skill

- Installing, authenticating, or launching Pi; explaining CLI flags / slash commands.
- Configuring providers, API keys, custom models (`models.json`), or proxies.
- Editing `settings.json`, keybindings, themes; understanding sessions & compaction.
- Understanding the **project-trust security model** and running Pi in containers/sandboxes.
- **Extending Pi**: writing extensions, skills, prompt templates, packages, custom providers, TUI UI;
  enabling `codemode` or writing its scripts.
- Checking Pi's version history / what changed in a recent release.
- Driving Pi programmatically via the SDK, RPC mode, or JSON event-stream mode.
- Setting up Pi on Windows/Termux/tmux/specific terminals, or building it from source.
- Understanding **why Pi is designed the way it is**: the creator's philosophy (minimal core, 4
  tools, YOLO by default; the 2025-11-30 manifesto lists MCP, plan mode, to-dos, and sub-agents as
  deliberate non-features, and built-in MCP landed later, on 2026-09-29) and how to configure or
  extend Pi along those lines instead of against them.
- Working **inside** the pi monorepo: the `@earendil-works/chord` typed host runtime (contracts,
  hosts and links, hot reload, delta/replicated state), the durable harness
  (`@earendil-works/pi-durable`, Pico5), the agent core, and telemetry. The experimental
  `server`/`client`/`protocol` packages were removed in 1.2.0.
- Building on or asking about **Pi Durable** (`@earendil-works/pi-durable`): what the harness is, which
  version shipped what, where the runnable examples live, or why a blog-post demo path no longer exists.

## Reference index: load the file you need

| File | Covers |
| ------ | -------- |
| `references/cli-and-usage.md` | Install, auth, launching, how Pi works (agent loop, context assembly, session tree), the full CLI reference (commands, flags, modes), slash commands, message queue, context files, environment variables (incl. bash-tool `PI_SESSION_*`/`PI_MODEL`), sessions, keybindings |
| `references/providers-and-models.md` | Subscription & API-key providers (30+), llama.cpp local router, NVIDIA RTX recipe presets, `auth.json` (+ scoped `env`), cloud providers (Azure/Bedrock/Vertex/Cloudflare), custom models in `models.json`, `compat`, custom-provider extensions |
| `references/settings-and-compaction.md` | Configuration layout (agent directory vs project `.pi/`, context files), `settings.json` schema + example, trust/analytics/retry/transport keys, compaction (auto/manual) and branch summarization |
| `references/extending-pi.md` | Extension API (events, tools, commands, UI), Skills (SKILL.md), Prompt Templates, Themes, Packages, virtual models (`pi.registerVirtualModel`) |
| `references/mcp.md` | Built-in MCP support (2026-09-29): `mcp.json` global and project servers, stdio vs streamable HTTP, `pi mcp add/remove/list`, OAuth sign-in, exposure modes (`codemode`, `codemode-deferred`, `deferred`, `direct`, `hidden`) with `toolExposure`, `codemode`/`tool_search` tools, resources, permissions, servers from extensions, SDK wiring, and the `--no-mcp` / `mcp__*` tool patterns |
| `references/codemode.md` | The `codemode` tool: script input and the `// @options:` line, globals (`tools.<name>()`, `text()`, `image()`, `console.log()`, `store()`/`load()`, `searchTools()`, `describeTool()`), what tool calls resolve to, classifier and image models, namespaces and the inline budget, limits |
| `references/tui-components.md` | TUI component system for custom extension/tool UIs (components, overlays, theming, custom editor) |
| `references/security-and-containerization.md` | Project-trust model (`trust.json`, `defaultProjectTrust`), no built-in sandbox, Gondolin micro-VM, Docker, OpenShell, Docker Sandboxes |
| `references/session-format.md` | Session JSONL schema: versions, content blocks, entry types, tree/context building, SessionManager API, plus the model-facing message types |
| `references/programmatic.md` | SDK, CLI integration (interactive/print/JSON/RPC mode choice, `RpcClient`, fork-and-rebrand), JSON event-stream mode, RPC protocol, RPC command reference, RPC extension UI |
| `references/platform-setup.md` | Windows, Termux, tmux, per-terminal modified-Enter setup, shell aliases |
| `references/development.md` | Monorepo package list, build-from-source and standalone-binary builds, supply-chain rules, `AGENTS.md` development rules, the `CONTRIBUTING.md` gate |
| `references/philosophy-and-design.md` | Creator Mario Zechner's design manifesto (blog, 2025-11-30; manually curated, not auto-built): minimal prompt <1000 tokens, 4 tools, YOLO by default, the non-features it lists (MCP/plan mode/to-dos/sub-agents/background bash) with their intended alternatives and the MCP entry annotated as superseded since 2026-09-29, multi-provider architecture, Terminal-Bench 2.0 results |
| `references/chord.md` | `@earendil-works/chord`: the typed host runtime (contracts, declarations, registries, principals, handles, hot reload), hosts and links (`memoryLinkPair`, `ipcLink`, `webSocketLink`), and `chord/delta` replicated latest-value state. Built from `packages/chord/{README.md,docs/{guide,spec,tutorial}.md,src/delta/README.md}`; Pi Durable uses Chord, but the Pi coding agent does not; the spec describes the current runtime |
| `references/durable.md` | **Pi Durable** overview, curated from the 2026-10-01 Earendil blog post and the v1.3.0 tree: the harness/conversation/agent/task/execution-environment vocabulary, the positioning (a harness for building agentic applications, not the Pi CLI), the version timeline (1.0.0 with Pi 1.0 → 1.3.0, lockstep versions, breaking changes), install and code shape, the package layout and its 32 runnable examples, and the blog demos deleted in 1.2.0. Start here for status and routing |
| `references/agent-harness.md` | Internal runtime packages: `@earendil-works/pi-durable` (durable conversation/task/document harness, experimental API, stored before shown), `@earendil-works/pi-agent-core` (tool calling and state), `@earendil-works/pi-telemetry` (vendor-neutral telemetry contracts, adapters, typed schemas). Built from the three package READMEs; not user docs, and `durable.md` is the entry point |
| `references/durable-spec.md` | The normative **Pico5 specification** behind `pi-durable` (5352 lines): records and lifetimes, documents and mutation ownership, tasks and the effect sandwich, submissions and inbox, extensions/hooks/tools, telemetry. A design document for an experimental package, not a frozen API; the bundled text is the v1.3.0 spec |
| `references/changelog.md` | Release history: the last 25 versions with their headline change, extracted from `packages/coding-agent/CHANGELOG.md` (289 release sections; read the file in the checkout for the full text) |

## Pi 1.3.0 update notes

- `sessionShareDestination` selects `auto`, `gist`, or `radius` for `/share`.
- Resumed sessions restore active tools. `--tools +name`/`-name` adjusts that set.
- Ambiguous `--model` matches prefer a provider with credentials. Otherwise, specify `--provider`.
- Kimi Code now uses Chat Completions. Custom base URLs must include `/v1`.
- Codemode permits at most two live workers per Pi process, including cancelled workers until exit.
- Pi Durable supports SQLite table prefixes and shared Cloudflare adapter queues.

## Starter plugins

Every Pi user should install these three (same author, battle-tested):

```bash
pi install npm:pi-subagents       # subagents / loop / chain / parallel
pi install npm:pi-lens            # real-time LSP diagnostics
pi install npm:pi-web-access      # web search, URL fetch, YouTube, PDF
```

Then `pi list` to verify, restart Pi. MCP needs no package: it is built in since 2026-09-29 (see
`references/mcp.md`). An extension that registers `/mcp`, such as `pi-mcp-adapter`, replaces the
built-in support instead of adding to it.

## Cheat sheet

```bash
curl -fsSL https://pi.dev/install.sh | sh                         # install (pins dependencies)
npm install -g --ignore-scripts @earendil-works/pi-coding-agent   # npm alternative (no pinned transitive deps)
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
pi --tools read,grep,find,ls -p "..."           # allowlist tools (-xt excludes; +name/-name adjusts defaults)
pi --mode json "..." | jq -c 'select(.type=="message_end")'   # JSON stream
pi --mode rpc                                   # JSON-RPC over stdin/stdout

# In-editor: @file (fuzzy), !cmd (run+send), !!cmd (run, hidden), /command, Ctrl+L model, Shift+Tab thinking, Ctrl+X copy
# While the agent runs: Enter queues a steering msg, Alt+Enter a follow-up, Esc aborts + restores
```

**Key locations** (global `~/.pi/agent/`, project `.pi/`):
`settings.json`, `auth.json`, `models.json`, `keybindings.json`, `trust.json`, `AGENTS.md`,
`SYSTEM.md`, `extensions/`, `skills/`, `prompts/`, `themes/`, `sessions/`.

## Hard rules

- **Install package name is exactly** `@earendil-works/pi-coding-agent`. The pi.dev installer
  (`curl -fsSL https://pi.dev/install.sh | sh`) pins dependencies and is the documented install
  path; a global npm install needs `--ignore-scripts` and pins nothing.
- **Project context file is `AGENTS.md`** (Pi also reads `CLAUDE.md`); put it in the project root.
- **Extensions run with full system permissions**: treat them as trusted code; gate dangerous
  ops (`rm`, `sudo`, sensitive paths) with `ctx.ui.confirm` or a `tool_call` block handler.
- **Project trust is an input-loading guard, not a sandbox.** Pi ships no built-in sandbox; a project
  is "trusted" only to decide whether to load its `.pi/` resources (settings/extensions/skills/
  prompts/themes); decisions live in `~/.pi/agent/trust.json`, governed by `defaultProjectTrust`
  (`ask`/`always`/`never`), overridable per run with `--approve`/`--no-approve`. For untrusted repos
  or unattended runs, isolate with a container/VM (Gondolin/Docker/OpenShell); don't mount host
  `~/.pi/agent` unless the sandbox should see host credentials.
- **MCP is built in since 2026-09-29**, configured in `~/.pi/agent/mcp.json` or a project `.pi/
  mcp.json`; the project file is read only after the project is trusted, because stdio servers run
  commands. MCP calls go through the tool pipeline, so `tool_call` handlers and permission gates
  apply (`codemode` calls carry `parentToolCallId`). Installing an extension that registers `/mcp`
  (`pi-mcp-adapter`) disables the built-in support; disable it deliberately with `"extensions":
  ["-builtin:mcp"]`, `pi config`, or `--no-mcp` for one run.
- **In extension/SDK tools: throw on error, never return an error flag.** Pi wraps a thrown error
  into an error tool result (`isError: true`); the docs defer to `ToolDefinition` in
  `packages/coding-agent/src/core/extensions/types.ts` for the exact contract. Limit tool output to
  ~50KB / 2000 lines (`DEFAULT_MAX_BYTES = 50 * 1024`). Use `StringEnum` (from
  `@earendil-works/pi-ai`) for LLM-facing enums.
- **Skill `name`**: 1–64 chars, lowercase `a-z 0-9 -`, no leading/trailing or consecutive hyphens;
  `description` ≤1024 chars and must say *when* to load it (a skill with no description won't load).
- **`chord.md`, `durable.md`, `agent-harness.md`, and `durable-spec.md` describe internals, not a
  stable contract.** Chord is application-neutral and used by Pi Durable, not by the Pi CLI.
  `pi-durable` is experimental (1.0.0 on 2026-10-01 with Pi 1.0, 1.3.0 on 2026-10-15).
  Versions follow the monorepo, and earlier releases include breaking changes. The Pico5 spec is
  a design document. Quote the source tree state (pi@`71023aec1`), not a promised API.
- **The Pi Durable blog post is a 2026-10-01 snapshot.** Its "Try it" demos
  (`packages/coding-agent/src/experimental/{durable,vacation}/`) were deleted in 1.2.0 by commit
  `7472cda0d`; the durable harness itself is unaffected. Run examples from
  `packages/durable/test/examples/` (00–31) instead, and read `durable.md` for the version timeline.
- **`auth.json` holds API keys and OAuth tokens**: Pi writes it `0600`, keep it private and out of
  version control. Credential priority: CLI `--api-key` → `auth.json` →
  env var → custom-provider keys in `models.json`.
- Project settings override agent-directory settings, and resource lists are combined rather than
  replaced (per-model objects such as compaction thresholds merge before the model lookup). Use
  `pi install -l` to write a package declaration to `.pi/settings.json`, which Pi reads only after
  the project is trusted.
