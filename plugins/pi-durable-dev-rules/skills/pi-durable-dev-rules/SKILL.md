---
name: pi-durable-dev-rules
version: 0.1.0
description: "Developer reference for building applications, tools, and agents on the Pi Durable agent harness (@earendil-works/pi-durable) and the pi-ai model layer. Use when writing or debugging code that imports @earendil-works/pi-durable or pi-ai: assembling a Harness over memory/SQLite/JSONL/Durable Object storage, submitting input and waiting for answers, defining tools with TypeBox schemas and structured output, calling tools from tools, hooks and guards, durable tasks with checkpoints and ownership, subagents and child tasks, documents and migrations, code mode, tool search, per-conversation environments, compaction, recovery after a crash, storage and environment conformance tests, or choosing models and providers. Also use when a durable/agent-runtime behavior question comes up: what survives a restart, why an input stayed queued, why a task is blocked or orphaned, how abort cascades, or what the Pico5 specification requires."
license: MIT
metadata: {"source":"https://github.com/earendil-works/pi/tree/main/packages/durable","docVersion":"1.2.0","fetched":"2026-10-13","piRevision":"b9ab2a623","piDurableVersion":"1.2.0","version":"0.1.0"}
---

# Pi Durable Dev Rules

`@earendil-works/pi-durable` is a **durable agent harness**: conversations, model turns, tool calls,
tasks, and your own documents are committed to storage before anything is shown, so a process that dies
mid-turn is picked up where it stopped. It ships in the pi monorepo next to `@earendil-works/pi-ai`
(model access, tools, messages) and `@earendil-works/chord` (tracked JSON state).

Two things about it decide most design choices:

- **The API is experimental.** Version 1.2.0 tracks the monorepo; breaking changes land in every
  release. Quote and write against the version you have installed, and treat a signature difference as a
  version difference rather than a mistake.
- **It is a library for building agentic applications, not a coding-agent CLI.** For the Pi CLI, its
  extensions, skills, MCP, and SDK, use the sibling skill `pi-dev-rules`.

## When to use this skill

- Writing or reviewing code that imports `@earendil-works/pi-durable` or `@earendil-works/pi-ai`.
- Assembling a harness: storage backend choice, `HarnessOptions`, settings, the registry, and an
  execution environment.
- Conversations: submit/wait, the busy inbox (steer, follow-up, write), reset and handoff, forks,
  per-conversation agent changes.
- Tools: TypeBox schemas, three output channels, nested calls with `executeTool()`, `callers`,
  `deferred` tools and tool search, replay safety, output limits, image handling.
- Durable tasks: phases and checkpoints, ownership, waiting and `failFast`, abort, recovery, migration.
- Subagents and child tasks, foreground versus background, reporting answers back.
- Documents: scopes, history and fork semantics, migrations, checkpoints, observation.
- Code mode (QuickJS scripts over the conversation's tools), hooks and guards, compaction, usage.
- Runtime questions: what survives a crash, why an input is still queued, why a task is blocked or
  orphaned, how an abort cascades, why a partial answer is visible or missing.
- Extending the harness: storage backends and execution environments verified with the conformance
  suites, custom tasks and prompt sections.

## Reference index: load the file you need

| File | Covers |
| ---- | ------ |
| `references/durable-guide.md` | The package's own guide, bundled verbatim: quick start, concepts, persist and resume, extensions, tools (including nested calls and `callers`), code mode, system prompt, per-conversation agent, settings, environment, reload, watching, busy conversations, reset and handoff, compaction, agent events, hooks, more conversations and forks, abort and subagents, child tasks, the task graph, your own state, usage and cost, storage, errors, and the runnable examples. **Start here.** |
| `references/durable-api.md` | The exact public surface: entry-point map, `Context`, `Harness`/`Session`/`Conversation`/`ConversationHandle`, submissions, the `Tx` transaction surface, documents, entries, extensions and sections, hooks, tools and `ToolExecutionApi`, tasks and `TaskRuntime`, environment, storage, testing, observation, error classes, and the export inventory per subpath |
| `references/durable-runtime.md` | How work actually executes: the commit line and its rules, one input end to end, task checkpoints, the ownership tree, recovery by case, compaction, the inbox boundaries, live state and progress cadence, the failure model, the knobs that change behavior, and the deliberate non-goals |
| `references/durable-recipes.md` | Project setup, the catalogue of all 32 runnable examples, and 19 recipes with code: minimal chat, persistence and exactly-once input, live UI, agent events, structured-output tools, tool-calling tools, foreground and background subagents, child tasks with durable waits, coding agent, plan mode, per-conversation sandbox, tool override and wrappers, extension state and migration, hooks, compaction, code mode, tool search, conformance testing, plus the pitfall checklist |
| `references/durable-spec.md` | The normative **Pico5 specification** bundled verbatim (5340 lines): records and lifetimes, documents and mutation ownership, transactions and storage ownership, tasks and the effect sandwich, structured concurrency, submissions and the inbox, extensions/hooks/tools, the built-in tasks, document observation, the storage contract and failure model, the backends, **API footguns**, and non-goals. Read section 12 before shipping |
| `references/pi-ai-models.md` | The model layer bundled verbatim: `createModels()`/`builtinModels()`, provider factories and auth, querying the model catalog, environment variables, defining tools with TypeBox, constrained sampling, the event reference, image input, usage and cost, retries, and the message types that end up in entries |
| `references/codemode-sandbox.md` | `@earendil-works/pi-codemode` bundled verbatim: what a script may call, the injected globals, the sandbox module surface, determinism and memory limits, and local versus remote sandboxes |

## Cheat sheet

```bash
npm install @earendil-works/pi-durable @earendil-works/pi-ai @earendil-works/chord
node --conditions=source --experimental-strip-types app.ts     # run TS directly against the source
```

```ts
import { BACKGROUND_CONTEXT } from "@earendil-works/chord/context";
import { builtinModels } from "@earendil-works/pi-ai/providers/all";
import { createRegistry, Harness, AssistantEntry } from "@earendil-works/pi-durable";
import { openNodeSqliteStorage } from "@earendil-works/pi-durable/storage/sqlite/node";

const context = BACKGROUND_CONTEXT;
const harness = await Harness.open(await openNodeSqliteStorage("./session.sqlite"), {
	models: builtinModels(), registry: createRegistry(), env: (target) => new NodeExecutionEnv({ cwd: target.cwd ?? process.cwd() }),
}, context);
const root = await harness.root(context, { agent: { model: { provider: "openai", modelId: "gpt-6-sol" } } });

harness.resume();                                              // continue unfinished work from a previous process
const submission = await root.submit({ type: "input", content: "Hello", requestId: "greeting-1" }, context);
const settled = await submission.wait(context);                // "done" | "unanswered"
if (settled.status === "done" && settled.type === "input") {
	const answer = await root.commit((tx) => tx.entry(AssistantEntry, settled.answer), context);
}
await harness.close(context);
```

Storage: `MemoryStorage` (nothing persisted), `openNodeSqliteStorage(path)` (the default for anything
long-running; WAL, commits survive process crashes), `openNodeJsonlStorage(directory, context)`
(append-only, keeps the whole history in memory), `openDurableObjectSqliteStorage(ctx.storage)`.
One process owns a storage at a time.

## Hard rules

- **Writes go through one commit line, and nothing is shown before its commit is stored.** Inside a
  commit callback read only through `tx`; read every table row you need *before* the first table write
  (`ReadAfterWrite`), and never await slow work there: no models, tools, processes, network, humans,
  nested commits, or session waiters.
- **Every asynchronous call takes a `Context`.** Cancelling it cancels only that call or wait, never the
  durable work. Use `BACKGROUND_CONTEXT` where nothing should cancel, and `withCancel()` at a host
  boundary. `withoutAbortSignal()` is for mandatory cleanup such as `close()`.
- **Report what you did only after it is committed.** The pattern for a task step is: commit the intent,
  perform the effect, commit the result. A crash between the effect and the commit reruns that step, so
  make steps idempotent, use `runtime.memo()` for first-writer-wins decisions, and set
  `replay: "safe"` on a tool only when a rerun is genuinely safe. An unsafe tool that is interrupted
  gives the model an `interrupted` error result with the output committed so far.
- **A tool has three output channels.** `output` is what the model reads, `structuredOutput` is what
  programs calling the tool read (validated against `structuredOutputSchema`, required unless the result
  is an error), `details` is for the host UI. Only `output` and `details` enter the transcript.
- **Every tool call is its own durable task owned by its caller.** Nested calls made with
  `api.executeTool()` return their result to the caller instead of the transcript and reuse a key on
  rerun; cancelling the context stops only the wait. A nested result's `usage` is already counted under
  its own tool, so forwarding it double-counts it.
- **Ownership decides lifetime.** Every task names its owner at creation; every conversation is
  ownerless or owned by a task. Abort flows down; a task finishes only once its ordinary owned work
  drained (stored as `completing` until then); a `background: true` task is a boundary that ordinary
  aborts and idle waits skip. Never create owned work from an abort handler (the task is abort-marked):
  compensate inline, or use background conversation-owned tasks with `runtime.waitForTask()`.
- **A run owns its own writes.** Do not append raw entries to a conversation with an active run: use a
  write submission, which a raw `tx.appendEntry()` cannot replace and which runs the stale check.
- **`pi.`-prefixed names belong to the built-ins** for task names, document kinds, and entry kinds
  (`pi.user`, `pi.assistant`, `pi.system`, `pi.tool-result`, `pi.reset`, `pi.compaction`, `pi.agent`,
  `pi.provider`, `pi.live`, `pi.inbox`, `pi.usage`, `pi.generation`, `pi.tool`). Nothing enforces this
  and reusing one collides with harness behavior.
- **A storage error ends the harness.** The failing call rejects, every later call and pending wait
  rejects with `SessionFailed`, watches end with `session_failed`, and `onReport` gets the error once.
  Nothing is retried; reopen to recover and resubmit with the same `requestId`. An invalid request
  fails only that call (`StorageRequestError`), and your own code fails only its own unit.
- **Documents are addressed by kind, not by object.** Kinds and visible names are persisted protocol:
  a value migration cannot rename a kind (copy and retire), and a stored version newer than the code, or
  older without `migrate`, fails access. Only a typed `tx.doc()` creates an absent document.
- **Values from `snapshot()`, document states, and watches are tracked containers.** Never mutate them;
  copy first. A watch keeps at most 100 undelivered frames before collapsing into one full-value
  replacement, so a consumer that must see every transition has to journal it itself.
- **Extensions are selected whole.** Hooks and wrappers apply only where their extension is selected, so
  a conversation that selects tools as an explicit array and omits a guard runs without it. Wrappers are
  pure; uninstalling an extension stops new use but does not free resources of a running call.
- **Prompt sections must be stable.** A section whose text changes without a real content change (a
  clock, a random value) appends a `pi.system` entry on every request and defeats provider prompt
  caching. Settings can be getters: they are read at every use and never stored.
- **The API is experimental, and the Pico5 specification is a design document.** Read
  `references/durable-guide.md` for behavior, `references/durable-spec.md` when a rule matters, and
  section 12 (API footguns) of the spec before shipping.
