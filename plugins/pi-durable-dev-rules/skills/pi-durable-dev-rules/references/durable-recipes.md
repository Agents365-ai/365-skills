# Pi Durable: Recipes

Working patterns for building on `@earendil-works/pi-durable`, distilled from the package's 32
runnable examples, plus the project setup and the pitfalls that bite first. Code here is condensed:
the full versions are in the example file named in each heading.

## 0. Project setup

```bash
npm install @earendil-works/pi-durable @earendil-works/pi-ai @earendil-works/chord
```

Optional, per feature: `@earendil-works/pi-codemode` for code mode, `@silvia-odwyer/photon` for image
processing. `typebox` arrives with pi-ai; import `Type` from `@earendil-works/pi-ai` rather than adding
a second copy.

Node 22.19 or newer, ESM. The package ships source maps and `"source"` export conditions, so during
development you can run TypeScript directly:

```bash
node --conditions=source --experimental-strip-types app.ts
```

Type checking needs `module`/`moduleResolution` set to `nodenext` (or `bundler`) and `strict` on;
`exactOptionalPropertyTypes` is worth having, because the API distinguishes an absent field from
`undefined`.

Model access needs credentials for the provider you use: `createModels()` reads the provider's
environment variables (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, ...), or register a provider factory that
reads a credential store. `models` is also what `runtime.models` and `api.models` expose to tasks and
tools.

Two context values are used throughout:

```ts
import { BACKGROUND_CONTEXT, withCancel } from "@earendil-works/chord/context";

const context = BACKGROUND_CONTEXT;                        // in scripts and tests
const { context: sessionContext, cancel } = withCancel(BACKGROUND_CONTEXT);   // in a host, so a user abort
                                                          // cancels waits without cancelling the harness
```

## 1. Example catalog

Run any example from the package directory:

```bash
node --conditions=source --experimental-strip-types test/examples/14-chat.ts
```

| Example | Shows |
| ------- | ----- |
| `00-conversation.ts` | `createSession()`, one commit that creates a conversation |
| `01-documents.ts` | `defineDoc()`, `tx.doc()`, `snapshot()`, `snapshotAsOf()` |
| `02-forks.ts` | forking at an entry, fork semantics of documents |
| `03-owned-conversations.ts` | conversation ownership by a task |
| `04-chord-state.ts` | the Chord state underneath documents |
| `05-watches.ts` | `watchDoc()` and `session.watch()` |
| `06-harness.ts` | `Harness.open()` over a session |
| `07-configuration.ts` | agent changes, `configure()`, per-conversation settings |
| `08-harness-conversations.ts` | creating and listing conversations |
| `09-context.ts` | `context()`: raw entries, contributions, model messages |
| `10-registry-reload.ts` | installing and uninstalling extensions while running |
| `11-extension-state.ts` | an extension's own document, read by a section |
| `12-tasks.ts` | `defineTask()`, phases, checkpoints, `waitForTask()` |
| `13-recovery.ts` | a crash between a task's steps, and the rerun |
| `14-chat.ts` | one question and answer, with a prompt section |
| `15-system-prompt.ts` | sections, positional `pi.system` entries, tool changes |
| `16-real-model.ts` | streaming an answer from a real provider |
| `17-coding-tools.ts` | a tool-using turn on JSONL storage, with timing hooks |
| `18-print.ts` | print mode: submit, print the answer |
| `19-json.ts` | agent events or raw view operations, on SQLite/JSONL/memory |
| `20-inbox.ts` | steers, follow-ups, writes, withdrawal while busy |
| `21-late-join.ts` | attaching a view and an event stream mid-run |
| `22-subagent-foreground.ts` | a replay-safe subagent tool owning a child conversation |
| `23-subagent-background.ts` | persistent subagents: spawn, steer, stop, list, report back, restart-safe |
| `24-child-tasks.ts` | a checkout owning four payments: `failFast`, abort, restart |
| `25-compaction.ts` | a long chat compacted in the background, manually, after overflow |
| `26-coding-agent.ts` | coding tools, live settings, an environment per conversation |
| `27-plan-mode.ts` | read-only plan mode as an extension with its own document |
| `28-reviewer.ts` | a second conversation with its own model, tools, and directory |
| `29-sandbox-per-conversation.ts` | an environment looked up from an application document |
| `30-tool-override.ts` | a same-name tool for some conversations, a wrapper timing whichever won |
| `31-reload-and-restart.ts` | reloading an extension mid-call, stored choices surviving a restart |

## 2. Recipes

### 2.1 Minimal chat turn

```ts
import { BACKGROUND_CONTEXT } from "@earendil-works/chord/context";
import { builtinModels } from "@earendil-works/pi-ai/providers/all";
import { AssistantEntry, createRegistry, Harness, MemoryStorage } from "@earendil-works/pi-durable";

const context = BACKGROUND_CONTEXT;
const harness = await Harness.open(new MemoryStorage(), { models: builtinModels(), registry: createRegistry() }, context);
const root = await harness.root(context, { agent: { model: { provider: "openai", modelId: "gpt-6-sol" } } });

const submission = await root.submit({ type: "input", content: "What is the capital of France?" }, context);
const settled = await submission.wait(context);
if (settled.status === "done" && settled.type === "input") {
	const answer = await root.commit((tx) => tx.entry(AssistantEntry, settled.answer), context);
	console.log(answer?.model?.[0]);
}
await harness.close(context);
```

`submit()` admits the input durably and returns immediately; `wait()` resolves when the input is
answered (`done`) or cannot be (`unanswered`, with a reason). The answer is an entry ID: read the entry
to get the assistant message. Cancelling the context passed to `wait()` cancels only that wait.

### 2.2 Persistent app, restart, and exactly-once input

```ts
import { openNodeSqliteStorage } from "@earendil-works/pi-durable/storage/sqlite/node";

const harness = await Harness.open(await openNodeSqliteStorage("./session.sqlite"), { models, registry }, context);
const root = await harness.root(context);
harness.resume();                                        // continue work the last process left unfinished

const submission = await root.submit({ type: "input", content: "Hello", requestId: "greeting-1" }, context);
// After a restart, the same request ID returns the existing submission instead of admitting another.
await root.submit({ type: "input", content: "Hello", requestId: "greeting-1" }, context);
```

Use SQLite for anything long-running: JSONL keeps the whole history in memory. One process owns a
storage at a time. `harness.submission(id)` reacquires a submission after a restart. `requestId` is
scoped to one conversation, which makes it the restart-safe way for a recovered task to post a message.

### 2.3 Live UI: view state, watches, progress cadence

```ts
const view = await root.viewState(context);
view.subscribe((value) => {
	render({
		entries: value.entries,                                   // the active transcript
		live: value.docs["pi.live"],                              // partial answer, retry, tools, nested calls
		inbox: value.docs["pi.inbox"], usage: value.docs["pi.usage"],
		agent: value.docs["pi.agent"], provider: value.docs["pi.provider"],
	});
});

// The same value with the exact Chord operations of each commit, for a remote client:
const watch = await root.watch(context);
watch.start(async (value, ops) => { await send(ops); });
// later: view.dispose(); await watch.stop();
```

Partial answers and tool output are committed at most every 100 ms by default; `settings.progress`
changes that, and a host with remote storage should commit less often (`{ partialIntervalMs: 500,
outputIntervalMs: 500 }`) in exchange for a larger crash window. A slow watch keeps at most 100
undelivered frames, then collapses them into one full-value replacement, so a consumer that must see
every transition has to journal it itself.

### 2.4 Coding-agent style events

```ts
import { watchEvents } from "@earendil-works/pi-durable";

const stream = await watchEvents(harness, root.id, context);
initialize(stream.snapshot);
stream.start(async (events) => { for (const event of events) console.log(JSON.stringify(event)); });
```

Events are derived from the same commits, one batch per commit, with deltas for text, thinking, tool
arguments, and tool output (`message_start`, `message_update`, `tool_execution_start`,
`tool_execution_update`, `message_end`, `compaction_start`, `compaction_end`, ...). A consumer more
than 100 batches behind receives a fresh `snapshot` instead. `test/examples/19-json.ts` prints the whole
stream of one run.

### 2.5 A tool with structured output

```ts
import { Type } from "@earendil-works/pi-ai";
import { defineExtension, defineTool } from "@earendil-works/pi-durable";

const lines = defineTool({
	name: "lines",
	description: "Count the lines of a file",
	parameters: Type.Object({ path: Type.String() }),
	structuredOutputSchema: Type.Object({ lines: Type.Number() }),
	execute: async (args, api, context) => {
		const text = await (await api.env!.readTextFile(args.path, context));
		if (!text.ok) throw new Error(text.error.message);
		const count = text.value.split("\n").length;
		return { output: [{ type: "text", text: `${count} lines` }], structuredOutput: { lines: count } };
	},
});
registry.install(defineExtension({ name: "lines", tools: [lines] }));
```

Three channels matter: `output` is what the model reads, `structuredOutput` is what programs calling
the tool read (and is validated against `structuredOutputSchema`), and `details` is for the host UI.
Only `output` and `details` enter the transcript. `api.output()` streams running output and becomes
`output` when the result omits it; `api.diagnostic()` adds a model-visible remark such as a truncation
notice; `result.usage` is added to `pi.usage.tools`.

Each call is its own durable task. The intent is committed before `execute()` runs, so after a crash a
call reruns only when it declares `replay: "safe"`; otherwise the model gets an `interrupted` error
result carrying the output committed so far.

### 2.6 A tool that calls other tools

```ts
const testsPass = defineTool({
	name: "tests_pass",
	description: "Run the test suite and say whether it passed",
	parameters: Type.Object({}),
	execute: async (_args, api, context) => {
		const run = await api.executeTool("bash", { command: "npm test" }, context);
		const exitCode = (run.structuredOutput as { exitCode: number } | undefined)?.exitCode;
		return { output: [{ type: "text", text: exitCode === 0 ? "passed" : "failed" }] };
	},
});
```

The nested call is its own `pi.tool` task owned by the caller: it is validated, runs the `ToolTask`
hooks (which see `call.parent`), keeps its own output limits and replay policy, and reports into
`pi.live.nestedTools`. Its result comes back to the caller instead of entering the transcript, and
`progress: false` keeps its running output out of the live document. Keys make a rerun reattach: a
replay-safe caller that calls in the same order, or passes the same `{ key }`, gets the nested call it
already made back. `usage` is already counted under the nested tool, so passing it on counts it twice.

`callers` decides who may call a tool. Behind code mode, the script tool is `callers: ["model"]` so
scripts cannot start scripts, and MCP-style tools can be `callers: ["tools"]` so the model is never
offered them.

### 2.7 A foreground subagent tool

```ts
const Subagent = defineExtension({
	name: "subagent",
	tools: [defineTool({
		name: "subagent",
		description: "Delegate a self-contained task to a subagent and get its answer back.",
		parameters: Type.Object({ task: Type.String() }),
		replay: "safe",
		execute: async (args, api, context) => {
			const child = await api.commit(async (tx) => {
				// Ownership remembers the child, so a rerun reuses it instead of creating another.
				const existing = (await tx.scanConversations({ ownerTaskId: api.taskId }, 1)).items[0];
				if (existing !== undefined) return existing.id;
				const created = await tx.createConversation({ ownership: { kind: "task", taskId: api.taskId } });
				await configure(tx, created.id, { extensions: { remove: [Subagent] } });   // no subagents of its own
				return created.id;
			}, context);
			await api.details({ conversationId: child }, context);                        // lets a UI attach
			const handle = (await api.conversation(child, context))!;
			const settled = await (await handle.submit(
				{ type: "input", content: args.task, requestId: `subagent:${api.taskId}` }, context)).wait(context);
			// ... read the child's answer entry and return its text
		},
	})],
});
```

A child conversation starts as a copy of its owner's agent, so it inherits the model, thinking level,
extensions, tools, and `cwd`; change what it should differ in with `configure()`. Aborting the tool call
aborts the child, and the call finishes only once the child's work is done. `22-subagent-foreground.ts`
also shows a UI indenting the child's events under the call through the call's `details`.

### 2.8 Persistent background subagents

`23-subagent-background.ts` is the product-grade version: one `subagent` tool that spawns, messages
(steer or follow-up), waits for, stops, and lists children. The pattern:

- Each child is owned by a **background anchor task**, so the parent's Esc and idle waits never reach
  it, and it survives the parent's abort.
- Each message is delivered by a background reporter task that posts the answer back to the parent as a
  follow-up input once it arrives.
- Every message and report carries a request ID, so a restart sends neither twice.

Use this when the child should outlive the turn; use 2.7 when the parent should wait for the answer.

### 2.9 Child tasks and durable waits

```ts
pay: async (task, runtime, context) => {
	await runtime.commit(async (tx) => {
		const payments: TaskId<PaymentResult>[] = [];
		for (const card of task.input.cards) {
			payments.push(await tx.createTask(Payment, { card }, { ownership: { kind: "task", taskId: task.id } }));
		}
		return { status: "waiting", checkpoint: { phase: "decide", payments }, on: payments, policy: "failFast" };
	}, context);
},
decide: async (task, runtime, context) => {
	const outcomes = await runtime.outcomes(task.state.checkpoint.payments, context);
	// ... commit this task's own outcome
},
```

A waiting task runs no code until every task in `on` is terminal. `failFast` gives the other live tasks
an abort mark as soon as one fails; the waiting task itself is not marked and reads the outcomes.
Aborting runs bottom-up: the children's abort handlers run before the parent's, so each task undoes its
own effect. An abort handler cannot create owned children (its task is abort-marked): it compensates
inline, or creates background conversation-owned tasks and waits with `runtime.waitForTask()`.

### 2.10 A coding agent

```ts
const registry = createRegistry();
registry.install(CodingTools);
registry.install(defineExtension({
	name: "coding",
	sections: [
		section("preamble", () => "You are a coding agent. Use the tools to inspect the project.", { tag: false }),
		section("cwd", (input) => input.env?.cwd),
	],
}));

const settings: HarnessSettings = {
	get toolExecution() { return userSettings.parallelTools ? "parallel" : "sequential"; },
	get retry() { return { maxRetries: userSettings.maxRetries }; },
};

const harness = await Harness.open(storage, {
	models, registry, settings,
	env: ({ cwd = workspace }) => new NodeExecutionEnv({ cwd }),
}, context);
const root = await harness.root(context, { agent: { model, cwd: workspace } });
```

The environment function is called per tool call, per section render, and per `runtime.env()`, so a
per-conversation directory or container needs no restart: `await root.configure({ cwd: other }, context)`
applies from the next use. Settings are read at every use and never stored, so a settings object with
getters gives the user live control. A section returning a value that differs every time (a clock)
appends a `pi.system` entry on every request and defeats provider prompt caching.

### 2.11 Plan mode: switch the agent, not the prompt

```ts
const read = createReadTool();
await root.configure({ extensions: { add: [Plan] }, tools: [read, submitPlan] }, context);   // enter
await root.configure({ extensions: null, tools: null }, context);                             // leave
```

An array selects exactly those tools; `null` clears a field back to the host default. The model sees the
switch as a positional `pi.system` entry naming the tools added and removed, so the prompt cache stays
warm for everything else. `27-plan-mode.ts` pairs this with a per-conversation plan document and
`control: { terminate: true }` on the tool that submits the plan.

### 2.12 One environment per conversation

```ts
const Sandbox = defineDoc<{ path?: string }>({
	kind: "app.sandbox", version: 1, scope: "conversation", history: "latest", fork: "initial", initial: () => ({}),
});

const harness = await Harness.open(storage, {
	models, registry,
	env: async ({ conversationId, read }, envContext) => {
		const sandbox = await read.snapshot(Sandbox, conversationId, envContext);
		return sandbox?.path === undefined ? undefined : new NodeExecutionEnv({ cwd: sandbox.path });
	},
}, context);

await harness.createConversation({
	ownership: { kind: "ownerless" },
	init: async (tx, id) => { (await tx.doc(Sandbox, id)).path = await makeSandbox(); },   // same commit
}, context);
```

`env` receives committed reads, so the document is the source of truth and no side table is needed. A
conversation without a sandbox gets no environment: its tools fail with an error result, which is a
clean failure rather than a fallback into the wrong directory. `fork: "initial"` keeps a fork from
inheriting the parent's sandbox.

### 2.13 Override a tool, decorate whichever one wins

```ts
// Same name as CodingTools' bash: selected later, it replaces it in place.
const Venv = defineExtension({ name: "venv", tools: [createBashTool({ commandPrefix: "source .venv/bin/activate" })] });

// Wraps the bash that won, whichever it is. The wrapper never captures a base tool, so a reload keeps working.
const Timing = defineExtension({
	name: "timing",
	wraps: [wrapTool(createBashTool(), (bash) => ({ ...bash,
		execute: async (args, api, context) => { const start = Date.now();
			try { return await bash.execute(args, api, context); } finally { timings.push(Date.now() - start); } } }))],
});
```

A later extension's tool with the same name replaces an earlier one where both are selected; `wraps`
apply where the wrapping extension is selected. Wrappers are pure: they describe a decoration, not an
instance, which is what makes reloading work. Uninstalling or replacing an extension only stops new
use: a call already running finishes under the code it started with.

### 2.14 Extension-owned state, and its migration

```ts
const Todos = defineDoc<{ items: string[] }>({
	kind: "app.todos", version: 1, scope: "conversation", history: "rewindable", fork: "asOf",
	initial: () => ({ items: [] }),
});

// write: in a tool
await api.commit(async (tx) => { (await tx.doc(Todos, api.conversationId)).items.push(args.item); }, context);

// read: in a section
section("todos", async (input, context) => {
	const todos = await input.read.snapshot(Todos, input.conversationId, context);
	return todos === undefined || todos.items.length === 0 ? undefined : todos.items.join("\n");
});
```

Only a typed `tx.doc()` creates an absent document; every read returns `undefined` for one that was
never created, so treat absence as the initial value. `history: "rewindable"` enables
`snapshotAsOf(token, conversationId, entryId, context)`, which is what `fork: "asOf"` uses. To change
the shape, raise `version` and add `migrate(value, fromVersion)`; a stored version newer than the code,
or an older one without `migrate`, makes access fail. Kinds are persisted protocol: a value migration
cannot rename a kind.

### 2.15 Hooks

```ts
const Guard = defineExtension({
	name: "guard",
	hooks: [
		hook(ToolTask, {
			beforeTool: (call) => (call.name === "bash" ? { block: "bash is disabled here" } : undefined),
			afterTool: (call, result) => (call.name === "read" ? redact(result) : undefined),
		}),
		hook(GenerationTask, { onYield: (answer) => (needsMoreWork(answer) ? { continue: "Keep going." } : undefined) }),
		hook(CompactionTask, { beforeCompact: () => ({ decline: true }) }),
	],
});
```

The first `block` wins; the first `beforeCompact` decision wins; the first `onYield` that returns
`{ continue }` appends that user message and continues the run. A throwing hook is reported through
`onReport` and skipped, and a throwing `beforeTool` blocks the call. Hooks share the asking task's memo
namespace with the task and with each other, so prefix memo names. A guard applies only where its
extension is selected: a conversation that selects tools as an explicit array and omits the guard runs
without it.

### 2.16 Compaction

```ts
const id = await root.compact("Keep the failing test names", context);
const { outcome } = (await harness.waitForTask(id, context)).state;
if (outcome.status === "completed" && outcome.result.submissionId !== undefined) {
	const placed = await (await harness.submission(outcome.result.submissionId, context))!.wait(context);
	// "done", or "unanswered" with reason "stale"
}
```

Automatic compaction is part of generation preparation: `settings.compaction` sets `enabled`,
`reserveTokens`, `keepRecentTokens`, and `backgroundTokens`. A generation blocks above
`contextWindow - reserveTokens`; below that, a background compaction starts once the context is within
`backgroundTokens` of the blocking threshold. After a provider rejects a request as too long, generation
compacts and retries once. Every attempt pays for a summarization request, including one that ends
`stale`; the newest failure stays in `docs["pi.live"].compactionFailure` until a compaction succeeds.

### 2.17 Code mode

```ts
import { CodemodeSandbox } from "@earendil-works/pi-codemode";
import { createCodemodeExtension } from "@earendil-works/pi-durable/codemode";

registry.install(createCodemodeExtension({
	sandbox: new CodemodeSandbox({ memoryLimitBytes: 256 * 1024 * 1024 }),
	namespaces: [{ name: "github", description: "GitHub MCP tools", prefix: "mcp__github__" }],
	inlineBudget: 3000,
}));
```

The model writes JavaScript that calls the conversation's tools as `await tools.<name>(args)`; each call
is a nested tool call and only the script's output reaches the model. The script survives a restart: the
sandbox reruns it deterministically and hands it the journaled results in order, so a rerun makes the
same calls, which reattach by key. A rerun that takes another path, whose sandbox fingerprint changed,
or whose `timeout_ms` passed ends with an error instead. A failing nested call rejects in the script
unless the tool declares `structuredOutputSchema` and returned its own value with the error, as `bash`
does for a nonzero exit, where the script should check `exitCode`.

### 2.18 Tool search for large tool sets

```ts
registry.install(createToolSearchExtension());
```

Mark a tool `deferred: true` and it is not offered to the model until loaded; other tools can call it at
any time. `tool_search` lets the model search the deferred tools and load matches with
`control.addTools`, recorded in the conversation's `modelTools`; loaded tools stay offered on that
branch, also after a compaction, and the `codemode` section leaves them out.

### 2.19 Testing a storage or an environment

```ts
import { registerStorageConformance } from "@earendil-works/pi-durable/testing";
import { describe, expect, it } from "vitest";

registerStorageConformance({ describe, expect, it }, "My Storage", async (use) => {
	const storage = await openMyStorage();
	try { await use(storage); } finally { await closeMyStorage(storage); }
});

registerEnvConformance({ describe, expect, it }, "My Env", async (use) => { /* same shape */ }, { shell: true, symlinks: true });
```

The conformance suites are what the built-in backends are held to, so passing them is the cheapest way
to know a custom backend is usable. For tests that exercise conversations, use the scripted provider
instead of a model:

```ts
import { fauxAssistantMessage, fauxProvider, fauxText, fauxToolCall } from "@earendil-works/pi-ai/providers/faux";

const faux = fauxProvider();
const models = createModels();
models.setProvider(faux.provider);
faux.setResponses([
	fauxAssistantMessage([fauxToolCall("read", { path: "notes.txt" }, { id: "r" })], { stopReason: "toolUse" }),
	fauxAssistantMessage([fauxText("Done.")]),
]);
```

`MemoryStorage` plus the faux provider gives a deterministic, synchronous-feeling test of a whole run,
including tool rounds and hooks.

## 3. Pitfalls

Check this before shipping; the normative list is spec section 12.

- **Read every table row before the first table write** in a commit callback; read only through `tx`.
- **Never await slow work inside a commit callback**: no models, tools, processes, network, humans,
  nested commits, or session waiters. The callback holds the session's mutation line.
- **Do not append raw entries to a conversation with an active run.** Use a write submission; a raw
  append can misplace the generation's positional system entries.
- **Do not mutate a value returned by `snapshot()`, a state, or a watch.** Those are tracked containers.
- **Prefix hook memo names**: hooks share the asking task's memo namespace.
- **Uninstalling an extension does not free its resources.** A running call still uses the old code.
- **A selection that omits a guard runs without the guard.** Hooks and wrappers are selected with their
  extension; they are not registry-wide.
- **`{ add, remove }` always edits the host default selection**, so a child that copied the owner's
  selection does not get the owner's set plus the edit. Compute the child's array from the resolved
  agent.
- **A task-owned conversation copies its owner's agent once**, at creation; later owner changes do not
  reach it.
- **A tool rerun builds its environment again** with the conversation's current `cwd`, which may differ
  from the first attempt's.
- **Queued items survive a failed run.** Their `wait()` stays pending until a boundary places them or
  the host withdraws them.
- **A skipped read can hang**: use `env.listFiles?.()` with a fallback rather than assuming it exists.
- **Keep terminal outcomes small.** Put large results in entries or longer-lived documents and keep
  only their IDs in the outcome; never reference a task document retired by that same outcome.
- **`pi.`-prefixed names belong to the built-ins**, for task names, document kinds, and entry kinds.
