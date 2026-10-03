# Pi Agent Runtime, Durable Harness, and Telemetry
Source: `packages/durable/README.md`, `packages/agent/README.md`, `packages/telemetry/README.md`
Internal runtime packages, not user documentation. `@earendil-works/pi-durable` is the durable agent harness, `@earendil-works/pi-agent-core` is the tool-calling and state core, and `@earendil-works/pi-telemetry` holds the vendor-neutral telemetry contracts. The durable harness is experimental and its API changes between releases; the normative Pico5 specification is bundled in `durable-spec.md`. See the shipped CLI docs in the other reference files for user-facing behavior.

---

> **Auto-built from individual doc pages.**
> Sources: https://raw.githubusercontent.com/earendil-works/pi/main/packages/durable/README.md, https://raw.githubusercontent.com/earendil-works/pi/main/packages/agent/README.md, https://raw.githubusercontent.com/earendil-works/pi/main/packages/telemetry/README.md

## Durable Agent Harness

A durable agent harness. Conversations, model turns, tool calls, and your own state are committed to storage before anything is shown. If the process dies mid-turn, reopening the storage picks the work up where it stopped.

Built on [`@earendil-works/pi-ai`](../ai/README.md) for model access and `@earendil-works/chord` for document state.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Concepts](#concepts)
- [Persist and Resume](#persist-and-resume)
- [Extensions](#extensions)
- [Tools](#tools)
- [System Prompt](#system-prompt)
- [Per-Conversation Agent](#per-conversation-agent)
- [Settings](#settings)
- [Environment](#environment)
- [Reload](#reload)
- [Watching a Conversation](#watching-a-conversation)
- [Busy Conversations](#busy-conversations)
- [Reset and Handoff](#reset-and-handoff)
- [Compaction](#compaction)
- [Agent Events (Experimental)](#agent-events-experimental)
- [Hooks](#hooks)
- [More Conversations and Forks](#more-conversations-and-forks)
- [Abort and Subagents](#abort-and-subagents)
- [Child Tasks](#child-tasks)
- [Task Graph](#task-graph)
- [Your Own State](#your-own-state)
- [Usage and Cost](#usage-and-cost)
- [Storage](#storage)
- [Examples](#examples)
- [Design Documents](#design-documents)

## Installation

```bash
npm install @earendil-works/pi-durable @earendil-works/pi-ai @earendil-works/chord
```

## Quick Start

```typescript
import { BACKGROUND_CONTEXT } from "@earendil-works/chord/context";
import { createModels } from "@earendil-works/pi-ai/models";
import { openaiProvider } from "@earendil-works/pi-ai/providers/openai";
import { AssistantEntry, createRegistry, Harness, MemoryStorage } from "@earendil-works/pi-durable";

const context = BACKGROUND_CONTEXT;

const models = createModels();
models.setProvider(openaiProvider()); // reads OPENAI_API_KEY

const harness = await Harness.open(new MemoryStorage(), { models, registry: createRegistry() }, context);
const root = await harness.root(context, { agent: { model: { provider: "openai", modelId: "gpt-6-sol" } } });

const submission = await root.submit({ type: "input", content: "What is the capital of France?" }, context);
const settled = await submission.wait(context);
if (settled.status === "done" && settled.type === "input") {
	const answer = await root.commit((tx) => tx.entry(AssistantEntry, settled.answer), context);
	console.log(answer?.model?.[0]);
}
await harness.close(context);
```

What happened:

- `Harness.open()` opens a Session over a storage backend. `MemoryStorage` keeps everything in memory.
- `root()` returns the root conversation, creating it on first use with the given agent choices. A conversation is a transcript of immutable entries.
- `submit()` durably admits your input and returns a `Submission`. A built-in generation task calls the model and appends the answer.
- `wait()` resolves once the input is answered (`done`) or has failed (`unanswered`, with a reason).

Every async call takes a Chord `Context`, which carries cancellation. `BACKGROUND_CONTEXT` never cancels. Cancelling a wait only cancels that wait, never the work.

## Concepts

- **Harness**: one open storage plus the machinery that runs agents on it. All changes go through one line of atomic commits, and nothing is shown before its commit is stored.
- **Conversation**: a transcript. `root()` creates the root conversation on first use; you can create more and fork them. A `Conversation` handle holds no state; compare handles by `id`.
- **Entry**: one immutable transcript record, such as a user message (`pi.user`), a model response (`pi.assistant`), a tool result (`pi.tool-result`), a system prompt change (`pi.system`), a reset (`pi.reset`), or your own kind. The model sees the entries from the newest reset onward.
- **Commit**: an atomic write. `conversation.commit((tx) => ...)` can append entries, edit documents, and create tasks together; either all of it is stored or none of it.
- **Document**: typed JSON state stored next to the transcript and changed in commits. Built-in ones hold each conversation's agent choices (`pi.agent`), the running generation and tools (`pi.live`), queued submissions (`pi.inbox`), and spend (`pi.usage`).
- **Task**: a durable state machine that saves a checkpoint at every step, so a restarted process continues from the last one. Every task has an owner: its conversation, or another task. The Harness runs answers as built-in tasks: `pi.generation` calls the model and owns the `pi.tool` tasks of its tool calls, waits for them, and hands the run to the next generation.
- **Submission**: something you hand to a conversation, either user input or an entry to write, which you can wait for.
- **Turn and run**: a turn is one model response and its tool calls; a run is the turns from an input to its final answer. A conversation is busy while a run is going.
- **Extension**: a named bundle of tools, system prompt sections, hooks, wrappers, and tasks.
- **Registry**: the extensions this process installed. It can change while the Harness runs; new work uses the new state.
- **Agent**: what a conversation runs with: model, thinking level, selected extensions, tools, instructions, and working directory. Stored per conversation as names in `pi.agent`, resolved against the registry at each use.

One answered input, as entries and tasks:

```text
submit(input) → pi.user
  pi.generation → pi.system (only if the prompt or tools changed), pi.assistant (tool calls)
    pi.tool × n → pi.tool-result × n   (owned by the generation, which waits for them)
  pi.generation → pi.assistant (answer) → submission done
```

## Persist and Resume

Use SQLite or JSONL storage to keep conversations across restarts:

```typescript
import { openNodeSqliteStorage } from "@earendil-works/pi-durable/storage/sqlite/node";

const harness = await Harness.open(await openNodeSqliteStorage("./session.sqlite"), { models, registry }, context);
const root = await harness.root(context); // the same root as last time
harness.resume(); // continue any run the last process left unfinished
```

Work interrupted by a crash or close stays pending. `resume()` starts the task scheduler; submitting or waiting starts it too. A retried submission with the same `requestId` returns the existing submission instead of submitting twice:

```typescript
const submission = await root.submit({ type: "input", content: "Hello", requestId: "greeting-1" }, context);
// After a restart: the same request ID finds the same submission.
const again = await root.submit({ type: "input", content: "Hello", requestId: "greeting-1" }, context);
// again.id === submission.id
```

`harness.submission(id)` reacquires a submission by ID, for example to wait for it after a restart.

## Extensions

Code the Harness runs, other than its built-in tasks, comes in named extensions installed in a registry your process owns:

```typescript
import { createRegistry, defineExtension, defineTool, hook, section, ToolTask } from "@earendil-works/pi-durable";
import { CodingTools } from "@earendil-works/pi-durable/tools";

const Coding = defineExtension({
	name: "coding",
	sections: [section("preamble", () => "You are a concise coding assistant.", { tag: false })],
	hooks: [hook(ToolTask, { beforeTool: (call) => (isDangerous(call) ? { block: "Needs approval" } : undefined) })],
});

const registry = createRegistry();
registry.install(CodingTools);
registry.install(Coding);
```

An extension may bring `tools`, `sections`, `hooks`, `wraps` (decorators of a tool or section by name), and `tasks`. By default every conversation selects every installed extension, in install order. Nothing in the registry is stored; conversations store extension names.

## Tools

`@earendil-works/pi-durable/tools` provides `read`, `write`, `edit`, and `bash`, and the `CodingTools` extension with all four. They touch files and processes only through the call's environment (see [Environment](#environment)). Reading images is not supported yet.

Define your own tool with a TypeBox schema. `defineTool()` types `args` from `parameters`, which the Harness validates before `execute()`. `api.output()` streams running output, which becomes the result when `execute()` returns no `content`:

```typescript
import { Type } from "@earendil-works/pi-ai";

const count = defineTool({
	name: "count",
	description: "Count from 1 to n",
	parameters: Type.Object({ n: Type.Number() }),
	execute: async (args, api) => {
		for (let i = 1; i <= args.n; i++) api.output(`${i}\n`);
		return {};
	},
});
registry.install(defineExtension({ name: "count", tools: [count] }));
```

Each call runs as its own durable task. Its intent is committed before `execute()` runs. If the process dies mid-call, the tool reruns on reopen only when it is declared `replay: "safe"`; otherwise the model gets an `interrupted` error result with the output committed so far. Throwing from `execute()` gives the model an error result. A result can also return `usage`, which is added to the conversation's [usage](#usage-and-cost). It can also return `control: { terminate: true }`: when every result of the round asks for it, the run ends without another model request.

A later extension's tool with the same name replaces an earlier one where both are selected, and `wrapTool()` decorates whichever tool won:

```typescript
const Venv = defineExtension({ name: "venv", tools: [createBashTool({ commandPrefix: "source .venv/bin/activate" })] });
const Timing = defineExtension({
	name: "timing",
	wraps: [wrapTool(createBashTool(), (bash) => ({ ...bash, execute: (args, api, ctx) => timed(() => bash.execute(args, api, ctx)) }))],
});
```

## System Prompt

The system prompt is built from the selected extensions' sections, rendered in order before each request. A section sees the resolved agent, the environment built for the request, and committed documents:

```typescript
section("cwd", (input) => input.env?.cwd); // rendered as <cwd>\n...\n</cwd>; undefined omits it
```

A conversation's `instructions` render last, as the section `instructions`. Sections and tool changes are stored as positional system entries in the transcript. Only what changed is sent again, which keeps provider prompt caches warm. A section that returns something different every time, such as the current time, defeats that.

## Per-Conversation Agent

Each conversation stores what it runs with in its `pi.agent` document. `configure()` changes it in one commit; unset fields follow the host:

```typescript
await root.configure(
	{
		model: { provider: "openai", modelId: "gpt-6-sol" },
		thinkingLevel: "high",
		extensions: { remove: [Coding] }, // edits the host default; an array selects exactly these, in order
		tools: [readTool, bashTool], // an array offers exactly these; { remove: [...] } drops some
		instructions: "Only read; never edit files.",
		cwd: "/work/repo",
	},
	context,
);
await root.configure({ tools: null }, context); // null clears a field back to the host default
const agent = await root.agent(context); // resolved: model, extensions, tools, sections, cwd
```

Extensions and tools are passed as objects and stored by name, so a stored name outlives its code: after an extension is uninstalled, conversations that select it just stop getting it until it is installed again. `createConversation()`, `fork()`, and `root()` take the same change as `agent`. A task-owned conversation, such as a subagent's, starts as a copy of its owner's conversation's agent. A fork starts with the agent its parent had at the fork entry. The model, prompt, and offered tools of a request are fixed when it is prepared; a change applies from the next request. Tool calls and hooks use the agent as their task phase resolves it, and the environment is built from the current `cwd` at each use, so a `cwd` or extension change can reach calls the model already made.

## Settings

Run policy shared by every conversation is passed as `settings`. It is read at every use and never stored, so getters make it live, for example backed by a settings file:

```typescript
const harness = await Harness.open(storage, {
	models,
	registry,
	settings: {
		extensions: [CodingTools, Coding], // default selection; absent: every installed extension
		stream: { timeoutMs: 120_000 },
		retry: { maxRetries: 3 },
		compaction: { reserveTokens: 16384 },
		toolExecution: "parallel",
		get followUpMode() {
			return userSettings.followUpMode;
		},
	},
}, context);
```

## Environment

`env` builds the execution environment for each tool call, section rendering, and `runtime.env()`. It receives the conversation's ID, its agent `cwd`, and committed reads, so one function serves a directory per conversation or a container per conversation:

```typescript
import { NodeExecutionEnv } from "@earendil-works/pi-durable/env/node";

const harness = await Harness.open(storage, {
	models,
	registry,
	env: ({ cwd }) => new NodeExecutionEnv({ cwd: cwd ?? process.cwd() }),
}, context);
```

A throw from `env` becomes the call's error result. Without an environment, the built-in tools fail with an error result. A fresh environment object per call is fine: `edit` and `write` serialize changes to one file by the environment's `id` and path. A custom `ExecutionEnv` sets `id` so that equal ids see the same files at the same paths, for example one id per container.

## Reload

Installing an extension with an installed name replaces it in place, in one step:

```typescript
registry.install(await loadCodingExtension()); // same name "coding": replaces the installed one
```

`registry.uninstall(extension)` removes the installed extension with that name, whichever object it is.

Work that already started keeps the code it took: a running tool call finishes under its old implementation, and each task phase resolves hooks and the agent once, from the registry at the phase's start. The next phase, request, or call uses the new code. After a restart, install the same extensions again; pending tasks of an extension's `tasks` resume once it is installed.

## Watching a Conversation

Everything a UI needs is committed state. `viewState()` returns the conversation's structural view as a read-only Chord state, updated after every commit that touches it:

```typescript
const view = await root.viewState(context);
view.subscribe((value) => {
	// value.entries: the active transcript
	// value.docs["pi.live"]: the running generation (streamed partial, retry, deferred) and tool calls (output, details)
	// value.docs["pi.inbox"], value.docs["pi.usage"], value.docs["pi.agent"]
	render(value);
});
// later: view.dispose();
```

`watch()` delivers the same view with the exact Chord operations of each commit, one callback at a time:

```typescript
const watch = await root.watch(context);
render(watch.value); // the state at attachment
watch.start(async (value, ops) => {
	await send(ops); // for example to a remote client that applies them
});
// later: await watch.stop();
```

A slow watch keeps at most 100 undelivered frames. After that, the pending frames are replaced by one frame holding the whole newest view. A client that joins late or reconnects starts from the current view; nothing is replayed.

Partial answers and tool output are committed at most every 100 ms, so a crash loses at most that window.

## Busy Conversations

A conversation is busy while a run is working on an input. Submitting to a busy conversation queues the submission in the conversation's inbox, `docs["pi.inbox"]` in the view:

```typescript
await root.submit({ type: "input", content: "Also run the tests" }, context); // follow-up (default)
await root.submit({ type: "input", content: "Use pnpm, not npm", whenBusy: "steer" }, context);
await root.submit({ type: "input", content: "Only if idle", whenBusy: "reject" }, context); // throws ConversationBusy
await root.submit({ type: "write", entry: { kind: "app.note", data: "user opened a file" } }, context);
```

- **Steers** are placed after the current tool round and join the running work.
- **Follow-ups** are placed when the run answers, and start the next run.
- **Writes** append an entry without asking the model anything.
- `await submission.abort(context)` withdraws a queued submission.
- The [settings](#settings) `steeringMode: "all"` and `followUpMode: "all"` place every queued item at once instead of one per turn.

If a run fails, queued items stay in the inbox until the next submission places them, oldest first.

## Reset and Handoff

`reset()` starts a new context. The model no longer sees older entries, but they stay in storage:

```typescript
await root.reset(undefined, context);                                  // start from nothing
await root.reset("We were fixing the flaky login test. Continue.", context); // start from a handoff note
```

While busy, the reset is queued like a write. When it is placed during a tool round, the current run ends. A tool can request the same with `control: { handoff: "..." }`.

## Compaction

Compaction shrinks what the model sees: it summarizes older entries and appends a `pi.compaction` entry that holds the summary and heads the first entry it keeps. Older entries stay in storage.

```typescript
const id = await root.compact("Keep the failing test names", context); // manual, with optional instructions
const { outcome } = (await harness.waitForTask(id, context)).state;
if (outcome.status === "completed" && outcome.result.submissionId !== undefined) {
	const placed = await (await harness.submission(outcome.result.submissionId, context))!.wait(context);
	console.log(placed.status); // "done", or "unanswered" with reason "stale"
}
```

The conversation keeps working while the summary is made. The summary is placed at once when the conversation is idle, otherwise at the next turn boundary. Esc (`abort()`) cancels a manual compaction.

Generation also compacts on its own, controlled by the [settings](#settings):

```typescript
settings: {
	compaction: {
		enabled: true, // automatic compaction; manual compact() always works
		reserveTokens: 16384, // above contextWindow - reserveTokens, the next request waits for a compaction
		keepRecentTokens: 20000, // roughly how much recent context stays verbatim
		backgroundTokens: 32768, // this far below that, a compaction starts in the background; 0 disables it
	},
}
```

When a provider rejects a request because the context is too long, generation compacts and retries once. A summary that would cut before the start of the current context settles as `stale` when it is placed, so when several are in flight, the furthest cut stays in effect. Summarization spend counts in `pi.usage`. A `beforeCompact` hook on `CompactionTask` can decline or supply its own summary.

Running compactions are listed in `docs["pi.live"].compactions` with their reason, attempt, and retry backoff. The agent events add `compaction_start` and `compaction_end`, and a `compactions` field in the snapshot.

## Agent Events (Experimental)

For consumers that want coding-agent style events (`message_start`, `message_update`, `tool_execution_start`, ...) instead of structural state:

```typescript
import { watchEvents } from "@earendil-works/pi-durable";

const stream = await watchEvents(harness, root.id, context);
initialize(stream.snapshot); // entries, run, in-flight generation, tools, compactions, inbox, agent, usage
stream.start(async (events) => {
	for (const event of events) console.log(JSON.stringify(event));
});
```

Events are derived from commits, one batch per commit, and apply on top of the snapshot. Message and tool updates carry deltas: text and thinking appends, appended tool-call argument text, and output trims and appends. When a consumer falls more than 100 batches behind, it receives a fresh `snapshot` event instead. See `test/examples/19-json.ts` for the full stream of one run.

## Hooks

Hooks let extensions observe or adjust the built-in tasks, in the conversations that select them:

```typescript
import { GenerationTask, hook, ToolTask } from "@earendil-works/pi-durable";

const Guard = defineExtension({
	name: "guard",
	hooks: [
		hook(ToolTask, { beforeTool: (call) => (call.name === "bash" ? { block: "bash is disabled here" } : undefined) }),
		hook(GenerationTask, { onYield: (answer) => (needsMoreWork(answer) ? { continue: "Keep going." } : undefined) }),
	],
});
```

- **Generation:** `beforeRequest` (replace the messages of one request), `afterResponse`, `onYield` (continue the run with another user message), and `afterTools` (runs once a round's tools are done).
- **Tools:** `beforeTool` (block or rewrite arguments) and `afterTool` (replace the result).

To limit a hook to some conversations, select its extension only there, for example with `configure({ extensions: { add: [Guard] } })`.

## More Conversations and Forks

```typescript
const other = await harness.createConversation({ ownership: { kind: "ownerless" } }, context);
const fork = await root.fork(entryId, { ownership: { kind: "ownerless" } }, context);
```

A fork sees its parent's entries up to `entryId` and continues independently. It keeps the parent's agent as of that entry. Both take `agent` and `init`, applied in the creating commit.

## Abort and Subagents

`await root.abort(context)` stops a conversation: queued inputs are withdrawn (queued writes stay), every task of its current work is aborted, and the call resolves once the conversation is idle.

A conversation can be **owned** by a task. A subagent tool creates its child inside `api.commit()` with `ownership: { kind: "task", taskId: api.taskId }`, then drives it through `api.conversation(id)`:

```typescript
const Subagent: Extension = defineExtension({
	name: "subagent",
	tools: [
		defineTool({
			name: "subagent",
			description: "Delegate a self-contained task to a subagent and get its answer back.",
			parameters: Type.Object({ task: Type.String() }),
			replay: "safe", // a rerun after a crash finds the same child and submission
			execute: async (args, api, context) => {
				const child = await api.commit(async (tx) => {
					// The ownership index remembers the child, so a rerun reuses it.
					const existing = (await tx.scanConversations({ ownerTaskId: api.taskId }, 1)).items[0];
					if (existing !== undefined) return existing.id;
					// Starts as a copy of this conversation's agent: model, extensions, tools, cwd.
					const created = await tx.createConversation({ ownership: { kind: "task", taskId: api.taskId } });
					// A cheaper model, and no subagents of its own.
					await configure(tx, created.id, { model: haiku, extensions: { remove: [Subagent] } });
					return created.id;
				}, context);
				await api.details({ conversationId: child }, context); // lets a UI attach to the child
				const request = { type: "input", content: args.task, requestId: `subagent:${api.taskId}` } as const;
				const settled = await (await (await api.conversation(child, context))!.submit(request, context)).wait(context);
				return { content: [{ type: "text", text: settled.status }] };
			},
		}),
	],
});
```

Owned work belongs to its owner:

- Aborting the call aborts the child. So does the call failing: `execute()` throwing, or a crash that interrupts a call that is not replay-safe.
- The parent is idle only once the child is.
- A task created with `{ background: true }` is a boundary: work it owns survives the parent's abort and does not keep the parent busy. `root.abort(context, { background: true })` aborts it too.

The examples show both patterns as product code:

- [`22-subagent-foreground.ts`](test/examples/22-subagent-foreground.ts): the tool above, returning the child's answer. The UI finds the child through the call's `details` and prints the child's events indented under the call.
- [`23-subagent-background.ts`](test/examples/23-subagent-background.ts): persistent subagents behind one `subagent` tool that spawns, messages (steer or follow-up), waits for, stops, and lists them. Each child is owned by a background anchor task, so the parent's Esc and idle waits never reach it. Each message is delivered by a background reporter task that posts the answer back to the parent as a follow-up input once it arrives; request IDs keep a restart from sending a message or a report twice.

## Child Tasks

A task can own child tasks, created with `ownership: { kind: "task", taskId }`, and wait for them by committing a `waiting` state:

```typescript
pay: async (task, runtime, context) => {
	await runtime.commit(async (tx) => {
		const payments = [];
		for (const card of task.input.cards) {
			payments.push(await tx.createTask(Payment, { card }, { ownership: { kind: "task", taskId: task.id } }));
		}
		// Resume in `decide` once every payment is done; the first failure aborts the rest.
		return { status: "waiting", checkpoint: { phase: "decide", payments }, on: payments, policy: "failFast" };
	}, context);
},
decide: async (task, runtime, context) => {
	const outcomes = await runtime.outcomes(task.state.checkpoint.payments, context);
	// ...commit the checkout's own outcome
},
```

- **Waiting:** the task runs no code while it waits. With `allSettled` it resumes once every task in `on` is done; with `failFast` the first failed child also aborts the others. `on` may name other tasks too, with `allSettled`.
- **Finishing:** a task that finishes while work it owns is still running is `completing`: its outcome is decided, but it becomes terminal, and `waitForTask()` returns, only once that work is done. A failed or aborted outcome aborts that work first.
- **Aborting:** abort runs bottom-up. Aborting a task aborts the work it owns first, and its own abort handler starts only once that work is done, so each task undoes its own effects.

[`24-child-tasks.ts`](test/examples/24-child-tasks.ts) runs a checkout with four payments: a declined card, a cancelled checkout, and a restart while the payments run.

## Task Graph

`harness.taskGraph(context)` shows every live task of the Session as one Chord state, for a task panel or debugging. Each node has its owner edge (`owner` task, or none for a task its conversation owns), its status, whether it is `background` or abort-marked, and the conversations it owns. `harness.watchTaskGraph(context)` delivers the same value as a watch, like a conversation's `watch()`.

```typescript
const graph = await harness.taskGraph(context);
graph.subscribe((value) => {
	for (const node of Object.values(value.tasks)) {
		const status = node.state.status === "waiting" ? `waiting on ${node.state.on.join(", ")}` : node.state.status;
		console.log(`${node.id} ${node.kind} ${status}`, node.owner ?? `conversation ${node.conversationId}`);
	}
});
```

A task appears with the commit that creates it and leaves with the commit that makes it terminal. Statuses are the committed ones: `pending`, `running`, `waiting` (with `on` and `policy`), and `completing` (with the held outcome's status). After a restart, tasks that were `running` show as `pending` until they run again. Whether a pending task is blocked by a missing definition is not part of the graph; `harness.inspect()` reports that. The graph lists live tasks only: once a subagent's owner task is terminal, a later task in its conversation is a top-level node, and the conversation's `ConversationRecord.owner` (also in its view's `conversation`) links it to its parent. [`24-child-tasks.ts`](test/examples/24-child-tasks.ts) prints the checkout's tree while its payments run.

## Your Own State

Documents are typed JSON objects committed together with entries. Define one, and edit it in a commit:

```typescript
import { defineDoc } from "@earendil-works/pi-durable";

const Todos = defineDoc<{ items: string[] }>({
	kind: "app.todos",
	version: 1,
	scope: "conversation",
	history: "latest", // or "rewindable" to read old values with snapshotAsOf()
	fork: "initial", // what a fork starts with: "initial", "current", or "asOf"
	initial: () => ({ items: [] }),
});

await root.commit(async (tx) => {
	(await tx.doc(Todos, root.id)).items.push("write docs");
}, context);
console.log(await harness.snapshot(Todos, root.id, context));
```

`harness.watchDoc()` and `harness.documentState()` observe one document like the view above. `HarnessOptions.conversationCreated(tx, conversation)` runs in every commit that creates or forks a conversation, including a tool's raw `tx.createConversation()`, so every conversation gets your documents; `init` in `createConversation()`, `fork()`, and `root()` writes per-call data in the same commit. An extension's tools, sections, and hooks read their own documents through `api` or `input.read`, and treat an absent one as its default ([`11-extension-state.ts`](test/examples/11-extension-state.ts)).

## Usage and Cost

Each conversation keeps token and cost totals in `docs["pi.usage"]`: per `provider/model` for model responses, and per tool name for tool results that report usage. Failed and aborted attempts count too. For the whole Session:

```typescript
const usage = await harness.usage(context); // { models: { "openai/gpt-6-sol": Usage }, tools: {...} }
```

## Storage

| Backend | Import | Notes |
|---|---|---|
| Memory | `MemoryStorage` from the package root | Nothing is persisted. |
| SQLite | `openNodeSqliteStorage(file)` from `@earendil-works/pi-durable/storage/sqlite/node` | One database file. WAL mode with `synchronous = NORMAL`: commits survive process crashes; the newest may be lost on power or host failure. |
| JSONL | `openNodeJsonlStorage(directory, context)` from `@earendil-works/pi-durable/storage/jsonl/node` | Append-only files in one directory. Pass `{ fsync: true }` to flush before each commit marker. |

One process owns a storage at a time; there is no cross-process locking. The portable SQLite and JSONL cores (`/storage/sqlite`, `/storage/jsonl`) run without Node APIs, for example on Bun or in Cloudflare Durable Objects, given an asynchronous `SqliteDatabase` facade or a `FileSystem` from `@earendil-works/pi-durable/env`.

SQLite adapters implement promise-based `exec`, `run`, `get`, `all`, `transaction`, and `close`. `run`, `get`, and `all` take SQL text plus positional bindings; adapters may cache prepared statements by SQL text. A transaction callback receives a transaction handle; all work in the transaction must use it, and the handle expires when the callback settles. Adapters must queue unrelated operations and other transactions until the transaction finishes, so calling `database` itself inside the callback never settles:

```typescript
await database.transaction(async (transaction) => {
	await transaction.exec("CREATE TABLE example (value TEXT)");
	await transaction.run("INSERT INTO example (value) VALUES (?)", "stored atomically");
});
```

Custom backends can run the shared conformance suite with any Vitest- or Jest-compatible runner:

```typescript
import { registerStorageConformance } from "@earendil-works/pi-durable/testing";
import { describe, expect, it } from "vitest";

registerStorageConformance({ describe, expect, it }, "My Storage", async (use) => {
	const storage = await openMyStorage();
	try {
		await use(storage);
	} finally {
		await closeMyStorage(storage);
	}
});
```

The package root loads TypeBox, because the tool task validates arguments with pi-ai's `validateToolArguments()`. That costs about 23 MB of peak RSS unbundled, about 4 MB in a tree-shaken bundle.

## Examples

Runnable examples live in [`test/examples`](test/examples). Run one from this package directory with:

```bash
node --conditions=source --experimental-strip-types test/examples/14-chat.ts
```

| Example | Shows |
|---|---|
| [14-chat](test/examples/14-chat.ts) | One question and answer |
| [16-real-model](test/examples/16-real-model.ts) | Streaming an answer from OpenAI |
| [17-coding-tools](test/examples/17-coding-tools.ts) | A tool-using turn on JSONL storage |
| [18-print](test/examples/18-print.ts) | Print mode: submit a prompt, print the answer |
| [19-json](test/examples/19-json.ts) | JSON mode: agent events or raw view operations, on SQLite, JSONL, or memory |
| [20-inbox](test/examples/20-inbox.ts) | Steers, follow-ups, writes, and withdrawal while busy |
| [21-late-join](test/examples/21-late-join.ts) | Attaching a view and an event stream mid-run |
| [22-subagent-foreground](test/examples/22-subagent-foreground.ts) | A replay-safe subagent tool whose child the call owns, with the child's events under the call |
| [23-subagent-background](test/examples/23-subagent-background.ts) | Persistent subagents: spawn, steer, stop, list, answers reported back, restart-safe |
| [24-child-tasks](test/examples/24-child-tasks.ts) | A checkout that owns and waits for four payments: failFast, abort, restart |
| [25-compaction](test/examples/25-compaction.ts) | A long chat compacted in the background, manually, and after a context overflow |
| [26-coding-agent](test/examples/26-coding-agent.ts) | CodingTools, live settings from a settings object, an environment that follows the conversation's directory |
| [27-plan-mode](test/examples/27-plan-mode.ts) | A read-only plan mode as an extension with its own document, switched with `configure()` |
| [28-reviewer](test/examples/28-reviewer.ts) | A reviewer conversation with its own model, extensions, tools, directory, and review loop |
| [29-sandbox-per-conversation](test/examples/29-sandbox-per-conversation.ts) | An environment per conversation, looked up from an app document |
| [30-tool-override](test/examples/30-tool-override.ts) | A same-name bash for some conversations, and a wrapper that times whichever bash won |
| [31-reload-and-restart](test/examples/31-reload-and-restart.ts) | Reloading an extension mid-call, and stored choices surviving a restart |
| [00](test/examples/00-conversation.ts)–[13](test/examples/13-recovery.ts) | The layers underneath: sessions, documents, forks, watches, the Harness, agent configuration, reload, extension state, tasks, recovery |

Examples that call OpenAI need `OPENAI_API_KEY`; most use the faux provider otherwise.

## Design Documents

- [`docs/spec.md`](https://github.com/earendil-works/pi/blob/main/packages/durable/docs/spec.md): the normative specification
- [`docs/pico-v5-handoff.md`](https://github.com/earendil-works/pi/blob/main/packages/durable/docs/pico-v5-handoff.md): the implementation plan
- [`docs/pico-v5-chord-usage.md`](https://github.com/earendil-works/pi/blob/main/packages/durable/docs/pico-v5-chord-usage.md): how the package uses Chord

Benchmarks: `npm run bench:storage`, `npm run bench:storage:memory`, and `npm run bench:tool-output`.

## License

MIT

---

## Agent Core

Stateful agent with tool execution and event streaming. Built on `@earendil-works/pi-ai`.

## Installation

```bash
npm install @earendil-works/pi-agent-core
```

## Quick Start

```typescript
import { Agent } from "@earendil-works/pi-agent-core";
import { createModels } from "@earendil-works/pi-ai";
import { anthropicProvider } from "@earendil-works/pi-ai/providers/anthropic";

const models = createModels();
models.setProvider(anthropicProvider());
const model = models.getModel("anthropic", "claude-sonnet-4-6");
if (!model) throw new Error("Model not found");

const agent = new Agent({
  initialState: {
    systemPrompt: "You are a helpful assistant.",
    model,
  },
  streamFn: models.streamSimple.bind(models),
});

agent.subscribe((event) => {
  if (event.type === "message_update" && event.assistantMessageEvent.type === "text_delta") {
    // Stream just the new text chunk
    process.stdout.write(event.assistantMessageEvent.delta);
  }
});

await agent.prompt("Hello!");
```

## Core Concepts

### AgentMessage vs LLM Message

The agent works with `AgentMessage`, a flexible type that can include:
- Standard LLM messages (`user`, `assistant`, `toolResult`)
- Custom app-specific message types via declaration merging

LLMs only understand `user`, `assistant`, and `toolResult`. The `convertToLlm` function bridges this gap by filtering and transforming messages before each LLM call.

### Message Flow

```
AgentMessage[] → transformContext() → AgentMessage[] → convertToLlm() → Message[] → LLM
                    (optional)                           (required)
```

1. **transformContext**: Prune old messages, inject external context
2. **convertToLlm**: Filter out UI-only messages, convert custom types to LLM format

## Event Flow

The agent emits events for UI updates. Understanding the event sequence helps build responsive interfaces.

### prompt() Event Sequence

When you call `prompt("Hello")`:

```
prompt("Hello")
├─ agent_start
├─ turn_start
├─ message_start   { message: userMessage }      // Your prompt
├─ message_end     { message: userMessage }
├─ message_start   { message: assistantMessage } // LLM starts responding
├─ message_update  { message: partial... }       // Streaming chunks
├─ message_update  { message: partial... }
├─ message_end     { message: assistantMessage } // Complete response
├─ turn_end        { message, toolResults: [] }
└─ agent_end       { messages: [...] }
```

### With Tool Calls

If the assistant calls tools, the loop continues:

```
prompt("Read config.json")
├─ agent_start
├─ turn_start
├─ message_start/end  { userMessage }
├─ message_start      { assistantMessage with toolCall }
├─ message_update...
├─ message_end        { assistantMessage }
├─ tool_execution_start  { toolCallId, toolName, args }
├─ tool_execution_update { partialResult }           // If tool streams
├─ tool_execution_end    { toolCallId, result }
├─ message_start/end  { toolResultMessage }
├─ turn_end           { message, toolResults: [toolResult] }
│
├─ turn_start                                        // Next turn
├─ message_start      { assistantMessage }           // LLM responds to tool result
├─ message_update...
├─ message_end
├─ turn_end
└─ agent_end
```

Tool execution mode is configurable:

- `parallel` (default): preflight tool calls sequentially, execute allowed tools concurrently, emit `tool_execution_end` as soon as each tool is finalized, then emit toolResult messages and `turn_end.toolResults` in assistant source order
- `sequential`: execute tool calls one by one, matching the historical behavior

In parallel mode, tool completion events follow tool completion order, but persisted toolResult messages still follow assistant source order.

The mode can be set globally via `toolExecution` in the agent config, or per-tool via `executionMode` on `AgentTool`. If any tool call in a batch targets a tool with `executionMode: "sequential"`, the entire batch executes sequentially regardless of the global setting.

The `beforeToolCall` hook runs after `tool_execution_start` and validated argument parsing. It can block execution and attach `terminate: true` to the blocked result. The `afterToolCall` hook runs after tool execution finishes and before `tool_execution_end` and final tool result message events are emitted.

Tools, blocked `beforeToolCall` results, and `afterToolCall` overrides can return `terminate: true` to hint that the automatic follow-up LLM call should be skipped. The loop only stops early when every finalized tool result in that batch sets `terminate: true`. Mixed batches continue normally.

When you use the `Agent` class, assistant `message_end` processing is treated as a barrier before tool preflight begins. That means `beforeToolCall` sees agent state that already includes the assistant message that requested the tool call.

### Request preparation and turn finalization

`prepareRequest` runs immediately before every conversational provider request, including the first. Use it to install canonical persisted context after pending input has been emitted:

```typescript
agent.prepareRequest = async ({ context }) => ({
  context: { ...context, messages: await session.loadModelContext() },
});
```

`prepareRequest` does not poll queues. Steering queued while it runs waits for the next normal steering poll.

`finishTurn` runs after the assistant and all tool results are finalized, but before `turn_end`. It runs for normal, error, and aborted responses:

```typescript
agent.finishTurn = async ({ message }) => {
  if (message.stopReason === "error" || message.stopReason === "aborted") return;
  if (shouldEndRun(message)) return { action: "end" };
  return needsAnotherResponse(message) ? { action: "continue" } : undefined;
};
```

Returning `undefined` preserves normal scheduling. `{ action: "end" }` stops immediately after `turn_end`, before polling steering or follow-up queues or preparing another request. On a normal response, `{ action: "continue" }` ensures one next provider request. If tool results, steering, or a follow-up already cause that request, they satisfy the decision and no additional request is made; otherwise the loop makes one context-only request. Error and aborted responses remain hard exits, so their decisions are ignored. `finishTurn` runs again after the next request, so returning `{ action: "continue" }` unconditionally creates an endless loop.

To migrate from the removed `shouldStopAfterTurn`, return `{ action: "end" }`. Guard error and aborted responses to preserve the old hook's normal-response-only invocation, especially when the predicate has side effects or assumes a successful response:

```typescript
finishTurn: async (turn, signal) => {
  if (turn.message.stopReason === "error" || turn.message.stopReason === "aborted") return;
  return (await shouldStop(turn, signal)) ? { action: "end" } : undefined;
},
```

Each provider turn follows this lifecycle:

```text
selected input events
→ prepareRequest
→ provider response
→ tool results
→ finishTurn
→ turn_end
→ existing continuation scheduling or agent_end
```

### continue() and queued input

`continue()` retains its existing queue behavior. Empty and system-only transcripts reject without consuming queues. A non-assistant tail continues from existing context: steering is polled at startup, while follow-up input waits until the response naturally stops.

```typescript
agent.followUp({ role: "user", content: "After the retry", timestamp: Date.now() });
await agent.continue(); // The first request retries the existing user/toolResult tail.
```

An assistant tail cannot be sent directly, so `continue()` falls back to one queued steering batch, then one queued follow-up batch. Queue mode still controls whether that selected batch contains one message or all messages:

```typescript
agent.steer({ role: "user", content: "Continue from here", timestamp: Date.now() });
await agent.continue(); // Uses the queued message only because the tail is assistant.
```

### Event Types

| Event | Description |
|-------|-------------|
| `agent_start` | Agent begins processing |
| `agent_end` | Final event for the run. Awaited subscribers for this event still count toward settlement |
| `turn_start` | New turn begins (one LLM call + tool executions) |
| `turn_end` | Turn completes with assistant message and tool results |
| `message_start` | Any message begins (user, assistant, toolResult) |
| `message_update` | **Assistant only.** Includes `assistantMessageEvent` with delta |
| `message_end` | Message completes |
| `tool_execution_start` | Tool begins |
| `tool_execution_update` | Tool streams progress |
| `tool_execution_end` | Tool completes |

`Agent.subscribe()` listeners are awaited in registration order. `agent_end` means no more loop events will be emitted, but `await agent.waitForIdle()` and `await agent.prompt(...)` only settle after awaited `agent_end` listeners finish.

## Agent Options

```typescript
const agent = new Agent({
  // Initial state. systemPrompt and tools become the leading system message
  // unless messages already starts with one.
  initialState: {
    systemPrompt: string,
    model: Model<any>,
    thinkingLevel: "off" | "minimal" | "low" | "medium" | "high" | "xhigh" | "max",
    tools: AgentTool<any>[],
    messages: AgentMessage[],
  },

  // Convert AgentMessage[] to LLM Message[] (required for custom message types)
  convertToLlm: (messages) => messages.filter(...),

  // Transform context before convertToLlm (for pruning, compaction)
  transformContext: async (messages, signal) => pruneOldMessages(messages),

  // Steering mode: "one-at-a-time" (default) or "all"
  steeringMode: "one-at-a-time",

  // Follow-up mode: "one-at-a-time" (default) or "all"
  followUpMode: "one-at-a-time",

  // Required stream function. Receives a TranscriptContext: the prompt and tools
  // are in the transcript's system messages, not on the context.
  streamFn: models.streamSimple.bind(models),

  // Session ID for provider caching
  sessionId: "session-123",

  // Dynamic API key resolution (for expiring OAuth tokens)
  getApiKey: async (provider) => refreshToken(),

  // Tool execution mode: "parallel" (default) or "sequential"
  toolExecution: "parallel",

  // Preflight each tool call after args are validated. Can block execution.
  beforeToolCall: async ({ toolCall, args, context }) => {
    if (toolCall.name === "bash") {
      return { block: true, reason: "bash is disabled", terminate: true };
    }
  },

  // Postprocess each tool result before final tool events are emitted.
  afterToolCall: async ({ toolCall, result, isError, context }) => {
    if (toolCall.name === "notify_done" && !isError) {
      return { terminate: true };
    }
    if (!isError) {
      return { details: { ...result.details, audited: true } };
    }
  },

  // Rebuild finalized context immediately before every provider request.
  prepareRequest: async ({ context }, signal) => {
    return { context: { ...context, messages: await loadCanonicalMessages(signal) } };
  },

  // Finalize a completed turn before turn_end is emitted.
  // `continue` ensures one next request; existing tool/queue scheduling can satisfy it.
  // `end` ends this run after turn_end without polling queues.
  finishTurn: async ({ message, toolResults }, signal) => {
    return shouldContinue(message, toolResults) ? { action: "continue" } : undefined;
  },

  // Custom thinking budgets for token-based providers
  thinkingBudgets: {
    minimal: 128,
    low: 512,
    medium: 1024,
    high: 2048,
  },
});
```

## Agent State

```typescript
interface AgentState {
  model: Model<any>;
  thinkingLevel: ThinkingLevel;
  tools: AgentTool<any>[];
  messages: AgentMessage[];
  readonly isStreaming: boolean;
  readonly streamingMessage?: AgentMessage;
  readonly pendingToolCalls: ReadonlySet<string>;
  readonly errorMessage?: string;
}
```

Access state via `agent.state`.

Assigning `agent.state.tools = [...]` or `agent.state.messages = [...]` copies the top-level array before storing it. Mutating the returned array mutates the current agent state.

The transcript owns the system prompt and tool declarations: the leading system message is the prompt, later system messages patch it (see `SystemMessage` in pi-ai). `agent.state.systemPrompt` is read-only and replays the transcript. `agent.state.tools` is the executable loadout; before every request the loop diffs it against the tools the transcript declares and, if they differ, announces the change in a system message (merged into a pending system message when one exists). pi-ai's `getCurrentSystemMessage(messages)` returns the replayed head, including declared tools, for any message array, including agent transcripts with custom message roles.

To change the prompt mid-conversation, append a system message with `content` (added instructions) or `sections` (named replacements):

```typescript
await agent.prompt([
  { role: "system", content: "", sections: { skills: "<skills>...</skills>" }, timestamp: Date.now() },
  { role: "user", content: "Continue", timestamp: Date.now() },
]);
```

During streaming, `agent.state.streamingMessage` contains the current partial assistant message.

`agent.state.isStreaming` remains `true` until the run fully settles, including awaited `agent_end` subscribers.

## Methods

### Prompting

```typescript
// Text prompt
await agent.prompt("Hello");

// With images
await agent.prompt("What's in this image?", [
  { type: "image", data: base64Data, mimeType: "image/jpeg" }
]);

// AgentMessage directly
await agent.prompt({ role: "user", content: "Hello", timestamp: Date.now() });

// Continue existing non-assistant input; an assistant tail may use queued input as fallback
await agent.continue();
```

### State Management

```typescript
agent.state.model = getModel("openai", "gpt-4o");
agent.state.thinkingLevel = "medium";
agent.state.tools = [myTool];
agent.toolExecution = "sequential";
agent.beforeToolCall = async ({ toolCall }) => undefined;
agent.afterToolCall = async ({ toolCall, result }) => undefined;
agent.prepareRequest = async ({ context }) => ({
  context: { ...context, messages: await loadCanonicalMessages() },
});
agent.finishTurn = async () => undefined;
agent.state.messages = newMessages; // top-level array is copied
agent.state.messages.push(message);
const nextQueuedMessages = agent.peekQueuedMessages(); // respects queue modes; does not consume
agent.reset();
```

### Session and Thinking Budgets

```typescript
agent.sessionId = "session-123";

agent.thinkingBudgets = {
  minimal: 128,
  low: 512,
  medium: 1024,
  high: 2048,
};
```

### Control

```typescript
agent.abort();           // Cancel current operation
await agent.waitForIdle(); // Wait for completion
```

### Events

```typescript
const unsubscribe = agent.subscribe(async (event, signal) => {
  if (event.type === "agent_end") {
    // Final barrier work for the run
    await flushSessionState(signal);
  }
});
unsubscribe();
```

## Steering and Follow-up

Steering messages let you interrupt the agent while tools are running. Follow-up messages let you queue work after the agent would otherwise stop.

```typescript
agent.steeringMode = "one-at-a-time";
agent.followUpMode = "one-at-a-time";

// While agent is running tools
agent.steer({
  role: "user",
  content: "Stop! Do this instead.",
  timestamp: Date.now(),
});

// After the agent finishes its current work
agent.followUp({
  role: "user",
  content: "Also summarize the result.",
  timestamp: Date.now(),
});

const steeringMode = agent.steeringMode;
const followUpMode = agent.followUpMode;

agent.clearSteeringQueue();
agent.clearFollowUpQueue();
agent.clearAllQueues();
```

Use clearSteeringQueue, clearFollowUpQueue, or clearAllQueues to drop queued messages.

When steering messages are detected after a turn completes:
1. All tool calls from the current assistant message have already finished
2. Steering messages are injected
3. The LLM responds on the next turn

Follow-up messages are checked only when there are no more tool calls and no steering messages. If any are queued, they are injected and another turn runs.

## Custom Message Types

Extend `AgentMessage` via declaration merging:

```typescript
declare module "@earendil-works/pi-agent-core" {
  interface CustomAgentMessages {
    notification: { role: "notification"; text: string; timestamp: number };
  }
}

// Now valid
const msg: AgentMessage = { role: "notification", text: "Info", timestamp: Date.now() };
```

Handle custom types in `convertToLlm`:

```typescript
const agent = new Agent({
  streamFn: models.streamSimple.bind(models),
  convertToLlm: (messages) => messages.flatMap(m => {
    if (m.role === "notification") return []; // Filter out
    return [m];
  }),
});
```

## Tools

Define tools using `AgentTool`:

```typescript
import { Type } from "typebox";

const readFileTool: AgentTool = {
  name: "read_file",
  label: "Read File",  // For UI display
  description: "Read a file's contents",
  parameters: Type.Object({
    path: Type.String({ description: "File path" }),
  }),
  // Override execution mode for this tool (optional).
  // "sequential" forces the entire batch to run one at a time.
  // "parallel" allows concurrent execution with other tool calls.
  // If omitted, the global toolExecution config applies.
  executionMode: "sequential",
  execute: async (toolCallId, params, signal, onUpdate) => {
    const content = await fs.readFile(params.path, "utf-8");

    // Optional: stream progress
    onUpdate?.({ content: [{ type: "text", text: "Reading..." }], details: {} });

    // Optional: add `terminate: true` here to skip the automatic follow-up LLM call
    // when every finalized tool result in the batch does the same.
    return {
      content: [{ type: "text", text: content }],
      details: { path: params.path, size: content.length },
    };
  },
};

agent.state.tools = [readFileTool];
```

### Error Handling

**Throw an error** when a tool fails. Do not return error messages as content.

```typescript
execute: async (toolCallId, params, signal, onUpdate) => {
  if (!fs.existsSync(params.path)) {
    throw new Error(`File not found: ${params.path}`);
  }
  // Return content only on success
  return { content: [{ type: "text", text: "..." }] };
}
```

Thrown errors are caught by the agent and reported to the LLM as tool errors with `isError: true`.

Return `terminate: true` from `execute()`, a blocked `beforeToolCall`, or `afterToolCall` to hint that the agent should stop after the current tool batch. This only takes effect when every finalized tool result in the batch is terminating. The hint is runtime-only; emitted `toolResult` transcript messages remain standard LLM tool results.

### MCP and Codemode

`@earendil-works/pi-mcp` connects to MCP servers and `@earendil-works/pi-codemode` runs model-written JavaScript that calls tools. [examples/mcp-codemode](examples/mcp-codemode) wraps both as `AgentTool`s: one tool per MCP tool, and a `codemode` tool whose scripts call the agent's tools through `runToolCall()`, so `beforeToolCall` and `afterToolCall` apply to those calls too.

## Proxy Usage

For browser apps that proxy through a backend:

```typescript
import { Agent, streamProxy } from "@earendil-works/pi-agent-core";

const agent = new Agent({
  streamFn: (model, context, options) =>
    streamProxy(model, context, {
      ...options,
      authToken: "...",
      proxyUrl: "https://your-server.com",
    }),
});
```

## Low-Level API

For direct control without the Agent class:

```typescript
import { agentLoop, agentLoopContinue } from "@earendil-works/pi-agent-core";

const context: AgentContext = {
  messages: [{ role: "system", content: "You are helpful.", timestamp: Date.now() }],
  tools: [],
};

const config: AgentLoopConfig = {
  model: getModel("openai", "gpt-4o"),
  convertToLlm: (msgs) => msgs.filter(m => ["user", "assistant", "toolResult"].includes(m.role)),
  toolExecution: "parallel",  // overridden by per-tool executionMode if set
  beforeToolCall: async ({ toolCall, args, context }) => undefined,
  afterToolCall: async ({ toolCall, result, isError, context }) => undefined,
};

const userMessage = { role: "user", content: "Hello", timestamp: Date.now() };

const streamFn = models.streamSimple.bind(models);
for await (const event of agentLoop([userMessage], context, config, undefined, streamFn)) {
  console.log(event.type);
}

// Continue from existing context
for await (const event of agentLoopContinue(context, config, undefined, streamFn)) {
  console.log(event.type);
}
```

These low-level streams are observational. They preserve event order, but they do not wait for your async event handling to settle before later producer phases continue. If you need message processing to act as a barrier before tool preflight, use the `Agent` class instead of raw `agentLoop()` or `agentLoopContinue()`.

## License

MIT

---

## Telemetry

Vendor-neutral telemetry contracts and typed schema utilities for pi packages.

This package provides:

- an explicit, callback-based `TelemetryContext` / `TelemetrySpan` contract;
- a shared `NOOP_TELEMETRY_CONTEXT`;
- a reference `InMemoryTelemetryContext` implementation;
- serializable schema definitions with inferred TypeScript types;
- no exporter, global current-span state, or dependency on a telemetry backend.

Applications can use the in-memory reference or provide an adapter for OpenTelemetry, Sentry, logs, or another backend. Pi packages pass telemetry contexts explicitly and define their domain schemas separately.

## Table of Contents

- [Installation](#installation)
- [Telemetry Concepts](#telemetry-concepts)
- [Core Context API](#core-context-api)
- [Adapter Contract](#adapter-contract)
- [No-op Context](#no-op-context)
- [In-Memory Reference Adapter](#in-memory-reference-adapter)
- [Adapter Conformance](#adapter-conformance)
- [Typed Schemas](#typed-schemas)
  - [Start and Completion Attributes](#start-and-completion-attributes)
- [Schema Metadata](#schema-metadata)
- [Pi Package Integration](#pi-package-integration)
- [Security and Portability](#security-and-portability)
- [API Reference](#api-reference)
- [Development](#development)
- [License](#license)

## Installation

```bash
npm install @earendil-works/pi-telemetry
```

## Telemetry Concepts

Telemetry describes what a program did while it was running. This package models that work using spans, attributes, events, statuses, and explicit context:

| Concept | Plain-language meaning |
|---|---|
| **Span** | A timed record of one operation, such as loading an account or making an AI request. It begins before the work and ends when the work finishes. |
| **Parent and child spans** | Operations can contain smaller operations. A request span might contain a cache lookup and a database query. Together they form a tree showing where time was spent. |
| **Attribute** | A named fact attached to a span, such as `provider: "openai"`, `cache.hit: true`, or `item_count: 12`. Attributes describe the operation and its result. |
| **Event** | A named occurrence at a point during a span, such as `retry.scheduled` or `cache.lookup`. Events have no duration and may carry their own attributes. |
| **Status** | The operation's outcome: `ok` or `error`. An error status may include an error name and message. |
| **Context** | A handle identifying where new work belongs in the span tree. Starting a span from a context makes it a child of that context. |

For example, loading an account could produce this telemetry:

```text
example.account.load                         span
├─ attributes: account.id=123, found=true   facts about the span
├─ event: example.cache.lookup              occurrence during the span
│  └─ attribute: cache.hit=false            fact about the event
└─ status: ok                               final outcome
```

A span is diagnostic data, not business state. Recording it must not change whether the account load runs, succeeds, fails, or is persisted. An adapter translates these generic concepts into the corresponding concepts used by OpenTelemetry, Sentry, logs, or another backend.

## Core Context API

A `TelemetryContext` starts a span around a callback. The callback receives a `TelemetrySpan`, which is also the explicit parent context for child spans.

```typescript
import {
  NOOP_TELEMETRY_CONTEXT,
  type TelemetryContext,
} from '@earendil-works/pi-telemetry';

async function loadAccount(
  accountId: string,
  telemetryContext: TelemetryContext = NOOP_TELEMETRY_CONTEXT,
) {
  return telemetryContext.startSpan(
    {
      name: 'example.account.load',
      attributes: { 'example.account.id': accountId },
    },
    async (span) => {
      const account = await readAccount(accountId);
      span.setAttributes({ 'example.account.found': account !== undefined });
      return account;
    },
  );
}
```

Pass the callback span to lower-level work to create explicit nesting:

```typescript
return telemetryContext.startSpan({ name: 'example.parent' }, async (parentSpan) => {
  return parentSpan.startSpan({ name: 'example.child' }, async (childSpan) => {
    childSpan.addEvent('example.cache.lookup', { 'example.cache.hit': true });
    return performWork();
  });
});
```

There is no public `end()` method. `startSpan()` owns settlement and keeps the span open until the callback's value or promise settles. For an expected failure represented by a normal return value, set the status explicitly:

```typescript
return telemetryContext.startSpan({ name: 'example.save' }, async (span) => {
  const result = await save();
  if (!result.ok) {
    span.setStatus({
      status: 'error',
      error: { name: 'SaveError', message: result.reason },
    });
  }
  return result;
});
```

## Adapter Contract

An adapter implements `TelemetryContext` and bridges the generic API to its backend. It must:

- create a child span and invoke the callback synchronously, exactly once;
- preserve the callback's returned value and rejection value, returning a promise rejected with the same value after a synchronous throw;
- keep the native span open until a returned promise settles;
- treat normal completion as `ok` and throws/rejections as errors unless an explicit status was set;
- make repeated `setStatus()` calls last-write-wins;
- merge `setAttributes()` calls, with later defined values replacing earlier values and `undefined` ignored;
- make recording methods synchronous, passive, and non-throwing;
- ignore calls made after settlement;
- ignore a failed recording call atomically, suppress backend failures, and still execute the business callback exactly once.

Adapters may activate backend-native ambient context internally for automatic instrumentation, but pi code always propagates the parent through `TelemetryContext` arguments. Exporter buffering, flushing, sampling, backend IDs, and backend-specific context objects belong to the adapter. Use the [adapter conformance suite](#adapter-conformance) to check these observable semantics.

## No-op Context

Use `NOOP_TELEMETRY_CONTEXT` when telemetry is optional:

```typescript
import { NOOP_TELEMETRY_CONTEXT } from '@earendil-works/pi-telemetry';

const result = await NOOP_TELEMETRY_CONTEXT.startSpan(
  { name: 'example.operation' },
  () => runOperation(),
);
```

The no-op context:

- invokes callbacks synchronously;
- preserves returned values and asynchronous rejections, and converts a synchronous throw to a promise rejected with the same value;
- uses one shared frozen inert span, including for nested spans;
- does not inspect or retain names, attributes, events, or statuses.

## In-Memory Reference Adapter

`InMemoryTelemetryContext` is the backend-neutral reference implementation. It is useful for tests, local diagnostics, and applications that intentionally want process-local capture without an exporter:

```typescript
import { InMemoryTelemetryContext } from '@earendil-works/pi-telemetry';

const telemetry = new InMemoryTelemetryContext();

await telemetry.startSpan(
  { name: 'example.operation', attributes: { input: 'demo' } },
  async (span) => {
    span.addEvent('example.started');
    span.setAttributes({ output_count: 3 });
  },
);

console.log(telemetry.getSpans());
```

`getSpans()` returns detached snapshots in span-start order. Each `RecordedTelemetrySpan` contains a deterministic numeric ID, parent ID, merged attributes, ordered events, final status, settlement state, and deterministic end sequence. It records no timestamps.

The adapter is safe to use as an ordinary `TelemetryContext`, but storage is unbounded and process-local. Create a fresh instance to isolate tests or recording scopes, and do not capture sensitive attributes unless the caller's data policy allows them.

## Adapter Conformance

`@earendil-works/pi-telemetry/testing` exports a runner-independent conformance suite modeled as grouped cases. A fixture supplies a fresh context and converts its backend's finished spans into normalized `RecordedTelemetrySpan` snapshots:

```typescript
import {
  createTelemetryAdapterConformance,
  type TelemetryAdapterFixture,
} from '@earendil-works/pi-telemetry/testing';
import { describe, it } from 'vitest';

const conformance = createTelemetryAdapterConformance(async () => {
  const adapter = createMyTelemetryAdapter();
  return {
    context: adapter.context,
    getSpans: async () => adapter.normalizedSpans(),
    async [Symbol.asyncDispose]() {
      await adapter.close();
    },
  } satisfies TelemetryAdapterFixture;
});

for (const group of new Set(conformance.map((testCase) => testCase.group))) {
  describe(group, () => {
    for (const testCase of conformance.filter((candidate) => candidate.group === group)) {
      it(testCase.name, () => testCase.run());
    }
  });
}
```

The suite checks synchronous single admission, result and rejection identity, automatic and explicit status, attribute merging, event ordering, inert post-settlement calls, nested and concurrent parentage, and suppression of unreadable telemetry payload failures. `getSpans()` may flush an asynchronous exporter before returning. The testing subpath uses Node's assertion APIs; the root telemetry package remains runtime-neutral.

## Typed Schemas

The low-level span API intentionally accepts open names and attribute bags so adapters remain generic. Domain packages can define closed, serializable schemas and infer exact TypeScript types from them.

```typescript
import {
  createTypedSpanStarter,
  defineTelemetrySchema,
} from '@earendil-works/pi-telemetry';

export const EXAMPLE_TELEMETRY_SCHEMA = defineTelemetrySchema({
  version: 1,
  spans: {
    'example.read': {
      description: 'Read one resource',
      parents: { kind: 'any' },
      startAttributes: {
        'example.resource': {
          type: 'string',
          required: true,
          values: ['account', 'project'],
          description: 'Resource kind',
        },
      },
      endAttributes: {
        'example.item_count': {
          type: 'number',
          description: 'Number of returned items',
        },
      },
      events: {
        'example.cache': {
          description: 'Cache lookup result',
          attributes: {
            'example.cache.hit': {
              type: 'boolean',
              required: true,
              description: 'Whether the cache contained the resource',
            },
          },
        },
      },
      status: {
        default: 'ok',
        errorWhen: 'The read throws or returns an error result',
      },
    },
  },
} as const);

const startSpan = createTypedSpanStarter(
  telemetryContext,
  [EXAMPLE_TELEMETRY_SCHEMA],
);
```

The starter exposes one overload per span and checks names and attributes at compile time. Union-valued names must be narrowed before a call, preserving the relationship between each runtime name and its attribute schema. Its callback receives a child starter over the same schemas, already bound to the callback span:

```typescript
await startSpan(
  'example.read',
  { 'example.resource': 'account' },
  async (span, startChildSpan) => {
    span.addEvent('example.cache', { 'example.cache.hit': true });
    const accounts = await readAccounts();
    span.setAttributes({ 'example.item_count': accounts.length });

    await startChildSpan(
      'example.read',
      { 'example.resource': 'project' },
      async (childSpan) => {
        const projects = await readProjects();
        childSpan.setAttributes({ 'example.item_count': projects.length });
      },
    );

    return accounts;
  },
);
```

### Start and Completion Attributes

`startAttributes` and `endAttributes` describe when an attribute is normally known, not separate runtime storage:

| Schema field | How values are recorded | Requiredness |
|---|---|---|
| `startAttributes` | Passed in the typed starter's `attributes` argument when the span is created | Each definition explicitly sets `required: true` or `false` |
| `endAttributes` | Added later through the schema-scoped span's `setAttributes()` method | Always optional |

Both sets become ordinary attributes on the same backend span. There is no separate end-attribute payload or end callback. In the preceding example, `example.resource` is known when `example.read` starts, while `example.item_count` is known only after `readAccounts()` returns:

```typescript
await startSpan(
  'example.read',
  { 'example.resource': 'account' }, // required start attribute
  async (span) => {
    const accounts = await readAccounts();
    span.setAttributes({
      'example.item_count': accounts.length, // optional completion attribute
    });
    return accounts;
  },
); // resolving the callback settles the span
```

“End” means completion enrichment: an end attribute may be set at any point while the callback is active, and it may be omitted when unavailable. Calling `setAttributes()` zero times is valid. This matters for early failures, cancellation, and provider-specific data that may not exist on every path.

Repeated `setAttributes()` calls merge into the same attribute bag. A later defined value replaces an earlier value for the same key, while `undefined` is ignored. The schema-scoped method accepts only the current span's declared end attributes.

Attributes do not end the span. Returning, resolving, throwing, or rejecting from the callback controls settlement; `startSpan()` performs the actual end operation. Adapter calls made after settlement are inert.

A starter can compose multiple independently versioned schemas:

```typescript
import { AGENT_TELEMETRY_SCHEMAS } from '@earendil-works/pi-agent-core';

const startAgentSpan = createTypedSpanStarter(
  telemetryContext,
  AGENT_TELEMETRY_SCHEMAS,
);
```

Inline schema arrays retain their tuple types automatically. Separately declared arrays should use `as const`. Literal duplicate span names across the array are rejected at compile time; schemas are not merged, inspected, or retained at runtime.

Schema-derived types reject missing required attributes, unknown keys, invalid closed-set values, undeclared events, and attributes on empty schemas. End attributes are always optional enrichment; the type system does not require `setAttributes()` to be called.

`defineTelemetrySchema()` is a typed identity function. It returns ordinary JSON-serializable data and performs no runtime validation or parent-rule enforcement.

## Schema Metadata

Supported attribute types are:

- `string`, `number`, and `boolean`;
- `string[]`, `number[]`, and `boolean[]`.

Attribute definitions support:

- `values`: a closed set for scalar values;
- `elementValues`: a closed set for array elements;
- `examples`: documentation examples;
- `sensitive`: marks data requiring special handling;
- `cardinality`: records expected `low` or `high` cardinality.

Start and event attributes declare `required`. End attributes do not; see [Start and Completion Attributes](#start-and-completion-attributes).

Parent metadata is descriptive schema data:

- `{ kind: 'any' }`: root or any caller span;
- `{ kind: 'root_or_external' }`: root or a caller-owned span outside the schema;
- `{ kind: 'spans', spans: [...] }`: only the listed schema spans.

Adapters do not need to understand schema objects. Instrumentation helpers and tests use them to keep emitted names and attributes consistent.

## Pi Package Integration

Package ownership is intentionally split:

- `@earendil-works/pi-telemetry` owns the vendor-neutral contract, no-op and in-memory reference contexts, schema utilities, and adapter conformance suite;
- `@earendil-works/pi-ai` accepts and propagates `telemetryContext` in provider request options but owns no telemetry schema;
- `@earendil-works/pi-agent-core` owns and exports the pi AI-request and harness schemas, their combined readonly schema tuple, and typed span helpers.

```typescript
import {
  AGENT_TELEMETRY_SCHEMAS,
  AI_TELEMETRY_SCHEMA,
  HARNESS_TELEMETRY_SCHEMA,
  startAiSpan,
  startHarnessSpan,
} from '@earendil-works/pi-agent-core';
```

The pi schemas use pi-owned `pi.ai.*`, `pi.harness.*`, and `pi.session.*` names. Adapters may translate them to backend conventions without changing the emitted pi vocabulary.

## Security and Portability

Telemetry is process-local diagnostics, not durable application state. Do not persist a `TelemetryContext`, `TelemetrySpan`, or backend-native trace object in records, messages, snapshots, or deferred handles.

Attribute values are intentionally limited to primitive scalars and arrays. Domain instrumentation should avoid prompts, completions, tool arguments or output, file contents, provider payloads, headers, credentials, and free-form error details unless its schema and data policy explicitly allow them.

The package does not use `AsyncLocalStorage` or another runtime-specific ambient context API. It is suitable for Node.js, Bun, browsers, and workers; backend adapters remain responsible for their own runtime compatibility.

## API Reference

### Core types and values

| Export | Purpose |
|---|---|
| `TelemetryContext` | Starts callback-managed child spans |
| `TelemetrySpan` | Records attributes, events, and status; also acts as a child context |
| `SpanOptions` | Span name and optional start attributes |
| `SpanAttributes` / `AttributeValue` | Open adapter-level attribute bag and supported values |
| `SpanStatus` | Explicit `ok` or `error` status |
| `NOOP_TELEMETRY_CONTEXT` | Shared passive context for disabled telemetry |
| `InMemoryTelemetryContext` | Reference adapter with deterministic process-local recording |
| `RecordedTelemetrySpan` | Normalized captured span snapshot |
| `RecordedTelemetryEvent` | Normalized captured event snapshot |

### Schema definitions and inference

| Export | Purpose |
|---|---|
| `defineTelemetrySchema()` | Typed identity helper for serializable schema data |
| `createTypedSpanStarter()` | Binds a parent context to one or more schema vocabularies |
| `TypedSpanStarter` | Exact starter type with recursively child-bound callbacks |
| `TelemetrySchemaDefinition` | Top-level schema shape |
| `TelemetrySpanDefinition` | Span metadata, parents, attributes, events, and status rule |
| `TelemetryAttributeType` | Supported scalar and array type names |
| `TelemetryAttributeMetadata` | Description, sensitivity, and cardinality metadata |
| `TelemetryAttributeDefinition` | Attribute type, allowed values, examples, and metadata |
| `TelemetryStartAttributeDefinition` | Start attribute definition with requiredness |
| `TelemetryEventAttributeDefinition` | Event attribute definition with requiredness |
| `TelemetryEventDefinition` | Event description and attribute definitions |
| `TelemetryParentDefinition` | Open, external-root, or finite schema-parent rule |
| `TelemetrySchemaSpanName` | Union of declared span names |
| `TelemetrySchemaSpanStartAttributes` | Exact inferred start attributes for one span |
| `TelemetrySchemaSpanEndAttributes` | Optional inferred end attributes for one span |
| `TelemetrySchemaSpanEventName` | Union of events declared by one span |
| `TelemetrySchemaSpanEventAttributes` | Exact inferred attributes for one event |
| `SchemaTelemetrySpan` | Span view restricted to one schema span |
| `TelemetrySchemaSpanUnion` | Discriminated union of all spans in a schema |
| `InferStartAttributes` | Required and optional values inferred from start definitions |
| `InferOptionalAttributes` | Optional values inferred from end definitions |
| `InferEventAttributes` | Required and optional values inferred from event definitions |
| `InferRequiredAndOptionalAttributes` | Shared inference utility for definitions with requiredness |
| `ExactTelemetryAttributes` | Rejects keys outside an expected attribute set |

### Testing subpath

| Export | Purpose |
|---|---|
| `createTelemetryAdapterConformance()` | Creates runner-independent adapter conformance cases |
| `TelemetryAdapterFixture` | Fresh context and normalized snapshot reader for one case |
| `TelemetryAdapterFixtureFactory` | Creates isolated fixtures |
| `TelemetryAdapterConformanceCase` | Grouped case that test runners execute |

## Development

From this package directory:

```bash
npm test
npm run build
```

Repository-wide type checking, formatting, linting, and smoke checks run with:

```bash
npm run check
```

## License

MIT
