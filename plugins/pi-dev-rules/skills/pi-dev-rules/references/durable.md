# Pi Durable: What It Is, What Shipped, and Where to Read More

Source: <https://earendil.com/posts/pi-durable/> (Earendil Engineering, "Pi Durable", 2026-10-01)
and the pi tree at `pi@71023aec1` (release v1.3.0, 2026-10-15) with `packages/durable/CHANGELOG.md`.
Manually curated, not auto-built. The package README and the normative specification are bundled in
`agent-harness.md` (API) and `durable-spec.md` (semantics); this page is the routing and status layer
the blog provides and the docs site does not.

---

> **Why this file matters.** `@earendil-works/pi-durable` is a harness for building your own durable
> agentic applications, coding agents included. It is not the Pi CLI and does not replace it. Read
> this to know what the package is for, which version is current, which parts of the blog are stale,
> and which bundled file to open for API versus record semantics. The package is experimental and
> earlier releases include breaking changes, so pin a version.

## The vocabulary

The blog defines the terms the package, the README, and the specification all use:

| Term | Meaning |
| ------ | -------- |
| harness | Storage plus the machinery to run one or more conversations in parallel; it provides the tools and the execution environments they run in |
| conversation | One interaction with an agent, recorded as a transcript; it can fork another conversation at an entry |
| agent | The model plus its settings, such as the thinking level and the tools it may call |
| task | Everything the harness runs: a model request, a tool call, a compaction, or an extension's own unit of work |
| execution environment | Where a tool does its work: a laptop, a remote VM, or an in-memory sandbox, chosen per conversation |

Positioning, in the blog's words: Pi the coding agent is built for one person in a terminal on their
own machine; Pi Durable is for agents that run anywhere, are reached from several surfaces, hold
infinitely long conversations, survive failures, and let several people steer the same agent. It
shares code with the coding agent (`pi-ai`) and its principles (minimalism, malleability), and
lessons from it flow back into the coding agent.

What that buys, per the README:

- **Stored before shown:** every streamed partial, tool call, checkpoint, and document commit is
  durable. A killed process reopens the storage, finds unfinished tasks, and continues from the last
  checkpoint; `requestId` makes a submission exactly-once, and a tool reruns only if it declares
  `replay: "safe"`.
- **Documents:** typed JSON state (todos, plans, sandboxes) committed atomically with the transcript,
  with a per-document fork rule (`asOf`, `current`, `initial`).
- **Extensions as bundles:** prompt sections, tools, hooks, and tasks installed in a registry and
  selected per conversation; installing a name again replaces it while conversations run.
- **Multiplayer:** `viewState()`, `watch()`, and `watchEvents()` let any number of clients attach,
  late or after a reconnect, and steer a busy conversation (`whenBusy: "steer"`).
- **No built-in subagents:** a subagent is a child conversation owned by the tool call that started
  it, taken from the README's `subagent` example and made restart-safe by `replay: "safe"`.
- **Backends:** `MemoryStorage`, SQLite (`storage/sqlite/node`, also a Cloudflare Durable Object),
  and JSONL (`storage/jsonl/node`), plus a conformance suite and benchmarks for a custom one. One
  process owns a storage at a time.

The blog's own sizing claim: about 15,000 lines of source without tests (roughly 150k tokens with
GPT, 250k with Claude), of which the storage backends are about 3,000 lines that an agent can skip.

## Status and versions

`@earendil-works/pi-durable` is versioned in lockstep with the rest of the monorepo, and it is
experimental: the blog says the API might still change, and the CHANGELOG confirms it.

| Version | Date | Note |
| --------- | ------ | ------ |
| 1.0.0 | 2026-10-01 | Initial release, shipped with Pi 1.0 |
| 1.0.1 | 2026-10-03 | No entries in its CHANGELOG section |
| 1.0.2 – 1.0.4 | 2026-10-04 – 2026-10-05 | Execution-environment and tool fixes, PowerShell tool, env conformance suite |
| 1.1.0 | 2026-10-07 | Breaking scan `order`, Cloudflare storage, context caching |
| 1.2.0 | 2026-10-12 | Breaking: tagged `ToolTaskInput`, `output` instead of `content`, storage errors fail the Session, nested tool calls, structured output, deferred tools, the `codemode` extension |
| 1.3.0 | 2026-10-15 | SQLite table prefixes, shared operation queues for Cloudflare adapters, system-baseline ordering after compaction, lower-memory image encoding |

Install, as in the README:

```bash
npm install @earendil-works/pi-durable @earendil-works/pi-ai @earendil-works/chord
```

The shape of a durable app, from the blog (the README Quick Start is the fuller version):

```typescript
const harness = await Harness.open(storage, { models, registry, env }, context);
const root = await harness.root(context, { agent: { model: { provider: "openai", modelId: "gpt-6-sol" } } });
const submission = await root.submit({ type: "input", content: "..." }, context);
const settled = await submission.wait(context);
// after a crash: reopen the same storage, harness.resume()
```

## Where it lives in the tree

| Path (pi@71023aec1) | What it holds |
| --------------------- | ------------- |
| `packages/durable/README.md` | The public API, per feature; bundled in `agent-harness.md` |
| `packages/durable/docs/spec.md` | The normative Pico5 specification (5352 lines); bundled in `durable-spec.md` |
| `packages/durable/test/examples/00-31` | 32 runnable examples; the README's table names most of them: chat, coding tools, print/JSON mode, inbox, late join, foreground and background subagents, child tasks, compaction, reviewer, per-conversation sandbox, tool override, reload |
| `packages/durable/CHANGELOG.md` | Per-release breaking changes and features; the source of the table above |
| `packages/durable/docs/pico-v5-{handoff,chord-usage}.md`, `chord-delta-findings.md` | Implementation plan and Chord design notes; not bundled here |
| `packages/chord/` | The document-state runtime the harness builds on; see `chord.md` |

Run an example from the package directory:

```bash
node --conditions=source --experimental-strip-types test/examples/14-chat.ts
```

Examples that call OpenAI need `OPENAI_API_KEY`; the rest use the faux provider.

## What the blog no longer describes correctly

The blog's "Try it" section points at two demo apps in the coding agent:

```bash
node packages/coding-agent/src/experimental/durable/main.ts     # durable TUI coding agent
node packages/coding-agent/src/experimental/vacation/main.ts   # vacation planner
```

Both were deleted before v1.2.0. Commit `7472cda0d` (2026-10-12, "remove the experimental server
stack and the client, protocol, and server packages", first released in 1.2.0) removed 10,054 lines:
`packages/coding-agent/src/experimental/{durable,vacation}/`, the experimental server stack under
`src/experimental/`, and the `client`, `protocol`, and `server` packages. Do not send anyone to those
paths, and do not treat the blog's screenshots of the demos as the current tree. The demos still
exist in older checkouts (for example at `v1.1.0` and earlier), which is why a stale working tree may
show them; `git log --oneline --diff-filter=D -- packages/coding-agent/src/experimental/durable` is
the check.

The main features described in the blog remain in the v1.3.0 package: the storage backends, crash recovery,
queued submissions, forks, compaction as a background task, documents, hot extension replacement,
and the multi-client view. The blog's "coming weeks" items (a Slack bot, a GitHub triage bot) are not
in the tree.

## Which file to read

| Question | File |
| ---------- | ------ |
| How do I call the harness (open, root, submit, tools, compaction, documents, views)? | `agent-harness.md` |
| What are the exact record, task, submission, and document semantics? | `durable-spec.md` |
| How does document state replicate and observe? | `chord.md` |
| What does the Pi coding agent itself do (a different harness, same principles)? | the coding-agent bundles, starting with `cli-and-usage.md` |
