# Pi Durable: Runtime Semantics

How the harness executes work, what survives a crash, and which rule decides each case. Read
`durable-api.md` for names and `durable-spec.md` for the normative text; the section numbers in
parentheses are that spec's.

## 1. The one rule behind everything

> A Session atomically commits immutable entries, full task records, and Chord-tracked documents.
> Only committed state is observable.

Consequences you can rely on:

- Nothing is shown before its commit is stored. A streamed partial is shown because it was committed,
  so a watch never sees a state the storage can lose.
- Every write goes through one commit line. There is one ordering for the whole session, not one per
  conversation.
- Values are written in one commit or not at all: entries, documents, and task records move together.
- Reopening storage continues from the newest commit. Anything after it did not happen.

Crash windows are therefore real but bounded: a partial answer, tool output, or commit that had not
been written yet is lost, and the task that wrote it resumes from its last checkpoint.

## 2. The commit line

`Session.commit(callback)` runs the callback while holding the mutation line (§4). Rules:

| Rule | Why |
| ---- | --- |
| Read every table row you need **before** the first table write in the callback | a table read after a table write throws `ReadAfterWrite` |
| Read only through `tx` inside the callback | `snapshot()`, `documentState()`, `watchDoc()`, `getTask()`, and any other session or runtime read may queue on the line the callback holds, and then never resolve |
| Never await a model, tool, process, network call, human, nested commit, or session waiter inside the callback | the callback holds the line; a long one blocks the whole session |
| Draft work does not outlive the callback | draft reads, draft writes, and every `Tx` operation reject once the callback settles |
| A throwing callback rolls back that commit | your code fails only its own unit |

Document drafts from `tx.doc()` stay usable after a table write; table reads do not. Document mutation
ownership (§3.4) follows from the same line: the newest committed value wins, and a draft is written as
the diff from the value it read.

## 3. One input, end to end

```text
submit(input) ──▶ pi.user entry, submission "placed"
  pi.generation task
     ├─ prepare: build the system prompt from the agent's sections (only what changed),
     │           estimate tokens, compact if past a threshold, prepare the request
     ├─ call the model (streamed partials committed at the progress interval)
     ├─ append pi.assistant
     └─ for each tool call: create a pi.tool task it owns, then wait for the round
          pi.tool task ──▶ validated args, beforeTool hooks, execute(), afterTool hooks,
                           pi.tool-result entry
     └─ next generation appends the answer ──▶ submission "done"
```

Details that decide behavior:

- **A turn is one model response and its tool calls; a run is the turns from an input to its final
  answer.** A conversation is busy while a run is working.
- **Tool rounds** run in parallel by default, or sequentially when `settings.toolExecution` or the
  tool's `executionMode` says so; one sequential call makes its whole round sequential (§8.5).
- **A tool may end a run** with `control: { terminate: true }` when every result of the round asks for
  it, or with `control: { handoff: "..." }`, which resets the context with that handoff text.
- **Generation retries** its provider attempts by the settings' retry policy, and retries once after
  compacting when a provider rejects the request as too long (§8.3).
- **A generation that a failed blocking compaction stopped** fails without sending a request: its
  inputs settle `unanswered` with `model_error` and detail `Compaction failed: <error>`. A compaction
  that found nothing to compact or was declined lets the request go ahead.
- **A faulted generation** still keeps what the model produced: a committed partial becomes an aborted
  `pi.assistant` entry, and its spend is counted.

## 4. Task execution and checkpoints

A task is a durable state machine with named phases and a checkpoint committed after every step (§5.1).
The usual shape is **save what you are about to do, do it, save the result**:

```ts
phases: {
	charge: async (task, runtime, context) => {
		const key = task.state.checkpoint.key;                  // durable intent, committed earlier
		const receipt = await payments.charge(key, task.input.amount);   // the effect
		await runtime.commit(() => ({ status: "terminal", outcome: { status: "completed", result: { receipt } } }), context);
	},
}
```

- A phase handler **must** commit a changed checkpoint, a wait, or an outcome through
  `runtime.commit()`. Returning without durable progress faults the task.
- A crash between the effect and the commit reruns that step, so a step must be safe to repeat:
  idempotency keys, first-writer-wins memos (`runtime.memo(name, candidate)`), or a check-then-act
  under the commit line.
- `runtime.memo()` is a small first-writer-wins value kept while the task can run. It is the cheap way
  to make a rerun see the decision the first attempt made.
- `task.version` plus `migrate(input, checkpoint, fromVersion)` is how a stored task is carried into a
  new definition shape; a version gap without `migrate` blocks the task (§5.4).

## 5. The ownership tree

Everything is one tree. Every task names its owner at creation, and every conversation is ownerless or
owned by a task. Owner edges are immutable (§5.5).

```text
conversation (ownerless)
└─ task: generation              (conversation-owned, non-background)
   ├─ task: tool call            (child of the generation)
   │  └─ task: nested tool call  (child of that tool call)
   └─ conversation (owned by the generation)      ← a subagent
      └─ task: generation
```

**Ordinary owned work** of a task is every task reached below it: the tasks it owns, the tasks in the
conversations it owns, and so on transitively, excluding background tasks and everything below them.
Two rules follow:

- **Abort flows down.** A live owner's cancellation intent (its abort mark, or a held non-`completed`
  outcome) marks its ordinary owned work in a later reconcile commit, and again at open, so a crash in
  between loses nothing. Abort marks from a request replace a `restart` mark; an owner's own
  `runtime.abortOwned()` keeps it.
- **Owned work does not outlive its owner's finish.** A terminal state committed while ordinary owned
  work is live is stored as `completing`; the record becomes `terminal` in a later commit, once that
  work is done. A held `completed` outcome waits for the work to finish normally; any other held outcome
  is cancellation intent and aborts the work below first. The terminal state, task-document retirement,
  and task waiters are deferred to that final commit; everything else the finishing commit wrote lands
  at the hold.

A **background** task is a boundary: ordinary traversal skips it and its whole subtree. Use it for work
that must survive the parent's Esc, such as a persistent subagent. `Conversation.abort(context,
{ background: true })` crosses that boundary.

**Waiting** commits `{ status: "waiting", checkpoint, on, policy }`. The task runs no code until every
task in `on` is terminal. `on` may name other tasks, including terminal ones; a task the waiting task
does not own requires `policy: "allSettled"`. Cycles in the wait-for graph are rejected. With
`failFast`, the first task in `on` that ends with a non-`completed` outcome gives the others an abort
mark; the waiting task itself is not marked and reads the outcomes with `runtime.outcomes()`.

**Abort runs bottom-up.** A task's abort handler starts only once its ordinary owned work is no longer
live, so the handler sees final outcomes below it. An abort handler cannot create owned children
because its task is abort-marked: it compensates inline, or creates background conversation-owned tasks
and waits with `runtime.waitForTask()`.

## 6. Recovery

What a restart does, by case:

| State at the crash | After reopen |
| ------------------ | ------------ |
| task `running` | shown as `pending` until scheduled again, then resumes at its checkpoint |
| tool call interrupted, `replay: "safe"` | reruns; a rerun of a replay-safe tool that calls nested tools in the same order, or with the same keys, reattaches to the nested calls it already made |
| tool call interrupted, `replay: "unsafe"` (default) | the model gets an `interrupted` error result carrying the output committed so far |
| task with `abandonOnRestart: true` | the first reservation pass sets an abort mark with `abortReason: "restart"`; its abort handler runs and cleans up |
| task whose definition is missing or too old | stays pending, blocked (`missing_task`, `task_too_old`, `migration_failed`); it still blocks idle waits and is reconsidered whenever the registry changes |
| abort requested but not run | the abort invocation runs on reopen |
| code-mode script | reruns and is handed its journaled tool results in order, so it makes the same calls; a rerun that takes another path, or whose sandbox fingerprint changed, ends with an error |
| `close()` instead of a crash | every invocation stops without writing an outcome, so the work resumes on reopen |

Nothing is retried that failed durably. A blocked task is never terminalized by the harness, so an
abort of one settles it `orphaned` (no task code ran, external effects may remain) rather than
`aborted` (its own handler decided). `harness.inspect()` reports blocked tasks, and `harness.resume()`
starts scheduling; opening alone marks nothing.

## 7. Compaction

Compaction replaces an old prefix of the model context with a `pi.compaction` summary entry whose `head`
is the first kept entry. Raw history stays in storage (§8.7).

Three ways to start one; the task is the same, only ownership and placement differ:

| Started by | Owner | Background | Generation waits | Placement |
| ---------- | ----- | ---------- | ---------------- | --------- |
| `Conversation.compact(instructions)` | the conversation | no | no | write submission |
| generation above the background threshold | the conversation | yes | no | write submission |
| generation above the blocking threshold, or after a context overflow | the generation | no | yes | direct append |

Which one is available comes from `settings.compaction`: `enabled`, `reserveTokens` (generation blocks
above `contextWindow - reserveTokens`), `keepRecentTokens` (how much recent context stays verbatim),
and `backgroundTokens` (how far below the blocking threshold a background compaction starts; `0`
disables it). Manual `compact()` ignores `enabled`.

Range selection (§8.7) keeps `keepRecentTokens` of the newest contributions verbatim, cuts only at a
non-marker entry whose contribution begins with a user or assistant message, and keeps the tool results
that belong to a kept assistant message. Nothing is compacted while the context is smaller than
`keepRecentTokens`, so a small window can overflow before any threshold compaction.

A `beforeCompact` hook may decline or supply the summary; the first decision wins. Failures are recorded
in `docs["pi.live"].compactionFailure` until a compaction produces a summary, and running compactions
appear in `docs["pi.live"].compactions` with reason, attempt, and retry backoff. Every attempt pays for
a summarization request, including one that ends stale because a later compaction cut further.

## 8. Submissions and the inbox

A conversation places queued items at boundaries. The boundary behavior is what decides ordering (§6):

- **Steer** (`whenBusy: "steer"`) is placed after the current tool round and joins the running work.
- **Follow-up** (`whenBusy: "followUp"`, the default) is placed when the run answers and starts the
  next run.
- **Reject** (`whenBusy: "reject"`) throws `ConversationBusy`.
- **Write** of only `kind` and `data` touches nothing the model sees, is appended at once even
  mid-run, and is never queued. A write with `model`, `head`, or `edits` waits for the next boundary
  like a steer.

Failure does not clear the inbox: after a failed run, queued items stay in `pi.inbox` and their
`wait()` does not settle until an input or a queued write's boundary places them. A display-only write
runs no boundary. A finished compaction's write submission is a boundary, so a manual or background
compaction in an idle conversation can place waiting follow-ups and start a run.

`Submission.abort()` withdraws a queued submission. A queued write is kept by a conversation abort;
`Submission.abort()` still withdraws it. Resubmitting with the same `requestId` returns the existing
submission, which is how a recovered task sends a message or a report exactly once.

## 9. Live state, observation, and cadence

- `docs["pi.live"]` holds the running generation (streamed partial, retry, deferred), the tool slots
  with their output and details, the nested calls of a running tool, and compaction status.
- Running partials and tool output are committed at most every `settings.progress.partialIntervalMs` /
  `outputIntervalMs` (100 ms by default). A remote storage can commit less often, in exchange for
  larger steps and a larger crash window.
- `viewState()` and `watch()` give the structural view; `watchEvents()` derives coding-agent style
  events from the same commits, one batch per commit, with deltas for text, thinking, tool arguments,
  and tool output. A consumer more than 100 batches behind receives a fresh snapshot instead of a
  delta. A slow watch keeps at most 100 undelivered frames; beyond that the pending frames collapse
  into one full-value replacement.
- `settings.contextRetentionMs` bounds how long an idle conversation keeps its context read in memory;
  busier conversations always keep it. `settings.documentRetentionMs` bounds how long an unobserved
  document stays in memory. Both are memory knobs only; the durable copy is unaffected.
- `harness.usage()` sums every conversation's `pi.usage`; a tool result's `usage` is counted under
  that tool, and a child conversation's spend is already counted, so forwarding it double-counts it.

## 10. Failure model

1. **A storage error ends the harness.** The failing call rejects; everything after it and every
   pending wait rejects with `SessionFailed`; watches and streams end with `session_failed`; running
   tasks get their abort signal; `onReport` receives the error once; the harness closes itself. Nothing
   is retried: a custom storage retries its own transient failures. Reopen to recover; commits are
   atomic, so the store is consistent.
2. **An invalid request fails only that call**, with `StorageRequestError`, and has no durable effect.
   A cancelled read fails only itself.
3. **Your code fails only its own unit**: a throwing task phase faults that task, a throwing tool gets
   an error result, a throwing hook is reported and skipped (a throwing `beforeTool` blocks the call),
   a throwing commit callback rolls back, a throwing listener is reported while the others still run.
   The exception is a host `RegistryReader` whose `snapshot()` throws: the harness cannot schedule
   without it, so it fails like a storage error.

`harness.closed` settles with the end reason, so a host restarts on failure:

```ts
harness.closed.then((end) => { if (end.reason === "failed") reopen(end.error); });
```

Closing waits for running task code to return, so a handler, tool, or hook that ignores its abort
signal keeps `close()` and the storage open. Chord objects that expose harness state must be disposed
before `close()`: a state ended by close keeps its last value and never updates again.

## 11. Knobs that change behavior, not implementation

| Setting | Effect |
| ------- | ------ |
| `toolExecution: "sequential"` | tool rounds run one call at a time, in call order |
| `steeringMode` / `followUpMode: "all"` | every queued item of that mode is placed at once instead of one per turn |
| `progress.partialIntervalMs` / `outputIntervalMs` | crash window versus commit count |
| `compaction.*` | when the context is compacted, and how much stays verbatim |
| `retry.*` | provider attempt retries inside one generation attempt, and inside a summarization attempt |
| `stream.timeoutMs`, `stream.headers`, `stream.metadata` | the provider request itself |
| `contextRetentionMs` / `documentRetentionMs` | memory only |
| `settings.extensions` | which extensions a conversation on the default selection runs |

Tool-side limits: `outputLimits: { maxBytes, maxLines, retain }` bounds what the model sees and what is
retained in memory; the spilled full output stays in a file. `code mode` scripts have their own
`max_output_tokens` and the sandbox's `memoryLimitBytes`.

## 12. What is deliberately absent

The package has no whole-session DOM, no visible-but-undurable publication, no automatic checkpoint
heuristic, no automatic third-party view mounting, no CRDT or offline multi-writer merge, no SQL
translation of Chord operations, no JSONL compaction or corruption repair, no compatibility layer for
earlier prototypes, and no forced termination of non-cooperative extension code in one process (§13).

Two naming rules come with that: document kinds and task names are persisted protocol, so a value
migration cannot rename a kind (copy and retire instead), and names starting with `pi.` belong to the
built-ins, though nothing enforces it.
