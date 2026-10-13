# Pi Durable: API Surface

Exact signatures of the public surface of `@earendil-works/pi-durable` v1.2.0 and the `pi-ai` and
`chord` types it consumes. Read `durable-guide.md` for the narrative and `durable-runtime.md` for
the runtime rules; this file answers "what is the exact name, receiver, and shape".

The package is experimental: between releases a signature here can change. Confirm against the
package's `src/` when a build fails, and treat a mismatch as a version difference rather than a
typo.

## Entry points

| Import path | Holds |
| ----------- | ----- |
| `@earendil-works/pi-durable` | `Harness`, `createSession`, `defineTool`, `defineExtension`, `defineTask`, `defineDoc`, `defineDocFamily`, `defineEntry`, `section`, `hook`, `wrapTool`, `wrapSection`, `createRegistry`, `configure`, `watchEvents`, the built-in entries and tasks (`ToolTask`, `GenerationTask`, `CompactionTask`), the built-in documents (`AgentDoc`, `LiveDoc`, `InboxDoc`, `ProviderDoc`, `UsageDoc`, `NestedCallDoc`), `MemoryStorage`, the policy defaults, the error classes, and every public type |
| `@earendil-works/pi-durable/tools` | `read`, `write`, `edit`, `bash`, `createCodingTools`, `CodingTools`, `createPowerShellTool`, and the image-processor contracts |
| `@earendil-works/pi-durable/codemode` | `createCodemodeExtension`, `createCodemodeTool`, namespaces, the inline budget |
| `@earendil-works/pi-durable/tool-search` | `createToolSearchExtension`, `createToolSearchTool` |
| `@earendil-works/pi-durable/env` | the `ExecutionEnv`, `FileSystem`, and `Shell` contracts, `Result`, `FileError`, `ExecutionError` |
| `@earendil-works/pi-durable/env/node` | `NodeExecutionEnv`, `NodeWatchOptions` |
| `@earendil-works/pi-durable/storage/memory` | `MemoryStorage` |
| `@earendil-works/pi-durable/storage/sqlite` | `SqliteStorage`, `SqliteDatabase`, `SqliteExecutor`, `SqliteValue`, migrations |
| `@earendil-works/pi-durable/storage/sqlite/node` | `openNodeSqliteStorage`, `openNodeSqliteDatabase`, `NodeSqliteDatabase`, `NodeSqliteStorageOptions` |
| `@earendil-works/pi-durable/storage/sqlite/cloudflare` | `openDurableObjectSqliteStorage`, `DurableObjectSqliteDatabase` |
| `@earendil-works/pi-durable/storage/jsonl` | `JsonlStorage`, `JsonlStorageOptions`, `JsonlCorruptionError`, `JsonlStoragePoisonedError` |
| `@earendil-works/pi-durable/storage/jsonl/node` | `openNodeJsonlStorage` |
| `@earendil-works/pi-durable/images` | `createPhotonImages` |
| `@earendil-works/pi-durable/images/node` | `createNodePhotonImages` |
| `@earendil-works/pi-durable/images/cloudflare` | `createCloudflarePhotonImages` |
| `@earendil-works/pi-durable/testing` | `registerStorageConformance`, `registerEnvConformance`, `createStorageConformance`, `createEnvConformance`, `createExpectAssertions`, the storage benchmarks |

---

## 1. `Context` (`@earendil-works/chord/context`)

Every asynchronous call of the harness takes a `Context`. It carries cancellation only.

```ts
interface Context {
	readonly abortSignal: AbortSignal | undefined;
	value<T>(key: ContextKey<T>): T | undefined;
	toString(): string;
}

const BACKGROUND_CONTEXT: Context;   // never cancels
const TODO_CONTEXT: Context;

function createContextKey<T>(description: string): ContextKey<T>;
function withContextValue<T>(key: ContextKey<T>, value: T, parent: Context): Context;
function withAbortSignal(signal: AbortSignal, context: Context): Context;
function withoutAbortSignal(context: Context): Context;
function withCancel(context: Context): { readonly context: Context; readonly cancel: (reason?: unknown) => void };
function awaitWithContext<T>(promise: Promise<T>, context: Context): Promise<T>;
```

Rules that follow from this:

- Cancelling a context cancels only the wait that used it, never the durable work. `submission.wait(cancelled)`
  rejects while the run continues.
- `withoutAbortSignal()` is for mandatory cleanup such as `close()`, not for ordinary calls.
- Use `withCancel(BACKGROUND_CONTEXT)` at a host boundary so a user abort never cancels the harness itself.

---

## 2. Host assembly

```ts
const Harness = { open<Tool extends ToolRegistration>(storage: Storage, options: HarnessOptions<Tool>, context: Context): Promise<Harness> };

type HarnessOptions<Tool extends ToolRegistration = ToolRegistration> = {
	readonly models: Models;                       // pi-ai model access used by generation
	readonly registry: RegistryReader<Tool>;        // usually the `Registry` from createRegistry()
	readonly settings?: HarnessSettings;            // live run policy, read at every use, never stored
	readonly env?: (target: EnvTarget, context: Context) => ExecutionEnv | undefined | Promise<ExecutionEnv | undefined>;
	readonly conversationCreated?: (tx: Tx, conversation: ConversationRecord) => void | Promise<void>;
	readonly now?: () => number;
	readonly onReport?: (error: unknown) => void;
};

type EnvTarget = { readonly conversationId: ConversationId; readonly cwd?: string; readonly read: DocumentReader };
```

`Harness.open` throws when the registry lacks a built-in task, which happens when the registry was not
built with `createRegistry()`. It returns a `Harness`, which extends `Session`.

`createSession(storage)` returns the lower-level `Session` without the harness machinery: use it only
when writing tests of the storage and document layer, as `test/examples/00` to `05` do.

### Settings

Live policy. Every field is read at each use, so getters are supported and nothing is stored.

```ts
type HarnessSettings = {
	readonly extensions?: readonly Extension[];      // default selection; absent: every installed extension
	readonly stream?: ConversationStreamOptions;
	readonly retry?: Partial<ConversationRetryPolicy>;
	readonly compaction?: Partial<CompactionPolicy>;
	readonly progress?: Partial<ProgressPolicy>;
	readonly toolExecution?: ToolExecutionMode;      // "parallel" | "sequential"
	readonly steeringMode?: QueueMode;               // "all" | "one-at-a-time"
	readonly followUpMode?: QueueMode;
	readonly contextRetentionMs?: number;
	readonly documentRetentionMs?: number;
};

type ConversationStreamOptions = {
	transport?: Transport; timeoutMs?: number; maxRetries?: number; maxRetryDelayMs?: number;
	headers?: Record<string, string>; metadata?: JsonObject; cacheRetention?: CacheRetention;
	deferred?: boolean | { window?: "15m" | "1h" | "24h" };
};
type ConversationRetryPolicy = { enabled: boolean; maxRetries: number; baseDelayMs: number; maxAgentDelayMs?: number };
type CompactionPolicy = { enabled: boolean; reserveTokens: number; keepRecentTokens: number; backgroundTokens: number };
type ProgressPolicy = { partialIntervalMs: number; outputIntervalMs: number };
```

`DEFAULT_COMPACTION_POLICY`, `DEFAULT_PROGRESS_POLICY`, and `DEFAULT_RETRY_POLICY` are exported.
`HarnessSettings` is synchronous: some readers run on the Session mutation line, so a getter must not await.

### Registry

```ts
function createRegistry<Tool extends ToolRegistration = ToolRegistration>(): Registry<Tool>;

interface Registry<Tool> extends RegistryReader<Tool> {
	install(extension: Extension<Tool>): void;    // same name replaces in place, in one step
	uninstall(extension: Extension): void;        // removes by name, whichever object it is
}

interface RegistryReader<Tool> {
	snapshot(): RegistrySnapshot<Tool>;
	subscribe(listener: () => void): () => void;
}

interface RegistrySnapshot<Tool> {
	installed(): readonly Extension<Tool>[];
	extension(name: string): Extension<Tool> | undefined;
	tools(): readonly { readonly extension: Extension<Tool>; readonly tool: Tool }[];
	sections(): readonly { readonly extension: Extension<Tool>; readonly section: PromptSection<Tool> }[];
	tasks(): readonly AnyTask[];
	task(name: string): AnyTask | undefined;
}
```

---

## 3. `Harness` (extends `Session`)

```ts
interface Harness extends Session {
	resume(): void;                                        // start the task scheduler; idempotent
	root(context: Context, options?: { agent?: AgentChange; init?: ConversationInit }): Promise<Conversation>;
	conversation(id: ConversationId, context: Context): Promise<Conversation | undefined>;
	createConversation(options: ConversationCreateOptions, context: Context): Promise<Conversation>;
	getTask<R>(id: TaskId<R>, context: Context): Promise<TaskRecord<JsonValue, JsonValue, R> | undefined>;
	inspect(context: Context): Promise<HarnessInspection>;
	submission(id: SubmissionId, context: Context): Promise<Submission | undefined>;
	abortSubmission(id: SubmissionId, context: Context, conversationId?: ConversationId):
		Promise<"aborted" | "already_placed" | "settled" | "not_found">;
	abortTask(id: TaskId, context: Context): Promise<"marked" | "terminal">;
	waitForTask<R>(id: TaskId<R>, context: Context): Promise<SettledTask<R>>;
	waitForIdle(context: Context): Promise<void>;
	usage(context: Context): Promise<UsageState>;
	taskGraph(context: Context): Promise<AttachedReplicatedState<TaskGraph>>;
	watchTaskGraph(context: Context): Promise<TaskGraphWatch>;
}
```

Scheduling starts with `resume()` or with any call that asks for progress: `Conversation.submit()`,
`Conversation.compact()`, `Conversation.abort()`, `Submission.wait()`, `waitForTask()`,
`Harness.waitForIdle()`, `Conversation.waitForIdle()`. Read-only viewers never start it.

`Session` adds the commit line, document reads and observation, and the close contract:

```ts
interface Session extends DocumentObserver {
	commit<T>(change: (tx: Tx) => T | Promise<T>, context: Context): Promise<T>;
	close(context: Context): Promise<void>;
	readonly closed: Promise<SessionEnd>;                            // { reason: "closed" } | { reason: "failed"; error }
	subscribeCommits(listener: (publication: CommitPublication, context: Context) => void): () => void;
	subscribeClose(listener: () => void): () => void;
	snapshot<T extends JsonObject>(token: ConversationDocToken<T>, conversationId: ConversationId, context: Context): Promise<Readonly<T> | undefined>;
	snapshotAsOf<T extends JsonObject>(token: RewindableConversationDocToken<T>, conversationId: ConversationId, at: EntryId, context: Context): Promise<Readonly<T> | undefined>;
	documentState<T extends JsonObject>(token: ConversationDocToken<T>, conversationId: ConversationId, context: Context): Promise<DocumentState<T> | undefined>;
	watchDoc<T extends JsonObject>(token: ConversationDocToken<T>, conversationId: ConversationId, context: Context): Promise<DocumentWatch<T> | undefined>;
	// every one of the four above is overloaded for Session, Conversation, Task, and family documents
}

type SessionEnd = { readonly reason: "closed" } | { readonly reason: "failed"; readonly error: unknown };
type CommitPublication = { readonly seq: Seq; readonly changes: readonly CommitChange[] };
```

---

## 4. `Conversation`

A stateless handle. Compare handles by `id`.

```ts
interface Conversation {
	readonly id: ConversationId;

	agent(context: Context): Promise<Agent>;
	configure(change: AgentChange, context: Context): Promise<void>;

	submit(submission: SubmissionDraft, context: Context): Promise<Submission>;
	reset(handoff: string | undefined, context: Context): Promise<void>;
	compact(instructions: string | undefined, context: Context): Promise<TaskId<CompactionResult>>;

	commit<T>(change: (tx: Tx) => T | Promise<T>, context: Context): Promise<T>;
	context(context: Context, options?: { readonly at?: EntryId }): Promise<ContextView>;
	entries(query: Omit<EntryQuery, "conversationId">, limit: number, cursor: Cursor | undefined, context: Context): Promise<Page<EntryRecord, Cursor>>;
	fork(at: EntryId, options: ConversationCreateOptions, context: Context): Promise<Conversation>;

	abort(context: Context, options?: ConversationAbortOptions): Promise<void>;
	waitForIdle(context: Context): Promise<void>;
	viewState(context: Context): Promise<AttachedReplicatedState<ConversationView>>;
	watch(context: Context): Promise<ConversationWatch>;
}

type ConversationCreateOptions = {
	readonly ownership: ConversationOwnership;      // { kind: "ownerless" } | { kind: "task"; taskId }
	readonly agent?: AgentChange;
	readonly init?: ConversationInit;
};
type ConversationOwnership = { readonly kind: "ownerless" } | { readonly kind: "task"; readonly taskId: TaskId };
type ConversationAbortOptions = { readonly background?: boolean };
type ContextView = {
	readonly head: EntryRecord | undefined;
	readonly entries: readonly EntryRecord[];         // raw active transcript, head marker first
	readonly contributions: readonly (readonly Message[])[];   // per entry, after edits and stop-reason filtering
	readonly messages: readonly Message[];            // the model context of the next request
};
```

`ROOT_CONVERSATION_ID` is the reserved ID of the root conversation. `context({ at })` returns the view a
`fork(at)` would start with, without creating anything.

`ConversationHandle`, what a task or tool gets, is the narrow invocation-bound view:

```ts
interface ConversationHandle {
	readonly id: ConversationId;
	submit(submission: InputSubmissionDraft, context: Context): Promise<Submission>;
	abort(context: Context, options?: ConversationAbortOptions): Promise<void>;
	waitForIdle(context: Context): Promise<void>;
}
```

### Agent and agent changes

```ts
type AgentState = {
	model?: ModelRef;                                  // { provider, modelId }
	thinkingLevel?: ModelThinkingLevel;
	extensions?: string[] | { add?: string[]; remove?: string[] };
	tools?: string[] | { remove: string[] };
	modelTools?: string[] | { remove?: string[]; add?: string[] };
	instructions?: string;
	cwd?: string;
};

type AgentChange = {
	model?: ModelRef | null; thinkingLevel?: ModelThinkingLevel | null;
	extensions?: readonly Extension[] | { add?: readonly Extension[]; remove?: readonly Extension[] } | null;
	tools?: readonly ToolRegistration[] | { remove: readonly ToolRegistration[] } | null;
	modelTools?: readonly ToolRegistration[] | { remove?: readonly ToolRegistration[]; add?: readonly ToolRegistration[] } | null;
	instructions?: string | null; cwd?: string | null;
};

type Agent<Tool extends ToolRegistration = ToolRegistration> = {
	readonly model?: ModelRef;
	readonly thinkingLevel: ModelThinkingLevel;
	readonly extensions: readonly Extension<Tool>[];
	readonly tools: readonly Tool[];        // offered to the model, in order
	readonly callable: readonly Tool[];     // nested `executeTool()` calls resolve among these
	readonly deferred: readonly Tool[];     // enabled, not offered yet
	readonly sections: readonly PromptSection<Tool>[];
	readonly instructions?: string;
	readonly cwd?: string;
};
```

`configure(tx, conversationId, change)` is the free function form, for use inside a commit callback
(for example when creating a child conversation). A given field replaces the stored one, `null` clears it
back to the host default, `undefined` changes nothing.

---

## 5. Submissions and the inbox

```ts
type SubmissionDraft = { readonly requestId?: string } & (
	| { readonly type: "input"; readonly content: UserInput; readonly whenBusy?: "steer" | "followUp" | "reject";
	    readonly entry?: InputEntry }
	| { readonly type: "write"; readonly entry: EntryDraft }
);

type InputEntry = { readonly kind: string; readonly data?: JsonValue };   // kind must not start with "pi."
type UserInput = UserMessage["content"];

interface Submission {
	readonly id: SubmissionId;
	status(context: Context): Promise<SubmissionRecord>;
	wait(context: Context): Promise<SettledSubmissionRecord>;
	abort(context: Context): Promise<"aborted" | "already_placed" | "settled">;
}

type SettledSubmissionRecord = SubmissionRecord & { readonly status: "done" | "unanswered" };

type SubmissionRecord =
	| ({ id; conversationId; requestId?; type: "input" } & (
		| { status: "queued" }
		| { status: "placed"; entry: EntryId }
		| { status: "done"; entry: EntryId; answer: EntryId }
		| { status: "unanswered"; entry?: EntryId; reason: string; detail?: JsonValue }))
	| ({ id; conversationId; requestId?; type: "write" } & (
		| { status: "queued" }
		| { status: "done"; entry: EntryId }
		| { status: "unanswered"; reason: string; detail?: JsonValue }));
```

`requestId` is scoped to one conversation and deduplicates: resubmitting with the same ID returns the
existing submission. That is the restart-safe way to send a message from a recovered task.

Queueing rules: a busy conversation queues input in `pi.inbox`; `whenBusy: "reject"` throws
`ConversationBusy` instead. A write of only `kind` and `data` touches nothing the model sees and is
appended at once, even mid-run, and is never queued. A write with `model`, `head`, or `edits` waits for
the next boundary.

---

## 6. `Tx`: the transaction surface

Every write happens in `Session.commit()`, `Conversation.commit()`, `ToolExecutionApi.commit()`, or
`TaskRuntime.commit()`. Inside the callback read only through `tx`.

```ts
interface Tx {
	conversation(id: ConversationId): Promise<ConversationRecord | undefined>;
	entry(id: EntryId): Promise<EntryRecord | undefined>;
	entry<D extends JsonValue>(token: Entry<D>, id: EntryId): Promise<TypedEntry<D> | undefined>;
	task(id: TaskId): Promise<TaskRecord<JsonValue, JsonValue, JsonValue> | undefined>;
	scanConversations(query: ConversationQuery, limit: number, cursor?: Cursor): Promise<Page<ConversationRecord, Cursor>>;
	scanEntries(query: EntryQuery, limit: number, cursor?: Cursor): Promise<Page<EntryRecord, Cursor>>;
	scanTasks(query: TaskQuery, limit: number, cursor?: Cursor): Promise<Page<TaskRecord<JsonValue, JsonValue, JsonValue>, Cursor>>;
	latestHeadMarker(conversationId: ConversationId): Promise<(EntryRecord & { readonly head: EntryId }) | undefined>;
	submissionByRequest(conversationId: ConversationId, requestId: string): Promise<SubmissionRecord | undefined>;

	createConversation(options: { readonly ownership: ConversationOwnership }): Promise<ConversationRecord>;
	forkConversation(parentConversationId: ConversationId, at: EntryId, options: { readonly ownership: ConversationOwnership }): Promise<ConversationRecord>;
	appendEntry(conversationId: ConversationId, value: EntryDraft): Promise<EntryRecord>;
	appendEntry<D extends JsonValue>(token: Entry<D>, conversationId: ConversationId, value: TypedEntryDraft<NoInfer<D>>): Promise<TypedEntry<D>>;
	createTask<I, S extends { phase: string }, R, H extends object>(task: Task<I, S, R, H>, input: I, options: TaskOptions): Promise<TaskId<R>>;
	createSubmission(create: SubmissionCreate): Promise<SubmissionRecord>;
	settleSubmission(id: SubmissionId, settlement: SubmissionSettlement): void;
	placeSubmission(id: SubmissionId, entry: EntryId): void;

	doc<T extends JsonObject>(token: ConversationDocToken<T>, conversationId: ConversationId): Promise<Draft<T>>;
	doc<T extends JsonObject>(token: SessionDocToken<T>): Promise<Draft<T>>;
	doc<T extends JsonObject>(token: TaskDocToken<T>, taskId: TaskId): Promise<Draft<T>>;
	doc<T, I>(token: ConversationDocFamilyToken<T, I>, conversationId: ConversationId, key: string, seed: I): Promise<Draft<T>>;
	// ... plus the Session and Task family overloads
	retireDoc(token, ...owner): Promise<void>;   // same overload set as doc()
}
```

`Draft<T>` is a mutable tracked copy from `@earendil-works/chord/delta`; assign to it and the change is
stored when the commit settles. `tx.createSubmission()` and the placement methods are for a host that
implements admission itself; `Conversation.submit()` covers ordinary use.

`ConversationQuery`/`TaskQuery`/`SubmissionQuery` carry `order` (`"ascending"` oldest first,
`"descending"` newest first) and the filters you would expect: `ownerConversationId`, `ownerTaskId`,
`conversationId`, `kind`, `status`, `abortRequested`, `background`. `EntryQuery` carries
`conversationId`, `minEntryId`, `maxEntryId`, `order`.

---

## 7. Documents

```ts
function defineDoc<T extends JsonObject>(definition: DocDefinition<T>): DocToken<T, DocDefinition<T>>;
function defineDocFamily<T extends JsonObject, I extends JsonValue>(definition: DocFamilyDefinition<T, I>): DocFamilyToken<T, I, DocFamilyDefinition<T, I>>;

type CommonDocDefinition<T extends JsonObject> = {
	readonly kind: string;                 // stable persisted kind; public protocol
	readonly version: number;              // positive integer, the shape of the stored value
	initial(): T;
	migrate?(value: JsonObject, fromVersion: number): T;
	checkpointWhen?(value: Readonly<T>, ops: readonly Op[], info: { readonly deltasSinceBase: number }): boolean;
};

type DocumentSemantics =
	| { readonly scope: "session" }
	| { readonly scope: "conversation"; readonly history: "latest"; readonly fork: "current" | "initial" }
	| { readonly scope: "conversation"; readonly history: "rewindable"; readonly fork: "asOf" | "current" | "initial" }
	| { readonly scope: "task" };
```

- `history: "rewindable"` is what makes `snapshotAsOf(token, conversationId, at, context)` work. With
  `"latest"` only the current value is retained.
- `fork` is product semantics: `"asOf"` gives a fork the value the parent had at the fork entry,
  `"current"` the value at fork time, `"initial"` the definition's initial value.
- `checkpointWhen` returns true to store the change as a full base instead of a delta; without it a
  long-lived document can accumulate deltas without bound.
- Family documents take a seed on first acquisition only. A seed is not identity and not an update.

Reads: `session.snapshot(...)`, `session.snapshotAsOf(...)`, `session.documentState(...)`,
`session.watchDoc(...)`, and the same four on `Harness` (which extends `Session`) plus the
invocation-bound `api`/`runtime` variants. Only a typed `tx.doc()` creates an absent document; every
read returns `undefined` for one that was never created.

Built-in documents, all readable through the view:

| Kind | Holds |
| ---- | ----- |
| `pi.agent` | the conversation's stored agent choices (exported as `AgentDoc`) |
| `pi.provider` | provider-facing session identity, forwarded to pi-ai as `sessionId` |
| `pi.live` | the running generation (partial answer, retry, deferred), tool slots, nested tools, compactions |
| `pi.inbox` | queued submissions |
| `pi.usage` | per-model and per-tool token and cost totals |

---

## 8. Entries

```ts
function defineEntry<D extends JsonValue = never>(kind: string): Entry<D>;
interface Entry<D extends JsonValue = never> { readonly kind: string; is(entry: EntryRecord | undefined): entry is TypedEntry<D>; }

const UserEntry: Entry;                    // "pi.user",            model: [UserMessage]
const AssistantEntry: Entry;               // "pi.assistant",       model: [AssistantMessage]
const SystemEntry: Entry;                  // "pi.system",          positional prompt/tool change
const ToolResultEntry: Entry<{ diagnostics: ToolDiagnostic[] }>;   // "pi.tool-result"
const ResetEntry: Entry;                   // "pi.reset",           head: "self", optional handoff
const CompactionEntry: Entry<{ reason: CompactionReason }>;        // "pi.compaction", head: first kept

type EntryRecord = {
	readonly id: EntryId;
	readonly conversationId: ConversationId;
	readonly kind: string;
	readonly model?: readonly Message[];       // what the model sees
	readonly data?: JsonValue;                 // what the application sees
	readonly head?: EntryId;                   // first entry of the active context
	readonly edits?: readonly ContextEdit[];   // context-only overrides of earlier entries
	readonly byTaskId?: TaskId;
};

type EntryDraft = Omit<EntryRecord, "id" | "conversationId" | "byTaskId" | "head"> & { readonly head?: EntryId | "self" };
type ContextEdit = { readonly target: EntryId } & (
	| { readonly action: "omit" }
	| { readonly action: "replace"; readonly messages: readonly Message[] });
```

Application entry kinds, document kinds, and task names must not start with `pi.`. Nothing enforces it,
and reusing a built-in name collides with harness behavior.

---

## 9. Extensions

```ts
function defineExtension<Tool extends ToolRegistration = ToolRegistration>(extension: Extension<Tool>): Extension<Tool>;

interface Extension<Tool extends ToolRegistration = ToolRegistration> {
	readonly name: string;
	readonly tools?: readonly Tool[];
	readonly sections?: readonly PromptSection<Tool>[];
	readonly hooks?: readonly HookRegistration[];
	readonly wraps?: readonly Wrap<Tool>[];
	readonly tasks?: readonly AnyTask[];
}

function section<Tool extends ToolRegistration = ToolRegistration>(
	key: string,
	render: PromptSection<Tool>["render"],
	options?: { readonly tag?: boolean },   // default true: rendered as <key>\n...\n</key>
): PromptSection<Tool>;

function wrapTool<Tool extends ToolRegistration>(tool: Tool, wrapper: (tool: Tool) => Tool): Wrap<Tool>;
function wrapSection<Tool extends ToolRegistration = ToolRegistration>(key: string, wrapper: (section: PromptSection<Tool>) => PromptSection<Tool>): Wrap<Tool>;

type PromptSection<Tool extends ToolRegistration = ToolRegistration> = {
	readonly key: string;
	render(input: PromptInput<Tool>, context: Context): string | undefined | Promise<string | undefined>;
	readonly tag?: boolean;
};

type PromptInput<Tool extends ToolRegistration = ToolRegistration> = {
	readonly conversationId: ConversationId;
	readonly agent: Agent<Tool>;
	readonly env: ExecutionEnv | undefined;
	readonly shown: Readonly<Record<string, string>>;   // sections already in effect after replay
	readonly read: DocumentReader;
};
```

Sections render in selection order before every request; the conversation's `instructions` render last
as the section `instructions`. Returning `undefined` omits a section and removes it from the prompt.
A section whose output changes without a real content change (a clock, a random value) appends a
`pi.system` delta every request and defeats provider prompt caching.

An extension's tasks are resolved by name from every installed extension, whichever conversations
select it; its tools, sections, hooks, and wraps apply only where the extension is selected.

---

## 10. Hooks

```ts
function hook<K extends AnyTask>(task: K, handlers: Partial<HooksOf<K>>): HookRegistration;
type HookRegistration = { readonly task: string; readonly handlers: object };
type HookResult<T> = T | undefined | Promise<T | undefined>;

interface HookApi extends DocumentReader {
	readonly taskId: TaskId;
	readonly conversationId: ConversationId;
	readonly models: Models;
	memo<T extends JsonValue>(name: string, context: Context): Promise<T | undefined>;
	memo<T extends JsonValue>(name: string, candidate: T, context: Context): Promise<T>;
}

interface ToolHooks {
	beforeTool(call: ToolHookCall, api: HookApi, context: Context): HookResult<{ readonly arguments?: JsonObject; readonly block?: string }>;
	afterTool(call: ToolHookCall, result: ToolExecutionResult, api: HookApi, context: Context): HookResult<ToolExecutionResult>;
}

type ToolHookCall = ToolCall & { readonly parent?: { readonly taskId: TaskId; readonly callId: string } };

interface GenerationHooks {
	beforeRequest(request: { readonly messages: readonly Message[] }, api: HookApi, context: Context): HookResult<{ readonly messages: readonly Message[] }>;
	afterResponse(message: AssistantMessage, api: HookApi, context: Context): void | Promise<void>;
	onYield(answer: AssistantMessage, api: HookApi, context: Context): HookResult<{ readonly continue: UserInput }>;
	afterTools(assistant: EntryId, results: readonly EntryId[], api: HookApi, context: Context): void | Promise<void>;
}

interface CompactionHooks {
	beforeCompact(
		compaction: { readonly reason: CompactionReason; readonly entries: readonly EntryRecord[]; readonly messages: readonly Message[];
			readonly firstKept: EntryId; readonly instructions?: string },
		api: HookApi, context: Context,
	): HookResult<{ readonly decline: true } | { readonly summary: string }>;
}
```

The first `block` wins; the first `beforeCompact` decision wins; the first `onYield` that returns
`{ continue }` appends the user message and continues the run. A throwing hook is reported through
`onReport` and skipped, and `beforeTool` blocks the call. Hooks share the asking task's memo namespace
with the task and with each other, so prefix memo names.

---

## 11. Tools

```ts
function defineTool<TParameters extends TSchema, TDetails extends JsonValue = JsonValue>(
	tool: ToolRegistration<TParameters, TDetails>,
): ToolRegistration<TParameters, TDetails>;

type ToolRegistration<TParameters extends TSchema = TSchema, TDetails extends JsonValue = JsonValue> = Tool<TParameters> & {
	readonly replay?: "safe" | "unsafe";              // default: "unsafe"
	readonly executionMode?: ToolExecutionMode;        // default: settings.toolExecution
	prepareArguments?(args: unknown): Static<TParameters>;
	readonly structuredOutputSchema?: TSchema;
	readonly callers?: readonly ("model" | "tools")[]; // default: both
	readonly deferred?: true;
	readonly outputLimits?: { readonly maxBytes?: number; readonly maxLines?: number; readonly retain?: "head" | "tail" };
	execute(args: Static<TParameters>, api: ToolExecutionApi<TDetails>, context: Context): Promise<ToolExecutionResult<TDetails>>;
};
```

`Tool` comes from pi-ai and carries `name`, `description`, `parameters` (a TypeBox schema), and optional
pi-ai fields such as `constrainedSampling`. The harness validates `args` against `parameters` before
`execute()`, so `prepareArguments()` must be pure, must not mutate, and its result is validated too.

```ts
type ToolExecutionResult<TDetails extends JsonValue = JsonValue> = {
	readonly output?: ToolResultMessage["content"];         // for the model; omitted: the retained running output
	readonly structuredOutput?: JsonValue;                  // for programs; validated against structuredOutputSchema
	readonly isError?: boolean;
	readonly details?: TDetails;                            // for UIs
	readonly diagnostics?: readonly ToolDiagnostic[];
	readonly usage?: Usage;                                 // added to pi.usage.tools
	readonly control?: ToolControl;
};

type ToolControl = { readonly addTools?: readonly string[]; readonly terminate?: true; readonly handoff?: string };
type ToolDiagnostic = { readonly severity: "info" | "warn" | "error"; readonly message: string; readonly code?: string };
```

Three channels: `output` is what the model reads, `structuredOutput` is what programs calling the tool
read, `details` is for the host UI. The transcript stores only `output` and `details`. A tool that
declares `structuredOutputSchema` must return a matching `structuredOutput`, also on an error result
that carries one; an `afterTool` hook that redacts `output` must redact `structuredOutput` too.

`control: { terminate: true }` ends the run without another model request when every result of the
round asks for it. `control: { handoff: "..." }` resets the context like `reset()`.

### Invocation API

```ts
interface ToolExecutionApi<TDetails extends JsonValue = JsonValue> extends DocumentObserver, DocumentReader {
	readonly taskId: TaskId;
	readonly conversationId: ConversationId;
	readonly callId: string;
	readonly registry: RegistrySnapshot;
	readonly models: Models;
	readonly env: ExecutionEnv | undefined;
	readonly outputWindow: ShellOutputWindow | undefined;

	agent(context: Context): Promise<Agent>;
	output(chunk: string | Uint8Array, skipped?: ShellOutputSkip): void;
	retainedOutput(): { readonly text: string; readonly truncated: boolean };
	diagnostic(diagnostic: ToolDiagnostic): void;
	details(value: TDetails, context: Context): Promise<void>;
	commit<T>(change: (tx: Tx) => T | Promise<T>, context: Context): Promise<T>;
	memo<T extends JsonValue>(name: string, context: Context): Promise<T | undefined>;
	memo<T extends JsonValue>(name: string, candidate: T, context: Context): Promise<T>;
	createTask<I, S extends { phase: string }, R, H extends object>(task: Task<I, S, R, H>, input: I, options: Omit<TaskOptions, "conversationId">, context: Context): Promise<TaskId<R>>;
	getTask<R>(id: TaskId<R>, context: Context): Promise<TaskRecord<JsonValue, JsonValue, R> | undefined>;
	waitForTask<R>(id: TaskId<R>, context: Context): Promise<SettledTask<R>>;
	conversation(id: ConversationId, context: Context): Promise<ConversationHandle | undefined>;
	executeTool(name: string, args: JsonObject, context: Context, options?: { readonly key?: string; readonly progress?: boolean }): Promise<NestedToolExecutionResult>;
}
```

A result that omits `output` uses the text accumulated through `api.output()`; a result that omits
`details` uses the last `api.details()` value.

### Nested calls

```ts
type NestedToolExecutionResult = {
	readonly taskId: TaskId;
	readonly structuredOutput?: JsonValue;
	readonly isError: boolean;
	readonly details?: JsonValue;
	readonly diagnostics: readonly ToolDiagnostic[];
	readonly usage?: Usage;
	readonly durationMs?: number;
};
```

A nested call is its own `pi.tool` task owned by the calling one, resolved among `agent.callable`,
validated, hooked (`call.parent` is set), and reported in `pi.live.nestedTools`. Its result returns to
the caller instead of entering the transcript, and its `usage` is already counted under its own tool.
The key is the call's position among the caller's nested calls unless `{ key }` is passed; a rerun of a
replay-safe caller that makes the same calls in the same order gets the calls it already made back.
Keys must be non-empty, free of `/`, not `__proto__`, and not a positive integer.

### Tool search

`createToolSearchExtension()` installs the `tool_search` tool, which searches `deferred: true` tools and
loads the matches with `control.addTools` (recorded in the conversation's `modelTools`). Loaded tools
stay offered on that branch, also after a compaction. `createToolSearchTool()`, `TOOL_SEARCH_TOOL_NAME`,
`DEFAULT_TOOL_SEARCH_LIMIT`, and `ToolSearchToolDetails` are exported alongside.

---

## 12. Code mode

```ts
type CodemodeToolOptions = {
	readonly sandbox: CodemodeSandboxBase;               // CodemodeSandbox | RemoteCodemodeSandbox
	readonly namespaces?: readonly CodemodeNamespace[];  // { name, description, prefix }
	readonly inlineBudget?: number;                      // tokens for the declarations in the section; default 3000
	readonly models?: boolean;                           // give scripts models.*; default true
	readonly globals?: readonly CodemodeGlobal[];        // host functions scripts call as globals
};

function createCodemodeExtension(options: CodemodeToolOptions): Extension;
function createCodemodeTool(options: CodemodeToolOptions): ToolRegistration;

const CODEMODE_TOOL_NAME: "codemode";
const CODEMODE_MODULE_VERSION: 2;
const DEFAULT_CODEMODE_INLINE_BUDGET: number;
```

The extension contributes the `codemode` tool (`callers: ["model"]`, `replay: "safe"`) plus a `codemode`
prompt section that lists the callable, non-deferred tools within the inline budget. Scripts call tools
as `tools.<name>(args)`; each call is a nested tool call. Global helpers: `searchTools()`,
`describeTool()`, `describeNamespace()`, `store(key, value)`, `load(key)`, and, unless `models: false`,
`models.*` (catalog, `models.classify()`, `models.generateImages()`). Scripts that declare no
`structuredOutputSchema` resolve with `undefined` on failure and reject with the error text when the
schema returned a value with the error, as `bash` does for a nonzero exit.

---

## 13. Coding tools (`/tools`)

```ts
function createCodingTools(options: ReadToolOptions = {}): Extension;   // name "coding-tools"
const CodingTools: Extension;                                          // createCodingTools() without an image processor

function createReadTool(options: ReadToolOptions = {}): ToolRegistration<typeof readSchema, ReadToolDetails>;
function createWriteTool(): ToolRegistration<typeof writeSchema>;
function createEditTool(): ToolRegistration<typeof editSchema>;
function createBashTool(options?: BashToolOptions): ToolRegistration<typeof bashSchema, ShellStructuredOutput>;
function createPowerShellTool(options?: PowerShellToolOptions): ToolRegistration<typeof powershellSchema, ShellStructuredOutput>;

type ReadToolOptions = { readonly images?: ImageProcessor };
type BashToolOptions = { readonly commandPrefix?: string; readonly prepare?: BashPrepare };
type BashExecution = { command: string; cwd: string; env: Record<string, string>; inheritEnv: boolean };
type BashPrepare = (execution: BashExecution, api: ToolExecutionApi, context: Context) => void | Promise<void>;
```

Tool arguments:

| Tool | Arguments | Structured output |
| ---- | --------- | ----------------- |
| `read` | `path`, `offset?` (1-indexed line), `limit?` (lines) | none; one image file becomes an `ImageContent` |
| `write` | `path`, `content` | none |
| `edit` | `path`, `edits: [{ oldText, newText }]` | none |
| `bash` | `command`, `timeout?` (seconds) | `{ output, truncated, fullOutputPath?, exitCode }` |
| `powershell` | `command`, `timeout?` | same as `bash` |

`bash` keeps a tail of the output (the model sees the retained text, programs read `output` and
`exitCode`), spills the complete output to a temporary file past its thresholds, and answers a nonzero
exit code with an error result that still carries the structured output. All tools reach files and
processes only through the call's environment, so without `HarnessOptions.env` they fail with an error
result.

Image processing: `read` sends PNG, JPEG, GIF, and WebP files within the model's
`inputLimits.images.resize` (2000x2000 by default, 4.5 MB base64) as they are, without decoding, reading
dimensions from the header. With an `ImageProcessor` it decodes every image, applies EXIF orientation,
converts BMP to PNG, and shrinks to fit.

```ts
function createPhotonImages(wasm: SyncInitInput): ImageProcessor;                     // /images
function createNodePhotonImages(options?: NodePhotonImagesOptions): Promise<ImageProcessor>;   // /images/node, worker thread
function createCloudflarePhotonImages(): ImageProcessor;                              // /images/cloudflare

type NodePhotonImagesOptions = { readonly worker?: boolean; readonly idleMs?: number };   // default true, 30_000
type ImageProcessor = { prepare(bytes: Uint8Array, mimeType: string, limits: ImageLimits): Promise<PreparedImage | undefined> };
type ImageLimits = { readonly maxWidth: number; readonly maxHeight: number; readonly maxBytes: number };
const DEFAULT_IMAGE_LIMITS: ImageLimits;
```

---

## 14. Tasks

```ts
function defineTask<I, S extends { phase: string }, R, H extends object = object>(definition: TaskDefinition<I, S, R, H>): Task<I, S, R, H>;

type TaskDefinition<I, S extends { phase: string }, R, H extends object> = {
	readonly name: string;
	readonly version: number;
	initial(input: I): S;
	readonly phases: { readonly [P in S["phase"]]: PhaseHandler<I, Extract<S, { phase: P }>, S, R, H> };
	abort(task: RunningTask<I, S, R>, runtime: TaskRuntime<I, S, R, H>, context: Context): Promise<void>;
	migrate?(input: JsonValue, checkpoint: JsonValue, fromVersion: number): { input: I; checkpoint: S };
	readonly hooks?: H;
};

type PhaseHandler<I, P, S, R, H extends object> =
	(task: RunningTask<I, P, R>, runtime: TaskRuntime<I, S, R, H>, context: Context) => Promise<void>;

type NextTaskState<S, R> = Extract<TaskState<S, R>, { readonly status: "running" | "waiting" | "terminal" }>;

interface TaskRuntime<I, S, R, H extends object> extends DocumentObserver, DocumentReader {
	readonly taskId: TaskId<R>;
	readonly conversationId: ConversationId;
	readonly signal: AbortSignal;
	readonly registry: RegistrySnapshot;
	readonly settings: Settings;
	readonly models: Models;
	readonly hooks: HookRunner<H>;

	agent(context: Context): Promise<Agent>;
	env(context: Context): Promise<ExecutionEnv | undefined>;
	commit(change: (tx: Tx, current: RunningTask<I, S, R>) => NextTaskState<S, R> | undefined | Promise<NextTaskState<S, R> | undefined>, context: Context): Promise<void>;
	memo<T extends JsonValue>(name: string, context: Context): Promise<T | undefined>;
	memo<T extends JsonValue>(name: string, candidate: T, context: Context): Promise<T>;
	getTask<T>(id: TaskId<T>, context: Context): Promise<TaskRecord<JsonValue, JsonValue, T> | undefined>;
	waitForTask<T>(id: TaskId<T>, context: Context): Promise<SettledTask<T>>;
	abortOwned(id: TaskId, context: Context): Promise<void>;
	ownedTasks(context: Context): Promise<TaskRecord<JsonValue, JsonValue, JsonValue>[]>;
	outcomes<T>(ids: readonly TaskId<T>[], context: Context): Promise<TaskOutcome<T>[]>;
	conversation(id: ConversationId, context: Context): Promise<ConversationHandle | undefined>;
	entry(id: EntryId, context: Context): Promise<EntryRecord | undefined>;
	context(conversationId: ConversationId, context: Context, options?: { readonly at?: EntryId }): Promise<ContextView>;
	now(): number;
	report(error: unknown): void;
	sleep(until: number, context: Context): Promise<void>;
}

type TaskOptions = {
	readonly ownership: TaskOwnership;                 // required: { kind: "conversation" } | { kind: "task"; taskId }
	readonly conversationId?: ConversationId;
	readonly background?: boolean;
	readonly abandonOnRestart?: boolean;
};

type JoinPolicy = "failFast" | "allSettled";
type TaskState<S, R> =
	| { readonly status: "pending"; readonly checkpoint: S }
	| { readonly status: "running"; readonly checkpoint: S }
	| { readonly status: "waiting"; readonly checkpoint: S; readonly on: readonly TaskId[]; readonly policy: JoinPolicy }
	| { readonly status: "completing"; readonly outcome: TaskOutcome<R> }
	| { readonly status: "terminal"; readonly outcome: TaskOutcome<R> };

type TaskOutcome<R> =
	| { readonly status: "completed"; readonly result: R }
	| { readonly status: "failed"; readonly error: TaskOutcomeError; readonly result?: R }
	| { readonly status: "aborted"; readonly reason?: string; readonly result?: R }
	| { readonly status: "orphaned"; readonly reason: string }
	| { readonly status: "faulted"; readonly error: TaskOutcomeError };

type TaskOutcomeError = { readonly message: string; readonly detail?: JsonValue };
type SettledTask<R> = TaskRecord<JsonValue, JsonValue, R> & { readonly state: Extract<TaskState<JsonValue, R>, { readonly status: "terminal" }> };
```

`RunningTask` is `TaskRecord` with `state.status === "running"`, and `runtime.commit()` receives the
current record. `TaskRecord` carries `id`, `conversationId`, `kind`, `version`, `input`, `owner?`,
`background`, `abortRequested`, `abortReason?: "restart"`, `abandonOnRestart?`, `startedAt?`,
`endedAt?`, `memos?`, and `state`.

### Built-in tasks

| Export | Name | Role |
| ------ | ---- | ---- |
| `GenerationTask` | `pi.generation` | prepares the request, calls the model, appends the answer, owns the round's `pi.tool` tasks |
| `ToolTask` | `pi.tool` | one tool call, model-issued or nested |
| `CompactionTask` | `pi.compaction` | one summarization |

Their input, checkpoint, and result types (`GenerationInput`, `GenerationCheckpoint`, `GenerationResult`,
`ToolTaskInput`, `ToolTaskCheckpoint`, `ToolTaskResult`, `CompactionInput`, `CompactionCheckpoint`,
`SummaryRequest`) are exported. Their hook maps are `GenerationHooks`, `ToolHooks`, and `CompactionHooks`

---

## 15. Environment

```ts
interface ExecutionEnv extends FileSystem, Shell {}

interface Shell {
	exec(command: string | readonly string[], options: ShellExecOptions | undefined, context: Context): Promise<Result<ShellExecResult, ExecutionError>>;
	cleanup(context: Context): Promise<void>;
}

type ShellExecOptions = {
	cwd?: string; env?: Record<string, string>; inheritEnv?: boolean; timeout?: number;
	onOutput?: (text: string, context: Context, info: ShellOutputInfo) => void;
	spill?: ShellSpillOptions;
	window?: ShellOutputWindow;
};
type ShellExecResult = { exitCode: number; spillPath?: string };
type ShellOutputInfo = { stream: "stdout" | "stderr"; skipped?: ShellOutputSkip };
type ShellOutputSkip = { bytes: number; newlines: number; endsWithNewline: boolean };
type ShellOutputWindow = { maxBytes: number; maxLines: number; minIntervalMs: number; bytesPerSecond: number };

interface FileSystem {
	readonly id: string;             // equal ids see the same files at the same paths
	cwd: string;
	absolutePath(path: string, context: Context): Promise<Result<string, FileError>>;
	joinPath(parts: string[], context: Context): Promise<Result<string, FileError>>;
	readTextFile(path: string, context: Context): Promise<Result<string, FileError>>;
	openTextLineReader(path: string, context: Context): Promise<Result<TextLineReader, FileError>>;
	readTextLines(path: string, options: { maxLines?: number } | undefined, context: Context): Promise<Result<string[], FileError>>;
	readBinaryFile(path: string, context: Context): Promise<Result<Uint8Array, FileError>>;
	openBinaryReader(path: string, options: { noFollow?: boolean } | undefined, context: Context): Promise<Result<BinaryReader, FileError>>;
	writeFile(path: string, content: string | Uint8Array, context: Context): Promise<Result<void, FileError>>;
	appendFile(path: string, content: string | Uint8Array, context: Context): Promise<Result<void, FileError>>;
	truncateFile(path: string, size: number, context: Context): Promise<Result<void, FileError>>;
	flushFile(path: string, context: Context): Promise<Result<void, FileError>>;
	renameFile(sourcePath: string, destinationPath: string, context: Context): Promise<Result<void, FileError>>;
	fileInfo(path: string, context: Context): Promise<Result<FileInfo, FileError>>;
	listDir(path: string, context: Context): Promise<Result<FileInfo[], FileError>>;
	listFiles?(path: string, options: ListFilesOptions | undefined, context: Context): Promise<Result<FileListing, FileError>>;
	openDirReader(path: string, context: Context): Promise<Result<DirReader, FileError>>;
	watch(targets: readonly WatchTarget[], onChange: (change: WatchChange) => void, context: Context): Promise<Result<FileWatcher, FileError>>;
	canonicalPath(path: string, context: Context): Promise<Result<string, FileError>>;
	exists(path: string, context: Context): Promise<Result<boolean, FileError>>;
	createDir(path: string, options: { recursive?: boolean } | undefined, context: Context): Promise<Result<void, FileError>>;
	remove(path: string, options: { recursive?: boolean; force?: boolean } | undefined, context: Context): Promise<Result<void, FileError>>;
	createTempDir(prefix: string | undefined, context: Context): Promise<Result<string, FileError>>;
	createTempFile(options: { prefix?: string; suffix?: string } | undefined, context: Context): Promise<Result<string, FileError>>;
	cleanup(context: Context): Promise<void>;
}

type Result<TValue, TError> = { ok: true; value: TValue } | { ok: false; error: TError };
type FileErrorCode = "aborted" | "not_found" | "permission_denied" | "not_directory" | "is_directory" | "invalid" | "not_supported" | "unknown";
type ExecutionErrorCode = "aborted" | "timeout" | "shell_unavailable" | "spawn_error" | "callback_error" | "unknown";
class FileError extends Error { code: FileErrorCode; path?: string }
class ExecutionError extends Error { code: ExecutionErrorCode; spillPath?: string }

class NodeExecutionEnv implements ExecutionEnv {
	readonly id: "node:local";
	cwd: string;
	constructor(options: { cwd: string; shellPath?: string; shellEnv?: NodeJS.ProcessEnv; watch?: NodeWatchOptions });
}
```

File operations return `Result` instead of throwing; `Shell.exec` also returns a `Result`, with the
process's exit code inside the value. `exec()` with an argv array runs a program without a shell.
`cleanup()` is for shutting the environment down, never for one request. `listFiles()` is optional:
callers fall back to their own walk when it is missing or fails with `not_supported`.

---

## 16. Storage

| Backend | Constructor |
| ------- | ----------- |
| Memory | `new MemoryStorage()` |
| SQLite (Node) | `await openNodeSqliteStorage(path, { walAutoCheckpointPages?, busyTimeoutMs? })` |
| SQLite (Bun/other) | `await SqliteStorage.open(database: SqliteDatabase)` |
| SQLite (Durable Object) | `await openDurableObjectSqliteStorage(ctx.storage)` |
| JSONL (Node) | `await openNodeJsonlStorage(directory, context, { fsync?: boolean })` |
| JSONL (portable) | `await JsonlStorage.open(directory, fileSystem, context, options)` |

A SQLite adapter implements the promise-based facade:

```ts
interface SqliteDatabase {                   // extends SqliteExecutor
	exec(sql: string): Promise<void>;
	run(sql: string, ...params: SqliteValue[]): Promise<void>;
	get<T extends object>(sql: string, ...params: SqliteValue[]): Promise<T | undefined>;
	all<T extends object>(sql: string, ...params: SqliteValue[]): Promise<T[]>;
	transaction<T>(callback: (transaction: SqliteExecutor) => Promise<T>): Promise<T>;
	close(): Promise<void>;
}
type SqliteValue = null | number | bigint | string | Uint8Array;
```

All work inside a transaction must use the transaction handle, which expires when the callback settles;
adapters queue unrelated operations until the transaction finishes, so calling the database itself
inside the callback never settles.

`Storage` is the interface a custom backend implements: `commit(writes, context): Promise<Seq>`,
`mintId()`, `conversation()`, `scanConversations()`, `entry()`, `findLatestHeadMarker()`,
`scanEntries()`, `task()`, `scanTasks()`, `submission()`, `scanSubmissions()`, `submissionByRequest()`,
`findDocument()`, `document()`, `scanDocuments()`, and `close()`. Two error classes are meaningful
there: `StorageRequestError` for an invalid request, which must have no durable effect, and any other
error, which is fatal. One process owns a storage at a time; there is no cross-process locking.

---

## 17. Testing (`/testing`)

```ts
function registerStorageConformance(runner: StorageConformanceRunner, name: string, withStorage: StorageConformanceProvider): void;
function registerEnvConformance(runner: StorageConformanceRunner, name: string, withEnv: EnvConformanceProvider,
	options?: Pick<EnvConformanceOptions, "shell" | "symlinks" | "listFiles">): void;
function createStorageConformance(options: StorageConformanceOptions): StorageConformanceCase[];
function createEnvConformance(options: EnvConformanceOptions): EnvConformanceCase[];
function createExpectAssertions(expect: ExpectLike): StorageConformanceAssertions;

type StorageConformanceRunner = {
	describe(name: string, body: () => void): void;
	it(name: string, run: () => Promise<void>, timeoutMs?: number): void;
	expect: ExpectLike;
};
```

Usage with a Vitest- or Jest-compatible runner:

```ts
registerStorageConformance({ describe, expect, it }, "My Storage", async (use) => {
	const storage = await openMyStorage();
	try { await use(storage); } finally { await closeMyStorage(storage); }
});
```

Benchmark support: `STORAGE_MEMORY_SCALES`, `STORAGE_READ_BENCHMARKS`, `STORAGE_WRITE_BENCHMARKS`,
`seedStorageBenchmark()`, `seedStorageWriteBenchmark()`, `storageBenchmarkPrimaryRecordCount()`,
`TIMING_SCALE`, and their types.

---

## 18. Observation

```ts
// structural view of one conversation, updated after every commit that touches it
const view: AttachedReplicatedState<ConversationView> = await conversation.viewState(context);
view.subscribe((value) => render(value));
view.dispose();

// the same value with the exact Chord operations of each commit
const watch: ConversationWatch = await conversation.watch(context);
render(watch.value);                                  // the state at attachment
watch.start(async (value, ops, context) => { await send(ops); });
await watch.stop();                                   // WatchEnd
await watch.closed;

// coding-agent style events instead of structural state
const stream: AgentEventStream = await watchEvents(harness, conversationId, context);
initialize(stream.snapshot);
stream.start(async (events) => { for (const event of events) console.log(event); });

// live tasks of the session, for a task panel
const graph = await harness.taskGraph(context);
graph.subscribe((value) => { for (const node of Object.values(value.tasks)) … });
const graphWatch: TaskGraphWatch = await harness.watchTaskGraph(context);

// totals
const usage: UsageState = await harness.usage(context);
```

```ts
interface WatchHandle<T> {
	readonly value: T;                       // before start(): the immutable acquisition revision
	start(listener: (value: T, ops: readonly Op[], context: Context) => Promise<void>): void;
	stop(): Promise<WatchEnd>;
	readonly closed: Promise<WatchEnd>;
}
type WatchEnd =
	| { readonly reason: "stopped" | "cancelled" | "session_closed" | "retired" }
	| { readonly reason: "listener_error"; readonly error: Error }
	| { readonly reason: "session_failed"; readonly error: unknown };
type DocumentWatch<T extends JsonObject> = WatchHandle<Readonly<T> | null>;
type DocumentState<T extends JsonObject> = AttachedReplicatedState<Readonly<T> | null>;
```

`ConversationView` carries `entries`, `docs["pi.live"]`, `docs["pi.inbox"]`, `docs["pi.usage"]`,
`docs["pi.agent"]`, `docs["pi.provider"]`, and the conversation's `ConversationRecord`. The state value
is a view of what was committed, not of what the application last wrote, so a view is exact only up to
the newest commit.

`HarnessInspection` is the read-only snapshot for operators:

```ts
type HarnessInspection = {
	readonly scheduling: "paused" | "running" | "closing";
	readonly tasks: readonly TaskInspection[];
	readonly submissions: readonly SubmissionRecord[];
};
type TaskInspection = { readonly record: TaskRecord<JsonValue, JsonValue, JsonValue>;
	readonly state: { kind: "running" } | { kind: "ready"; migrates: boolean } | { kind: "waiting"; on: readonly TaskId[] }
		| { kind: "completing" } | { kind: "blocked"; reason: "missing_task" | "task_too_old" | "migration_failed"; error?: unknown } };
```

---

## 19. Errors

```ts
class ConversationBusy extends Error {}      // submit({ whenBusy: "reject" }) on a busy conversation
class ReadAfterWrite extends Error {}        // a table read after a table write in one commit
class SessionFailed extends Error {}         // every later call and pending wait after a storage failure
class StorageRequestError extends Error {}   // one invalid storage request; no durable effect
```

Three rules decide what an error does:

1. A **storage error ends the harness**. The failing call rejects, every later call and pending wait
   rejects with `SessionFailed` (whose `cause` is the original error), watches and event streams end
   with `session_failed`, running tasks receive their abort signal, `onReport` gets the error once, and
   the harness closes itself. Nothing is retried; a custom storage retries its own transient failures.
   Reopen to recover, and resubmit with the same `requestId`.
2. An **invalid request fails only that call** (`StorageRequestError`), as does a cancelled read.
3. **Your code fails only its own unit**: a throwing task phase faults that task, a throwing tool gets
   an error result, a throwing hook is reported and skipped, and a throwing commit callback rolls back
   that commit. The exception is a host `RegistryReader` whose `snapshot()` throws: the harness cannot
   schedule without it, so it fails.

`harness.closed` settles once the harness has closed, by `close()` or after a failure:
`{ reason: "failed", error }` is the signal for a host to reopen.
