# Chord: Typed Host Runtime
Source: `packages/chord/README.md`, `docs/guide.md`, `docs/spec.md`, `docs/tutorial.md`, `src/delta/README.md`
Not a Pi package: `@earendil-works/chord` is an application-neutral runtime that no Pi workspace package depends on, and it is not covered by the Pi user docs. Release 1.2.0 replaced the facet and service runtime with a typed host runtime (contracts, hosts, links, hot reload) and removed `PLANNING.md`, the `./bundler` export, and the `pi-client`/`pi-protocol`/`pi-server` packages. The specification and the guide describe the current runtime; the tutorial is a worked example.

---

> **Auto-built from individual doc pages.**
> Sources: https://raw.githubusercontent.com/earendil-works/pi/main/packages/chord/README.md, https://raw.githubusercontent.com/earendil-works/pi/main/packages/chord/docs/guide.md, https://raw.githubusercontent.com/earendil-works/pi/main/packages/chord/docs/spec.md, https://raw.githubusercontent.com/earendil-works/pi/main/packages/chord/docs/tutorial.md, https://raw.githubusercontent.com/earendil-works/pi/main/packages/chord/src/delta/README.md

## Overview

Chord builds applications out of **objects** that live in several processes (a server, workers, browser tabs) and can be **hot reloaded** while they run.

- An **object** is state plus code at an address. It is created on demand and lives while someone holds it.
- Everyone gets a **handle**, never the object. Handles work the same locally and across processes, and survive reloads.
- Every object knows its **principal**: an owner and a guest get different objects, with different methods.
- **State** is observable JSON. Remote viewers get a snapshot followed by deltas.
- **Hot reload** swaps code while it runs. Work in flight finishes on the code it started with, state is kept, and incompatible changes migrate at a safe point.

Contracts are runtime values described with [TypeBox](https://github.com/sinclairzx81/typebox) schemas. Hosts exchange JSON frames over links: in memory, a Node IPC channel, or a WebSocket.

## Entry points

| Import | Contents | Runs in |
|--------|----------|---------|
| `@earendil-works/chord` | Contracts (`local`, `remote`, `method`, `opaque`), declarations (`cell`, `derivation`, `listener`, `resource`), hosts (`createHost`, `defineFacet`, `defineRegistry`), links (`memoryLinkPair`, `ipcLink`, `webSocketLink`, `acceptWebSockets`), errors (`ChordError`, `isChordError`, `forbidden`, `invalid`). Also the shared base: `Context`, `JsonValue`, `JsonRepresentation`, `Draft`, `copyJson`, `isJsonValue`, and `replicatedState` with its types. | Node and browsers |
| `@earendil-works/chord/node` | Child host processes: `createHostManager`, `forkDriver`, `childControl`, `processLock`; the facet module loader `nodeLoader`. | Node |
| `@earendil-works/chord/context` | Explicit cancellation and invocation values: `BACKGROUND_CONTEXT`, `withCancel`, `withAbortSignal`, `withoutAbortSignal`, `withContextValue`, `awaitWithContext`. | Node and browsers |
| `@earendil-works/chord/delta` | The transactional JSON tracker, structural diff, immutable apply, and the wire encoder/decoder for operation batches. | Node and browsers |

## Quick start

```ts
import { Type } from "typebox";
import { cell, createHost, method, remote } from "@earendil-works/chord";

// contract.ts: shared by provider and consumers
export const Counter = remote("demo.counter", {
	version: 1,
	input: Type.Object({ name: Type.String() }),
	variants: {
		default: {
			state: { count: Type.Number() },
			methods: { increment: method(Type.Object({ by: Type.Number() }), Type.Null()) },
		},
	},
});

const host = createHost({ name: "server", principalKey: (p) => p.kind });

host.serve(Counter, ({ name }, _principal, self) => {
	const state = self.state({ count: cell(Type.Number(), 0) });
	return {
		kind: "default",
		count: state.count,
		increment: async ({ by }, ctx) => {
			state.count.change(ctx, (n) => n + by);
			return null;
		},
	};
});

await host.root(async (ctx) => {
	const clicks = ctx.get(Counter, { name: "clicks" }); // a handle; held until this root ends
	clicks.count.subscribe((n) => console.log("count", n));
	await clicks.increment({ by: 2 }, ctx); // logs 0, then 2
});
```

## Documentation

- [Tutorial](docs/tutorial.md): a shared todo list, built up section by section. Every example runs as `test/tutorial.test.ts`.
- [Usage guide](docs/guide.md): API reference for contracts, objects, state, roots, lifetime, plugins, hot reload, hosts, and links.
- [Specification](docs/spec.md): compatibility, lifetime, and reload semantics, plus known limitations and implementation decisions.
- [Delta guide](src/delta/README.md): ownership, lifecycle, operation, and replica contracts of `@earendil-works/chord/delta`.

## Tracking JSON deltas

Import the standalone transactional tracker from `@earendil-works/chord/delta`:

```ts
import { applyImmutable, track } from "@earendil-works/chord/delta";

const tracker = track({ output: "", count: 0 });
const change = tracker.beginChange();
change.state.output += "done\n";
change.state.count += 1;
const prepared = change.prepare();

tracker.adopt(prepared);
const replica = applyImmutable(prepared.base, prepared.ops);
```

`tracker.value` is always the latest adopted immutable revision. Preparation does
not change authority; adoption validates the preparation and swaps the root pointer.
Assigned containers are copied by value and unchanged subtrees may be shared between
revisions.

The tracker uses trusted immutable ownership rather than defensive copying or
freezing. `track(initial)`, `prepareReplace(value)`, `replicatedState(initial)`, and
`replace(context, value)` take ownership of alias-free strict-JSON roots without
walking them. Callers must not mutate transferred or published data. Values placed
through drafts are already copied, so that walk also rejects non-strict JSON before
the draft changes. Published values are not frozen. In-process consumers may share
their containers with the provider; mutating a consumed value violates the contract
and can corrupt authority. Clone or serialize at any mutable trust boundary.

Replicated state provides the same model through a callback. `replicatedState` is a
standalone observable value, independent of hosts; Durable uses it for document,
view, and task-graph states:

```ts
import { replicatedState } from "@earendil-works/chord";

const initial = { output: "", count: 0 };
const status = replicatedState(initial); // transfers ownership of initial
status.change(context, (draft) => {
	draft.output += "done\n";
	draft.count += 1;
});
```

A successful `change()` publishes exactly one atomic revision. If its callback
throws, the original value and sequence remain unchanged. Draft handles become
unusable when the callback returns. The tracker emits string append and
front-truncate operations, array splices and permutations, sets, and deletes; large
edit sets may fold into a complete replacement.

`replicatedState(source, { onError })` instead attaches a publication-only state to
an authoritative revision source (`ReplicatedStateSource`): it captures a snapshot,
then publishes every committed frame in cursor order.

### Public state subscriptions

`state.subscribe(async (value, context, delivery) => { ... })` serializes callbacks
independently for each subscription. Hydration starts immediately when a value is
available, and its returned promise must settle before updates start. Synchronous
callbacks still run synchronously. Read the captured `value` inside an asynchronous
callback: `state.value` may already refer to a later revision.

Each subscription retains at most 100 pending complete-value deliveries, excluding
the running callback. On overflow, only the newest pending value, context, and
delivery metadata are retained; a not-yet-started initial hydration is preserved.
Thus public delivery sequences may skip. This is a frame-count policy, not a byte
limit.

The returned unsubscribe function immediately discards pending work and prevents
new callbacks. It neither aborts nor waits for the running callback. Synchronous
throws and promise rejections are observed, reported, and do not stop other
subscriptions or subsequent callbacks. Attached sources use their `onError`
handler; mutable states (and attached sources without a handler) report failures
by throwing in a microtask. Unsubscribing does not hide a later rejection from the
running callback.

Cells of Chord objects and their remote readables have their own subscription
model; see [State](docs/guide.md#state) in the usage guide.

---

## Guide

Chord builds applications out of **objects** that live in several processes (a server, workers, browser tabs) and can be **hot reloaded** while they run.

- An **object** is state plus code at an address. It is created on demand and lives while someone holds it.
- Everyone gets a **handle**, never the object. Handles work the same locally and across processes, and survive reloads.
- Every object knows its **principal**: an owner and a guest get different objects, with different methods.
- **State** is observable JSON. Remote viewers get a snapshot followed by deltas.
- **Hot reload** swaps code while it runs. Work in flight finishes on the code it started with, state is kept, and incompatible changes migrate at a safe point.

## Contents

- [Quick start](#quick-start)
- [Contracts](#contracts)
- [Serving objects](#serving-objects)
- [Declarations](#declarations)
- [Activation](#activation)
- [Principals and variants](#principals-and-variants)
- [Handles](#handles)
- [State](#state)
- [Calls, ctx and roots](#calls-ctx-and-roots)
- [Lifetime](#lifetime)
- [Registries](#registries)
- [Plugins](#plugins)
- [Hot reload](#hot-reload)
- [Hosts and links](#hosts-and-links)
- [Durable](#durable)
- [Errors](#errors)
- [Rules of thumb](#rules-of-thumb)

## Quick start

```ts
import { Type } from "typebox";
import { cell, createHost, method, remote } from "@earendil-works/chord";

// contract.ts: shared by provider and consumers
export const Counter = remote("demo.counter", {
	version: 1,
	input: Type.Object({ name: Type.String() }),
	variants: {
		default: {
			state: { count: Type.Number() },
			methods: { increment: method(Type.Object({ by: Type.Number() }), Type.Null()) },
		},
	},
});

const host = createHost({ name: "server", principalKey: (p) => p.kind });

host.serve(Counter, ({ name }, _principal, self) => {
	const state = self.state({ count: cell(Type.Number(), 0) });
	return {
		kind: "default",
		count: state.count,
		increment: async ({ by }, ctx) => {
			state.count.change(ctx, (n) => n + by);
			return null;
		},
	};
});

await host.root(async (ctx) => {
	const clicks = ctx.get(Counter, { name: "clicks" });  // a handle; held until this root ends
	clicks.count.subscribe((n) => console.log("count", n));
	await clicks.increment({ by: 2 }, ctx);  // logs 0, then 2
});
```

## Contracts

A contract is a runtime value: a name, a version number, and a description of the members. Shipped bundles have no TypeScript, so everything the runtime checks must be in the contract. TypeScript types are inferred from it.

### Remote types

Remote types can be reached from other hosts. Everything that crosses the wire has a schema, and the provider validates it.

```ts
export const Chat = remote("pi.chat", {
	version: 1,
	input: Type.Object({ session: Type.String(), conversation: Type.Number() }),
	variants: {
		viewer: {
			state: { view: ConversationViewSchema },
		},
		participant: {
			state: { view: ConversationViewSchema },
			methods: {
				send: method(SendInputSchema, Type.Object({ submissionId: Type.Number() })),
				stop: method(Type.Null(), Type.Null()),
			},
		},
	},
});
```

### Local types

Local types are reachable only inside their host. Their members may be anything: functions, callbacks, native objects. Non-JSON members get opaque or function descriptors.

```ts
export const Index = local("pi.index", {
	version: 1,
	input: Type.Object({ session: Type.String() }),
	members: {
		search: method(Type.Object({ query: Type.String() }), Type.Array(HitSchema)),
		onChange: method(Type.Function([ChangeSchema], Type.Void()), UnsubscribeSchema),
		harness: opaque("pi.durable-harness@1"),
	},
});
```

### Inputs identify objects

`{ session: "S1", conversation: 1 }` always means the same object. Inputs are normalized (defaults applied, unknown fields removed), validated, and serialized canonically. Fields equal to their default are left out, so adding a new optional field with a default doesn't change existing addresses. Changing a default, or how inputs are normalized, needs a new type name.

### Versions and compatibility

Every bundle carries its own copy of each contract it was built against. When a consumer binds to a provider, the two copies are compared:

> A consumer built against version M binds to a provider at version N if **N = M and the provider's description covers the consumer's**. Otherwise the provider must offer an adapter in `accepts[M]`, or binding fails with `contract_mismatch`.

"Covers" means the provider still offers everything the consumer was built against:
- every member exists with the same kind;
- methods accept everything the consumer can send (new arguments must be optional) and return at least what it expects (extra result fields are fine);
- state values fit the consumer's schema;
- opaque members have the same name and version.

| Change | Version | Result |
| --- | --- | --- |
| Add a method, an optional argument, a result field, a state field | keep | binds |
| Remove or rename a member; make an argument required; change a type | **bump** | old consumers need `accepts`, or must be reloaded too |
| Same shape, different meaning (`query` is now a regular expression) | **bump** | as above; undetectable, so it's on you |
| Forgot to bump on a breaking shape change | keep | refused: "consumer needs member `search`" |

```ts
// version 2 changed what `search` means; old consumers keep working through an adapter
host.serve(Index, indexFactory, {
	accepts: {
		1: (current) => ({ search: ({ query }, ctx) => current.search({ query: escapeRegExp(query) }, ctx) }),
	},
});
```

## Serving objects

```ts
host.serve(Type, (input, principal, self) => behavior, options);
```

- The **factory** runs synchronously. It declares what the object needs and returns its behavior: methods and state members, plus `kind` for remote types. Returning a promise throws.
- There is one **record** per `(type, input, principal)`. It holds the object's state, resources and holds, and survives reloads. Only the behavior is replaced.
- **Options:**
  - `state: { version, migrate }`: the state version and its migrations (see [Hot reload](#hot-reload));
  - `accepts`: adapters for consumers built against older contract versions;
  - `linger`: how long to keep the object after the last hold is released;
  - `eager`: activate when the plugin loads, and keep it for the host's lifetime.

## Declarations

A reload runs the factory again over the same record. Declarations are matched by **property name**, so the new code's `status` cell is the old code's `status` cell, with its value.

```ts
host.serve(StatusStore, ({ session }, _host, self) => {
	const state = self.state({
		status: cell(StatusSchema, { running: false, tasks: 0 }),
		errors: cell(Type.Array(Type.String()), []),
	});
	const catalog = self.get(Catalog, {});
	const res = self.resources({
		db: resource({
			rev: 1,
			open: async ({ signal }) => openSqlite(statusPath(session), { signal }),
			close: async (db) => db.close(),
		}),
	});
	self.listen({
		catalogChanges: listener(catalog.rows, (rows, ctx) => state.errors.replace(ctx, checkRows(rows))),
	});
	self.tasks({
		flush: async (ctx) => {
			while (!ctx.signal.aborted) {
				await sleep(10_000, ctx.signal);
				await res.db.value.run("INSERT INTO history VALUES (?)", [JSON.stringify(state.status.value)]);
			}
		},
	});
	const derived = self.derive({
		summary: derivation([state.status, state.errors], (s, e) => ({ ...s, failing: e.length > 0 })),
	});
	return { summary: derived.summary, report: reportMethod(state) };
});
```

| Declaration | What it is | On reload |
| --- | --- | --- |
| `self.state({ name: cell(schema, initial) })` | an observable JSON cell; the schema is required | same cell and value; migrated when the state version is bumped |
| `self.get(Type, input, { at? })` | a hold on another object; its identity is the address | kept if declared again, otherwise released |
| `self.resources({ name: resource({ rev, deps?, exclusive?, open, close }) })` | a connection, watch, socket, port | kept; reopened only if `rev` or `deps` change |
| `self.listen({ name: listener(source, fn) })` or `listener(source, select, fn)` | reacts to a state or resource event | the same subscription, with the new `fn`, as long as the source (resource) and `select` are unchanged |
| `self.tasks({ name: async (ctx) => ... })` | long-running background work | the old run is aborted through `ctx.signal`, and the new code starts |
| `self.derive({ name: derivation(sources, fn) })` | live projection of state; `fn` is synchronous | kept; `fn` replaced |
| `self.register(Registry, { key: value })` | an entry in a registry | replaced at commit |
| `self.expose(res.name)` | a member backed by a resource (local types) | follows the resource |

A listener keeps its subscription across reloads when it is declared on the same resource (or source) with the same `select`: the same function, or one with the same source text. `select` is not called again, so a source that accepts a single subscriber (a Durable watch) survives reloads, and `select` may wrap the value in a new adapter object. A `select` whose result depends on captured values that change between reloads is not noticed; give such a listener a new name.

A name you no longer declare is released, closed or stopped, after the old code has finished what it was doing.

**State that must survive a reload lives in cells,** never in closure variables. A closure variable lasts as long as one version of the code.

```ts
// wrong: reset on every reload
host.serve(Visits, (_, _p, self) => {
	let visits = 0;
	return { hit: async (_, ctx) => ++visits };
});

// right
host.serve(Visits, (_, _p, self) => {
	const state = self.state({ visits: cell(Type.Number(), 0) });
	return {
		hit: async (_, ctx) => {
			state.visits.change(ctx, (n) => n + 1);
			return state.visits.value;
		},
	};
});
```

## Activation

The factory is synchronous, but activation isn't. `self.get` and `self.resources` only *declare*; the slow work happens afterwards:

```text
get(Index, { session: "S1" })
 1. run the factory               → declarations
 2. open declared resources        → e.g. connect to SQLite
 3. wait for declared holds        → dependencies activate first
 4. live                           → handles become "live"
```

```ts
host.serve(Index, ({ session }, _host, self) => {
	const res = self.resources({
		db: resource({ rev: 1, open: () => openSqlite(indexPath(session)), close: (db) => db.close() }),
	});
	return {
		search: async ({ query }, ctx) => res.db.value.all("SELECT entryId, text FROM fts WHERE fts MATCH ?", [query]),
	};
});

host.serve(Chat, ({ session, conversation }, principal, self) => {
	const index = self.get(Index, { session });  // a placeholder until Index is live
	return {
		kind: "participant",
		find: async ({ query }, ctx) => index.search({ query }, ctx),  // only ever runs once Chat (and Index) are live
		// ...
	};
});
```

**Rules:**
- Inside the factory, never use what you declared: `res.db.value` throws `not_ready`, and calling a handle throws. Use them in methods, listeners and tasks.
- **Concurrent `get`s** of one address share one activation, so the database opens once.
- **Failure propagates:** if `openSqlite` throws, `Index` fails, `Chat` fails with that cause, and every waiting `get` rejects. The next `get` tries again.
- **Abandoned activations:** if everyone releases before activation finishes, the result is disposed.

### Startup readiness and parent admission

`await host.load(facets)` and `await host.install(facet)` wait for the eager objects they install to become live:
resources are open, declared holds are live, and registrations are published. All facets in a load are installed
before activation is awaited, so an eager consumer can use a provider in a later facet. Ordinary lazy objects stay
lazy unless an eager object holds them. Factory, dependency and resource errors reject startup with the handle's
activation error; eager failures also reach `onError`. Installation is not rolled back on failure: close the host
when abandoning startup. `install` registers synchronously, so setup/registration errors still throw synchronously.

`await host.ready()` waits for the eager holds present when called, including direct `host.serve(..., { eager })`
and previously deferred loads. It is an activation barrier, not a continuous health check, a wait for tasks to
finish, or a remote-state hydration barrier. Later installations require another readiness wait.

A worker may need to open its local Harness and announce control readiness **before** the parent accepts its link.
An eager reporter waiting for the server's SessionStatus cannot become live before that acceptance. Awaiting the
whole load before announcing control readiness would deadlock. Defer the whole eager barrier explicitly:

```ts
// Connect the upstream link first; its outgoing holds can queue until the parent accepts it.
await worker.load(workerFacets, { awaitEager: false });  // also supported by install
const harness = worker.get(Harness, {});
await harness.ready;                                  // local bootstrap only; no upstream dependency
announceControlReady();                               // parent can now accept the worker link
await worker.ready();                                 // full eager readiness, including upstream holds
harness.release();
```

`awaitEager: false` still starts and host-holds every eager object; it skips waiting, not activation. There is no
automatic classification of upstream dependencies. Choose a local bootstrap handle with no upstream dependency,
connect before loading upstream consumers, and let the parent admit the link before the full barrier. Control
readiness means admission is possible, not that every eager object is live. Keep worker bootstrap counted as busy
until the full barrier settles, and report a later failure through the worker's fatal/startup-error path.

To hand out a native object a resource opens (a local type's `opaque` member), expose the resource. Handles read its value once the object is live, and `undefined` before:

```ts
host.serve(Harness, (_, _host, self) => {
	const res = self.resources({ durable: resource({ rev: 1, open: () => DurableHarness.open(storage), close: (h) => h.close() }) });
	return { harness: self.expose(res.durable) };  // contract member: harness: opaque<DurableHarness>("pi.durable-harness@1")
});

const harness = ctx.get(Harness, {});
await harness.ready;
harness.harness.resume();  // the DurableHarness itself
```

## Principals and variants

The application defines its principals and how they're keyed:

```ts
type Principal =
	| { kind: "owner"; via: "device" | "tunnel" | "relay" }
	| { kind: "guest"; id: string; name: string; session: string; mode: "view" | "full"; revision: number }
	| { kind: "worker"; session: string; generation: number };

const host = createHost({
	name: "server",
	principalKey: (p: Principal) =>
		p.kind === "owner" ? `owner@${p.via}` :
		p.kind === "guest" ? `guest:${p.id}:r${p.revision}` :
		`worker:${p.session}:${p.generation}`,
});
```

- There is one record per principal key: two tabs of the owner share an object, and a guest gets its own.
- Code inside a host acts as the built-in `host` principal, so internal objects are shared.
- A link stamps the principal of whatever connects to it. Callers can never supply their own.

**A remote factory picks a variant:**

```ts
host.serve(Chat, ({ session, conversation }, principal, self) => {
	if (!canView(principal, session)) throw forbidden();
	const c = self.get(Conversation, { session, conversation });  // as host: one shared instance
	if (!canSend(principal)) return { kind: "viewer", view: c.view };
	const author = authorOf(principal);
	return {
		kind: "participant",
		view: c.view,
		send: async (input, ctx) => c.submit(input, author, ctx),
		stop: async (_, ctx) => {
			await c.stop(author, ctx);
			return null;
		},
	};
});
```

```ts
const chat = ctx.get(Chat, { session: "S1", conversation: 1 }, { at: "session:S1" });
await chat.ready;
if (chat.kind === "participant") showComposer(chat.send);
else showReadOnly();
```

**What a variant doesn't do:**
- **It isn't complete authorization.** Methods still check their arguments: that a submission belongs to this conversation, or a session ID to this principal.
- **It doesn't cover flags that change while you hold the object.** Those are state, for example `you: { canDraw: boolean }`.
- **Revocation** is `host.invalidatePrincipal(match)`. It force-disposes matching records, here and over links, and their handles become `gone`. A new `get` runs the factory with the new grants.

Local types have no variants. Their only callers are inside the host, acting as `host`. If a local object needs to know who's acting, pass that explicitly, like `author` above.

## Handles

```ts
const chat = ctx.get(Chat, input, { at: "session:S1" });
chat.status;  // "loading" | "live" | "released" | "gone"
await chat.ready;  // live, or rejects with the activation error
chat.kind;  // the current variant
chat.shape;  // { kind, members, contract }
const send = chat.send;  // a stable function: always dispatches to the current code
chat.view.value;  // undefined until hydrated (remote: while someone subscribes)
chat.view.subscribe((v) => render(v));
chat.onStatus((status, error) => { if (status === "gone") reconnect(error); });
chat.release();
```

- **Calls on a `loading` handle wait** until it's live, respecting `ctx` cancellation and a deadline.
- A member missing from the current variant rejects with `not_in_variant`.
- After `release()`, every member rejects with `released`.
- **`gone`** means the object was forced away while held: revocation, archive, its host dying. Call `get` again, or show "unavailable". `onStatus` reports every status change (`live`, `loading` while a link reconnects, `released`, `gone` with the error), so a UI needn't poll.
- **A remote state member is hydrated only while subscribed.** When its last subscriber leaves, its `value` goes back to `undefined`, so a later subscriber never sees a stale value: it gets `undefined`, then the current snapshot.
- **Return values are values.** Anything long-lived you want to share is an object you reach with `get`.

## State

```ts
const state = self.state({ todos: cell(Type.Array(TodoSchema), []) });

state.todos.change(ctx, (draft) => {
	draft.push({ id: "t1", text: "Write docs", done: false });
});
state.todos.change(ctx, (draft) => {
	draft[0].done = true;
});
state.todos.replace(ctx, []);

state.todos.value;  // immutable
state.todos.subscribe((value) => render(value));

// mirroring an external immutable store: subscribers get a diff, not the whole value
state.view.replace(ctx, conversation.view);                    // diffs when the new value reuses old containers
state.view.replace(ctx, rebuilt, { diff: true });              // always diff
```

- A `change` is atomic: one revision, or nothing if the callback throws.
- `change` only touches the paths you mutate, so fields your code doesn't know about survive. Use `replace` only where your code owns the whole value.
- Values are immutable. Never mutate what you read or receive.
- Remote subscribers get a snapshot, then deltas. After a reconnect or a reload they get a `reset` snapshot, and nothing is replayed.
- `replace` sends a structural diff when the new value shares containers with the old one (a new revision of the same state), and a single replacement otherwise. `{ diff: true | false }` forces either. The value is the same either way.
- A behavior may expose another object's state member as its own: `return { kind: "viewer", view: conversation.view }`. It reads `undefined` only while that object is loading, which never happens once this object is live.

```ts
const derived = self.derive({
	visible: derivation([catalog.rows], (rows) => rows.filter((r) => visibleTo(principal, r))),
	openCount: derivation([state.todos], (t) => t.filter((x) => !x.done).length),
});
```

`derivation` functions are synchronous.

## Calls, ctx and roots

Every method gets `(args, ctx)`. Pass `ctx` on to everything you call:

```ts
send: async (input, ctx) => {
	ctx.signal.throwIfAborted();
	const uploads = ctx.get(Uploads, {});  // a hold owned by this call; released when it settles
	const files = await uploads.resolve({ ids: input.uploads }, ctx);
	return c.submit({ ...input, files }, author, ctx);
},
```

A **root** is a short tree of calls, started at ingress:
- by a link, for a request that arrives without one;
- by `host.root(fn)`, for timers and scripts;
- by each event delivered to a `listener`;
- by each Chord call made from a `task` or a Durable phase.

A root runs on the code that was current when it started (its **epoch**), across hosts, until it ends. Keep roots short. Long-running work is a `task`, and long waits are state.

```ts
// wrong: holds a root (and its version of the code) open for minutes
approve: async (_, ctx) => waitForHuman(ctx),

// right: record the request as state; the answer is a separate call
request: async (req, ctx) => {
	state.pending.change(ctx, (d) => {
		d.push(req);
	});
	return null;
},
answer: async ({ id, value }, ctx) => {
	state.pending.change(ctx, (d) => {
		settle(d, id, value);
	});
	return null;
},
```

## Lifetime

An object lives while it's **held**, and every hold has an owner:

| Owner | Acquired with | Released when |
| --- | --- | --- |
| another object | `self.get` | that object is disposed, or no longer declares it |
| a call | `ctx.get` | the call settles |
| a connection | a remote host's `get` | release, disconnect, revocation |
| the host | `eager: true` | host shutdown |
| UI | `useObject` | unmount |

- **Disposal** runs after the last hold, plus `linger`. Tasks are aborted, listeners removed, resources closed in reverse order (every close runs, and errors are collected), then the object's own holds are released, which can dispose further objects.
- **A resource's `close` may still use the objects its record holds.** That holds for host shutdown and revocation too: `host.close()` and `invalidatePrincipal` dispose holders before what they hold, and close links last. Bound remote calls in `close` with a signal: a call over a link that is already down waits for a reconnect.
- **Forced disposal** (revocation, archive) makes handles `gone` at once and aborts in-flight calls.
- **Holds must not form cycles.** Inside one host this is checked at `get`.

```ts
host.serve(Conversation, conversationFactory, { linger: 30_000 });  // switching back quickly doesn't reopen its watch
```

## Registries

```ts
export const Routes = defineRegistry<RouteHandler>("http.routes", { conflict: "error" });

// contribute (only from eager objects)
host.serve(Downloads, (_, _host, self) => {
	const blobs = self.get(Blobs, {});
	self.register(Routes, {
		"GET /download": async (request, who, ctx) => {
			const file = await blobs.find({ id: request.query.id }, ctx);
			if (!canView(who, file.session)) return forbidden();
			return stream(file, ctx);
		},
	});
	return {};
}, { eager: true });

// consume: a request sees the table of its own epoch
server.on("request", (req, res) =>
	host.root(async (ctx) => {
		const route = host.registry(Routes).get(`${req.method} ${pathOf(req)}`, ctx);
		return route ? route(req, principalOf(req), ctx) : notFound(res);
	}),
);
```

- Each epoch has one complete table. A reload never leaves a moment where an entry is missing.
- A request that started before a reload keeps using the old table.
- Order is first-registration order and survives replacement.
- `conflict: "error"` makes a duplicate key fail the registration (or the reload).

## Plugins

A plugin is a feature with one **facet** per host kind:

```text
plugins/chat/
  contract.ts    Chat, Conversation, Drafts
  server.ts      facet for the server
  worker.ts      facet for session workers
  web.tsx        facet for browsers
```

```ts
// plugins/chat/worker.ts
import { defineFacet } from "@earendil-works/chord";
import { Chat, Conversation } from "./contract.ts";

export default defineFacet((host) => {
	host.serve(Conversation, conversationFactory, { linger: 30_000 });
	host.serve(Chat, chatFactory);
});
```

```ts
// a host loads the plugins' facets for its kind
await host.load([
	new URL("../plugins/chat/worker.ts", import.meta.url),
	new URL("../plugins/status/worker.ts", import.meta.url),
]);
```

Built-in plugins are trusted code from this repository and load directly from source.

The facet's `setup` argument is its host, scoped to what a plugin needs: `serve`, `name`, `root(fn)` and `registry(R)`. Code that is not a Chord method, listener or task (Durable tools and hooks, callbacks of native libraries) keeps it to start roots and read registries, instead of reaching for a process-global host:

```ts
export default defineFacet((host) => {
	host.serve(Sessions, sessionsFactory);
	tools.register("rename_session", (args) =>
		host.root((ctx) => ctx.get(Sessions, {}, { at: "server" }).rename(args, ctx)),
	);
});
```

## Hot reload

```ts
await host.reload([new URL("../plugins/chat/worker.ts", import.meta.url)]);  // or reload every changed plugin
```

### What happens

1. **Load** the new modules.
2. **Prepare:** run the new factories over the existing records, without side effects. Cell writes throw, listeners and tasks don't start, registrations are collected, and changed resources are opened next to the old ones. Contracts are checked against every live consumer. Any failure leaves everything as it was.
3. **Gate:** only if a state version was bumped or an exclusive resource changes.
4. **Commit:** in one synchronous step, install the new code, swap registry tables, restart tasks, rebind listeners, and send `reset` and shape updates to subscribers.
5. **Retire:** old code keeps running the roots it started. Once they end, it's dropped, along with whatever it alone declared.

### Compatible changes: no waiting

Bug fixes, new methods, new cells, new resources and registration changes all switch immediately. A root that started on the old code finishes on it, and new roots get the new code.

### Changing what state looks like or means: bump the state version

```ts
// v1: { running, tasks } where tasks counted phases
// v2: tasks counts tasks, and usage is new
host.serve(StatusStore, ({ session }, _host, self) => {
	const state = self.state({ status: cell(StatusV2, { running: false, tasks: 0, usage: emptyUsage() }) });
	return {
		status: state.status,
		report: async (s, ctx) => {
			state.status.replace(ctx, s);
			return null;
		},
	};
}, {
	state: {
		version: 2,
		migrate: {
			status: (old, from) => (from < 2 ? { running: old.running, tasks: 0, usage: emptyUsage() } : old),
		},
	},
});
```

At the gate, for each live `StatusStore`:
1. **Roots already inside finish.** Their re-entrant calls are let in.
2. **Old roots that haven't touched it yet get `upgrade_conflict`** instead of old code over migrated state. They retry as a new root.
3. **`migrate` runs** on a private copy, and the result is validated against the new schema.
4. **Commit.** New roots use the new code and the migrated state.

If the roots inside don't finish within the deadline (5 s), the reload is **aborted** and nothing changes. The error names the blocking roots.

The runtime compares each cell's schema between old and new code:
- unchanged: compatible;
- changed with a bump: migrate;
- changed **without** a bump: the reload is refused.

A change of meaning with an identical schema needs a bump too. Nothing can detect that one for you.

### Resources

```ts
const res = self.resources({
	db: resource({ rev: 2, open: () => openSqlite(path, { wal: true }), close: (db) => db.close() }),  // rev 1 → 2: reopen
	port: resource({ rev: 1, exclusive: true, open: () => listen(8787), close: (s) => s.close() }),
});
```

- A reload doesn't touch a resource unless its `rev` or `deps` change.
- A changed resource opens next to the old one during prepare.
- An `exclusive` resource can't exist twice, so it's swapped at the gate: close the old one, open the new one, and reopen the old one if that fails.

### Contract changes

| Change | What happens |
| --- | --- |
| Additive, same version | reloads; consumers keep working |
| Breaking, version bumped, with `accepts[old]` | reloads; old consumers go through the adapter |
| Breaking, without an adapter | refused, unless the consumers reload in the same batch |
| Breaking, version not bumped | refused: "consumer needs member …" |

The host's own **eager bootstrap hold** is a lifecycle pin, not an old-version consumer. When a reload replaces
its provider, that hold adopts the new contract at commit; it does not require an `accepts` adapter for itself.
The record, cells and unchanged resources stay alive without reactivation. A refused reload keeps the original
hold and contract. Other holds (`self.get`, `ctx.get`, `host.get`, peers) still obey the compatibility rules above;
state-version bumps and migrations are still required when stored state changes.

### Several plugins at once

Reload them together: `host.reload([a, b])`. Prepare sees all new code at once, so a changed contract and its updated consumer check against each other.

On the server, `host.reload(serverFacets, { remote: { "session:": workerFacets } })` reloads every connected worker too. Its report covers the server; `report.children["session:S1"]` says what each worker changed, prepared and gated.

## Hosts and links

```ts
// server
const server = createHost({ name: "server", principalKey });
server.accept(webSocketLink(wss, { principal: (req) => authenticate(req) }));  // stamps owner or guest from cookies
server.route("session:", {
	authorize: (principal, host) => canReach(principal, host),  // before resolving or spawning
	resolve: (host) => workers.ensure(host),  // a link to the worker, spawned if needed
});

// worker
const worker = createHost({ name: `session:${id}`, principalKey, upstream: ipcLink(process) });

// anywhere
const chat = ctx.get(Chat, input, { at: "session:S1" });  // browser → server → worker
const sessions = self.get(Sessions, {}, { at: "server" });  // worker → server, acting as worker{S1}
```

- **The server relays** between its children: worker to worker, and browser to worker.
- **Disconnects:** when a browser disconnects, exactly the holds it had in workers are released.
- **Principals across links:**
  - a forwarded principal is accepted only from the parent link;
  - calls an object makes itself act as its host;
  - links ping, and a dead link releases everything held through it.
- **Reloads across hosts:** the server coordinates prepare and commit for every host.
- **Workers that start behind** (spawned after a reload) are caught up to the server's epoch before anything is routed to them. Calls their roots make to the server meanwhile run in the server's current epoch instead of failing `superseded`.
- **Browsers** don't take part in commits. They learn about new code through shape and `reset` messages, and an incompatible contract makes their calls fail with `upgrade_required`.

## Durable

A worker's host provides the Durable Harness as an eager local object. A Durable phase isn't a root: it's pinned to its registry snapshot by Durable itself. Each Chord call a hook or tool makes starts a fresh short root.

```ts
host.serve(Harness, (_, _host, self) => {
	const res = self.resources({
		durable: resource({
			rev: 1,
			open: () => DurableHarness.open(storage, { models, registry: durableRegistry(host, Extensions) }),  // a reader over the epoch tables
			close: (h) => h.close(),
		}),
	});
	return { conversation: (id: number) => res.durable.value.conversation(id) };
}, { eager: true });

// a plugin contributes a Durable extension like any registration
host.serve(Guard, (_, _host, self) => {
	self.register(Extensions, {
		guard: defineExtension({
			name: "guard",
			hooks: [hook(ToolTask, { beforeTool: (call) => (isDangerous(call) ? { block: "Needs approval" } : undefined) })],
		}),
	});
	return {};
}, { eager: true });
```

A reload changing the guard: Durable phases already running keep the old snapshot, the next phase uses the new one, and there's never a phase without a guard.

## Errors

| Code | Meaning |
| --- | --- |
| `forbidden` | The factory or a method refused this principal |
| `invalid` | Input, arguments or a result failed validation |
| `not_ready` | A declared resource or handle was used inside a factory |
| `not_in_variant` | The member doesn't exist in the variant you hold |
| `released` | The handle was released |
| `gone` | The object was forced away while held. Call `get` again. |
| `contract_mismatch` | The provider's contract doesn't cover the consumer's, and no adapter exists |
| `upgrade_conflict` | An old root reached an object migrated meanwhile. Retry as a new root. |
| `superseded` | The root's epoch is no longer available on this host. Retry. |
| `upgrade_required` | A browser's contract is outdated. Reload its web facets. |
| `unavailable` | The target host can't be reached or started |
| `aborted` | The call's `ctx` was cancelled |

## Rules of thumb

| Do | Not |
| --- | --- |
| Keep reloadable state in cells | Closure variables (lost on reload) |
| Bump the state version, with `migrate`, when a cell's shape or meaning changes | Changing a schema without a bump (refused) or a meaning without a bump (silent) |
| Bump the contract version on breaking changes; add `accepts` for old consumers | Renaming or removing members at the same version (refused) |
| Do slow setup in a resource's `open` | Awaiting inside the factory (it's synchronous) |
| Do side effects in resources, listeners, tasks and registrations | Effects in the factory body (they run during prepare) |
| Use `ctx.get` inside methods | `self.get` inside methods (a new hold per call) |
| Keep roots short; long waits are state | Awaiting a human inside a method |
| Check arguments in methods | Treating the variant as all of authorization |
| Pass `ctx` everywhere | Starting background work with the caller's `ctx` (use a task) |
| Treat state values as immutable | Mutating what you read |

---

## Specification

This document specifies the runtime in `src`. Where it and the code disagree, the disagreement is a bug. [Known limitations and decisions](#12-known-limitations-and-decisions) lists what the runtime does not do yet and the choices the sections below leave open.

Hard constraints:
- Chord's runtime depends only on its own `delta` module (tracker, applyImmutable, encoder/decoder, diff) and Node/browser built-ins plus `typebox` for schemas. No other Pi packages.
- Built-in plugins are trusted, loaded from source in-process. The plugin loader uses dynamic `import()` with a cache-busting query (owner-approved exception, `TODO(loader)`: replace with an isolating, evicting loader; old module copies leak; TUI plugins need isolation).
- Hot reload is required. Host restart only for Chord/runtime code changes or host-level crash recovery.

## 1. Concepts

| Term | Meaning |
| --- | --- |
| type | Name + contract. `remote` (addressable from other hosts; schemas for input, variant state members, method args/results) or `local` (host-only; members may be anything, including functions and native objects, but must be listed in the contract: `method`, `opaque` or a state schema). |
| factory | `(input, principal, self) => behavior`. Synchronous. Registered with `host.serve(type, factory, options)` from a plugin facet. |
| record | Stable identity per `(type, canonicalInput, principalKey)`. Owns cells, resources, holds, listeners, tasks, registrations. Survives reloads. |
| behavior | What a factory run returns (methods + state members; `kind` for remote variants). Immutable, per epoch. |
| handle | What `get` returns. Late-bound. Never the record or behavior. |
| hold | One handle's claim. A record lives while held. |
| principal | App-defined. Stamped by links. In-host code acts as the `host` principal. |
| root | One short Chord call tree, admitted at trusted ingress (link request without root, UI event, timer, `host.root`). Carries `{ rootId, epoch }`. |
| epoch | One committed set of behaviors/registrations per host (server-issued id). |
| code holder | Long-lived execution that is NOT a root: Durable phases/tool runs, browsers, `self.task` loops. Every Chord call they make starts a fresh short root. |

## 2. Contracts

Contracts are runtime values for every type (shipped bundles have no TypeScript; third-party plugins are built separately). TS types are inferred from them.

```ts
export const Chat = remote("pi.chat", {
	version: 1,                                   // contract version: a plain number, bumped only on breaking changes
	input: Type.Object({ session: Type.String(), conversation: Type.Number() }),
	variants: {
		viewer: { state: { view: ViewSchema } },
		participant: {
			state: { view: ViewSchema },
			methods: { send: method(SendSchema, Type.Object({ submissionId: Type.Number() })) },
		},
	},
});

export const Index = local("pi.index", {
	version: 1,
	input: Type.Object({ session: Type.String() }),
	members: {
		search: method(Type.Object({ query: Type.String() }), Type.Array(Hit)),
		onChange: method(Type.Function([Change], Type.Void()), Unsubscribe),   // non-JSON allowed for locals
		harness: opaque("pi.durable-harness@1"),                               // native object, by name+version
	},
});
```

- Input identity: normalize (apply defaults, strip unknown), validate, then canonical JSON with fields equal to their schema default omitted. Changing defaults or normalization requires a new type name.
- Remote calls validate args/results and state values at the provider boundary. Local calls are not validated per call.
- Local contracts list every member (`members: { search: method(...), harness: opaque(...), status: Schema }`). A handle that is still `loading` must know whether `h.x` is a method (a caller that waits until live), a state member (a readable) or an opaque value, before any behavior exists. Members missing from the contract are found only once the handle is live.
- Every bundle embeds the contract tokens it was built against (its own copy). Fingerprint = hash of the canonical description.

### Compatibility rule

A consumer built against version M binds to a provider at version N iff N = M and the provider's description covers the consumer's; otherwise only through `accepts[M]` adapters declared by the provider (`serve(type, factory, { accepts: { 1: (current) => v1View } })`); else `contract_mismatch`.

Covers: every consumer member exists with the same kind; methods: provider accepts every argument the consumer can send (new fields optional, nothing newly required or retyped) and the provider's result fits the consumer's expected result (extra fields fine); state: provider value fits consumer schema (extra fields fine); opaque: same name@version.

Additive changes need no bump. Breaking changes (remove/rename/retype, newly required, or a change of meaning with the same shape) bump the number. Same version + non-covering description = forgotten bump, refused. Meaning changes without a bump are undetectable (author's responsibility, as with Durable document versions).

Checked at: `get` binding, reload prepare (new provider token vs every surviving consumer holding the type and every loaded plugin importing it), remote holds (consumer token in the hold frame).

The exact host-owned eager bootstrap hold is a lifecycle pin, not a surviving old-contract consumer. When its
provider is replaced, commit replaces that hold with one bound to the new provider contract, acquiring it before
releasing the old hold so the same record, state and unchanged resources survive. It needs no `accepts` adapter
for its own previous contract. Prepare/abort do not change that hold. All other consumers retain their own tokens
and the normal coverage/adapter checks; state-version and migration checks are unchanged.

## 3. Factory and declarations

Factories are synchronous; returning a promise throws. Declarations are identified across factory reruns by **property names** in object literals (not call order, not separate string keys). Names are unique per record per declaration kind; a declaration method may be called more than once if names don't repeat. Holds are identified by their address.

```ts
host.serve(StatusStore, ({ session }, _host, self) => {
	const state = self.state({
		status: cell(StatusSchema, { running: false, tasks: 0 }),   // schema required, initial value
		errors: cell(Type.Array(Type.String()), []),
	});
	const catalog = self.get(Catalog, {});                         // hold; identity = canonical address (+ at)
	const res = self.resources({
		watch: resource({
			rev: 1, deps: [catalog], exclusive: false,
			open: async ({ signal }) => openWatch(session, signal),
			close: async (w) => w.close(),
		}),
	});
	self.listen({
		changes: listener(res.watch, (w) => w.events, (event, ctx) => state.status.change(ctx, (d) => { d.tasks = event.tasks; })),
	});
	self.tasks({ poll: async (ctx) => { /* loop until ctx.signal aborts */ } });
	const derived = self.derive({ visible: derivation([state.status], (s) => project(s)) });  // synchronous
	self.register(Routes, { "GET /status": handler });              // registry keys are the registry's own keys; eager records only
	return { status: derived.visible, report: (args, ctx) => { state.status.replace(ctx, args); return null; } };
}, {
	state: { version: 2, migrate: { status: (old, from) => upgrade(old, from) } },  // migrate gets the old value and its version
	linger: 30_000,
	eager: false,
});
```

| Declaration | Survives reload | Notes |
| --- | --- | --- |
| `state({ name: cell(schema, initial) })` | same cell and value; migrated on state-version bump | Schema required (no TypeScript at runtime). `change(ctx, draft => void)`, `replace(ctx, value)`, `value`, `subscribe`. Writes through `change` touch only mutated paths. |
| `get(type, input, { at? })` | kept if declared again (same address) | returns a handle |
| `resources({ name: resource({ rev, deps?, exclusive?, open, close }) })` | kept unless `rev`/`deps` change | `open` runs at prepare (non-exclusive) or at the gate (exclusive); handle exposes `.value` |
| `listen({ name: listener(source, select?, fn) })` | same subscription while source (resource) and `select` (identity or source text) are unchanged; `fn` swapped | each event starts a fresh root in the current epoch; `select` is not re-run for a kept subscription |
| `tasks({ name: fn })` | restarted with new code at commit (old one aborted via ctx.signal) | a code holder; calls inside start fresh roots |
| `derive({ name: derivation(sources, fn) })` | kept; fn swapped | synchronous fn |
| `register(registry, { key: value })` | value swapped at commit | eager records only (v1) |
| `expose(resource)` | follows the resource | a local member (usually `opaque`) whose handle value is the resource's value once live |

State members of a behavior may be cells, derivations, or state members of handles the record holds (they are defined once the record is live). `cell.replace(ctx, value, { diff? })` publishes a structural diff when the new value shares containers with the old one (or `diff: true`), else `r`. Facet `setup` receives `{ serve, name, root, registry }` of its host.

`migrate` per cell is `(old, fromVersion) => new`. A record may be several versions behind (author bumped more than once between reloads).

Removed vs guide: `self.own`, `holdWhile`, async factories, inferred dependencies.

### Synchronous factory, asynchronous activation

`self.get` and `self.resource` only declare and return placeholders. Activation of a record:

1. run the factory synchronously (declarations);
2. await declared resources' `open()` (e.g. connect a DB);
3. await declared holds becoming live (dependencies activate first, coalesced);
4. record is live: handles `live`, `ready` resolves.

Inside the factory, placeholders must not be used (`resource.value` throws `not_ready`; handle calls throw). Methods/listeners/tasks run only on live records, so their dependencies are live. External consumers (UI, roots) holding a `loading` handle: calls wait until live (ctx cancellation, deadline); state members read `undefined` until hydrated. Activation failures propagate to dependents and all waiting gets; the next get retries.

### Host eager readiness

- `host.install(facet, { awaitEager? })` installs declarations synchronously and returns a promise for this facet's
  eager activations. `host.load(facets, { awaitEager? })` installs the entire batch before awaiting its eager
  activations. `awaitEager` defaults to true. Unheld lazy objects are not activated.
- Factory, resource-open, dependency and activation-finalization failures reject the returned promise with the
  activation error (ChordError codes preserved; ordinary errors wrapped as `unavailable`). Eager failures also
  reach `onError`. Installation is not a rollback transaction; setup/registration errors from `install` throw
  synchronously. Abandoned startup should close the host.
- `{ awaitEager: false }` starts the same eager objects but resolves after installation, without waiting for their
  activation. `host.ready()` awaits a snapshot of the host's eager holds at call time (including direct eager
  `serve` and deferred loads), rejects their activation failures, and does not acquire additional holds. It is not
  an ongoing health check and does not await task completion or remote state hydration.
- Local bootstrap readiness and upstream admission are separate. A worker connects its upstream link, loads with
  `{ awaitEager: false }`, awaits its local bootstrap handle (e.g. Harness, with no upstream dependency), then
  announces control readiness so its parent can accept the link. Only after admission does it await `host.ready()`.
  Otherwise an eager reporter depending on server SessionStatus deadlocks with the parent waiting for control
  readiness. Deferred loads skip the whole barrier, not selected dependencies; callers explicitly choose local
  bootstrap handles, keep bootstrap busy until full readiness, and propagate later startup errors.

## 4. Principals, variants, handles

- `createHost({ principalKey })` maps principal to a key that includes connection provenance and grant revision. Records are per principal key. `host` is a built-in principal for in-host calls.
- Remote factories return `{ kind, ...members }`; `kind` must be a declared variant; members must match it. Local factories return any object.
- Handle: `status` (`loading | live | released | gone`), `ready` promise, `kind`, `shape` (`{ kind, members, contract }`), `onStatus(listener)` (every status change, with the error for `gone`), late-bound members, `release()`. A remote handle's state member holds a value only while subscribed (`undefined` after its last subscriber leaves). Shape changes (reload, variant) are pushed; members missing from the current variant reject `not_in_variant`; released handles reject `released`; forced disposal makes handles `gone`.
- Methods are `(args, ctx) => Promise<result>`. Factories still check arguments; variants are not complete authorization.
- Revocation: `host.invalidatePrincipal(match)` force-disposes matching records on this host and propagates over links; links re-stamp or close.

## 5. Lifetime

- Hold owners: record (declared `get`), call (`ctx.get`, released at settle), connection (remote holds; relay maps per origin connection), host (eager), UI.
- Activation coalesced per address; if all requesters leave before it completes, the result is disposed. Factory throw: unwind declarations, reject gets, next get retries.
- Disposal after last hold + `linger`: tasks aborted, listeners removed, resources closed (reverse order; all run; errors aggregated), holds released (cascade).
- Bulk forced disposal (`host.close`, `invalidatePrincipal`) goes in waves, holders before what they hold, so a resource's `close` can still use its record's holds; `host.close` closes links after the records.
- Forced disposal: handles `gone` immediately, new calls rejected, in-flight call contexts aborted, then cooperative cleanup.
- Hold graph acyclic in-host (checked at get); across hosts by convention.
- Links have ping/timeout; a dead link releases everything held through it.

## 6. Roots and epochs

- `Ctx = { signal, rootId, epoch, get(...) , principal? }`. Explicit; no AsyncLocalStorage dependency (may be used in dev to warn).
- A link creates a root for a request that carries none; nested remote calls carry `{rootId, epoch}`.
- Dispatch: a call with epoch E runs the record's behavior for E. A host retains at most `current` and `previous` epochs (two-version rule). A call for an epoch the host doesn't have (older than previous, or host started later) is rejected `superseded` (retryable by starting a new root). Never substitute another epoch.
- Browsers never carry epochs into the server: browser calls start roots at the server. Browsers learn of changes via shape/reset pushes and a server `Manifest` object; incompatible contract fingerprint -> `upgrade_required`.

## 7. Reload

Explicit trigger (`reload_plugins` tool, button, API). Serialized; no nesting.

1. Build/type-check gate (application tooling, outside Chord): dependency-closed set; refuse breaking remote contract changes without a contract version bump.
2. Load: on every affected host, import new facet modules (cache-busted).
3. Prepare: for each live record of each affected type, run the new factory in recording mode: existing cells readable, writes throw; listeners/tasks/registrations recorded, not started; holds recorded; non-exclusive resources whose key is new or `rev`/`deps` changed are opened as candidate-owned (closed on abort). Validate keys, variants, registry collisions. New records activated during prepare use the current epoch (old code). Any failure: abort, discard candidates. Vote.
4. Gate (only records whose state version was bumped or which replace an exclusive resource, plus records depending on those resources):
   - Admission cut: from now, an old-epoch root that has not touched the record gets `upgrade_conflict` (retryable), not queued. Roots that already hold an activation lease on it are grandfathered; their re-entry is admitted.
   - Wait for grandfathered activations to finish, deadline (default 5 s). Missed deadline: abort the reload, reopen, nothing changed (report blocking roots).
   - Exclusive resources: close old, open new; on failure reopen old and abort.
   - Run `migrate` into private copies; validate.
5. Commit (server commits itself, then sends commit to children; the decision is not persisted, see section 12; FIFO links guarantee no host receives a new-epoch root before committing): each host in one synchronous step installs migrated cell values and state versions, installs behaviors as epoch E', swaps registry tables, restarts tasks with new code, rebinds listeners, pushes shape/reset to subscribers, opens gates. E' current, E previous.
   The coordinator's result carries `children`: each participating child's prepared report (its vote).
6. Retire: when no roots of `previous` remain (or on the next reload, which first waits for retirement with a deadline), drop its behaviors and release declarations only it declared.

Compatible changes (no state bump, no exclusive resource change) skip the gate: no waiting.

State compatibility rule: reload prepare compares each cell's old and new schema. Unchanged: compatible (no gate). Changed with the state version bumped: gate + `migrate`, output validated against the new schema. Changed without a bump: reload refused. A change of meaning with an identical schema needs a bump too (undetectable; author's responsibility). Initial values and migrate outputs are validated; per-write validation in dev mode.

## 8. Registries

```ts
export const Routes = defineRegistry<RouteHandler>("http.routes", { conflict: "error" });
self.register(Routes, { "GET /download": handler });       // in an eager record; keys are the registry's keys
host.registry(Routes).get("GET /download", ctx);            // table of ctx.epoch (or current without ctx)
host.registry(Routes).subscribe((table, epoch) => ...);     // bridges for imperative consumers (Durable)
```

Per-epoch immutable tables; order = first registration order, kept on replace. An application can implement Durable's `RegistryReader` from the table (snapshot per epoch) so phases pin a complete snapshot; Chord does not ship that bridge.

## 9. Hosts and links

- `createHost({ name, principalKey, upstream? })`; `host.accept(link)` for children; `host.route(prefix, { authorize(principal, hostName), resolve(hostName) => Promise<Link> })`.
- Links: `memoryLinkPair()` (tests), Node IPC (child_process), WebSocket (server `ws`, browser `WebSocket`).
- Principal stamping: the accepting side stamps the principal of what connects (from its authenticator); forwarded principals accepted only from the parent link; payload principal fields ignored.
- A child that connects behind its parent's epoch is fenced (nothing routed to it) and reconciled by a reload of its modules to the parent's epoch. Calls its roots of the old epoch make upstream are admitted in the parent's current epoch (the parent never ran that epoch), not rejected `superseded`.
- Relay: server forwards frames for `at` hosts to the resolved child link, mapping holds per origin connection; authorizes before resolving/spawning and re-checks after.
- Wire frames (JSON): `hello`/`bye`, `hold`/`release` (a hold returns `shape` or `gone`; there is no separate `get`), `shape`, `call`/`result`/`cancel`, `sub`/`unsub` and `state` (`snap`/`ops`/`reset` with a per-subscription delta encoder), `gone`, `root_end`, `retire`, `invalidate`, `ping`/`pong`, reload control (`prepare`/`vote`/`commit`/`abort`).

## 10. Host manager (library)

`createHostManager({ driver, keepAlive })`: fork driver (entry, init, lock, env), serialized start/stop/replace, exit-before-replace, process-tree kill after grace, control channel (ready/fatal/shutdown), liveness callback (booting, activeCalls, viewers with heartbeats, durable tasks, idleFor).

## 11. Test coverage

The tests cover at least: lifetime/holds/linger/forced disposal/gone; activation coalescing and abandonment; principals and variants; remote calls over memory links incl. relay and principal forgery attempts; state snap/ops/reset over a link with reconnect; registries per epoch; reload: compatible (no wait, pinned roots), prepare isolation (writes throw, failing factory leaves everything unchanged), state bump with migrate and gate, `upgrade_conflict` for late old roots, deadline abort, exclusive resource replacement, cross-host commit ordering, two-version retirement and `superseded`.

## 12. Known limitations and decisions

### Still open

- **Retirement across hosts.** A child retires an epoch only after its parent retired it (`retire` frame) and its own roots of that epoch ended; the server decides from its own roots. A root started on a worker that calls up to a server which has already retired the epoch both had still gets `superseded` (retryable).
- **The commit decision is not persisted** (section 7, step 5). A server crash between its own commit and a child's commit leaves that child on the old epoch until it reconnects and is reconciled.
- **One level of reload participants.** Only the coordinator's direct child hosts take part; a child does not forward `prepare` to its own children.
- **Reconciliation needs the child's module list.** It is remembered from cluster reloads (`host.remoteModules`), so a server restart forgets it, and a child behind a restarted server then reloads no modules: it gets the epoch id with its own code. The reconciliation vote deadline is fixed at 30 s; a failed reconciliation closes the link, so the host manager restarts the worker.
- **Links do not resume.** The provider releases everything held through a closed link at once, so re-held records are new ones. Keeping holds for a reconnect window would need session ids on links. Calls in flight when a link drops reject `unavailable`; whether they ran is unknown.
- **Refused clients cannot tell.** The WebSocket adapter closes unauthenticated sockets; the client sees a dropped upstream and its calls wait for a reconnect until their ctx is aborted.
- **The publication queue is process-wide and synchronous.** A slow observer delays every later notification in the process, including those of other hosts in the same process.
- **No automatic restart.** A terminal host failure is picked up by the host manager's `keepAlive` or `fatal` path, not inside Chord.
- **The Node loader leaks.** Every reload imports fresh module copies that are never evicted, and it does not isolate plugins (`TODO(loader)`).
- **Stale socket locks.** On Unix systems other than Linux, two processes that probe the same stale socket file at the same moment could both take the lock. Managers serialize starts per lock name.
- **Listener `select` identity.** A listener's subscription is kept across factory runs when its origin and `select` are unchanged; `select` counts as unchanged when identical or with the same source text, so a `select` whose behavior depends on captured values that change between runs is not detected.
- **Shutdown and dead links.** `host.close()` disposes records in waves (holders before what they hold) and closes links last. A `close` that awaits a remote call over a link that is already down waits for a reconnect; bound such calls.

### Decisions

- **Errors.** The guide's codes; a `reason` field carries the detail, for example `invalid/args`, `invalid/cycle`, `invalid/duplicate`, `invalid/read_only`, `invalid/not_eager`, `invalid/registry_conflict`, or `unavailable/unknown_type`. A `ChordError` thrown by a factory or a dependency keeps its code through every dependent; other errors become `unavailable`, with the original as `cause`.
- **Reload errors.** There is no `reload_aborted` code. A failed reload throws the cause's code and reason with the message `reload aborted: …` (the cause is attached). Reasons of its own are `aborted/gate_deadline` (with the blocking roots in `details`), `aborted/deadline`, `aborted/vote_deadline` and `unavailable/reload_running`. Across hosts, the message names the host that failed. A child cannot reload on its own (`unavailable/not_coordinator`).
- **New records during prepare.** A reload pre-allocates the next epoch ("pending"). Types the same reload adds are served from it; their records install behavior only for the pending epoch and are force-disposed if the reload aborts.
- **Gate admission.** From the gate until commit or abort, creating a new record of a changed type fails with `upgrade_conflict` (retryable, reason `gate`); nothing is paused, so nothing can deadlock. Gated records get `minEpoch = E'`: calls and writes carrying an older epoch are rejected `upgrade_conflict` permanently, and a gated record drops its previous-epoch behavior at commit. Only records whose state version or exclusive resources change are gated.
- **Tasks and listeners during the gate.** Tasks of gated records are aborted at the admission cut and restart with new code at commit, or with the old code on abort. Listener events for gated records are queued and replayed through the new listener at commit, or the old one at abort.
- **Grandfathered roots** are the roots that called into the record and are still running at the cut. Every host remembers on which links a root's calls went out and sends `root_end` on them when the root ends, so leases outlive calls across hosts.
- **Removed types and missed retirement.** Records of removed types are force-disposed at commit. When a retirement deadline is missed, retirement is forced, so those roots get `superseded` on their next call.
- **Two-version rule.** A record of a changed type created after a commit has only new code; a previous-epoch root calling it gets `superseded`.
- **Validation.** Remote calls are validated at handle dispatch, in-host too: a direct binding against the provider's schema, a binding through an adapter against the consumer's. A provider validates each snapshot and reset of a remote state member once per (re)subscription, against the consumer's contract through an `accepts` adapter and the provider's otherwise; ops are validated only in dev mode. At reload, the new provider's description must cover the old provider's when the version is unchanged, in addition to the check against live consumers and facets' `uses`.
- **Contracts.** Local contracts list their members, so a loading handle knows whether a member is a method, state or opaque. Canonical identity omits input fields equal to their default; with TypeBox, use `Type.Optional(Type.X({ default }))` to let callers omit them. Provider variants must cover consumer variants; members the consumer's contract does not list are hidden. Schema change detection compares canonical JSON, so reordering `anyOf` branches counts as a change. Fingerprints use a non-cryptographic 64-bit hash: synchronous and browser-safe; contracts are trusted.
- **Principals.** A root ctx at ingress acts as its principal (`host.root(fn, { principal })`); contexts inside objects act as `host`. The acceptor decides a link's kind and name (`accept(link, { principal, kind, name })`); only configured host links are addressable, carry roots and may vote, and control frames are accepted only from the parent. Clients never carry roots or epochs. Relaying needs a matching `route`; `authorize(principal, hostName)` runs before `resolve` and again after, and revoking or re-stamping a principal closes its relays at once. `invalidatePrincipal(match)` re-stamps or closes matching links and propagates pattern matches to child hosts.
- **Cells and readables.** A value returned from `change` replaces the value and is always validated; `replace` transfers ownership without copying; by default (`{ diff }` overrides) it publishes a diff when the new value reuses a container of the old one at the same key, else `r`. `subscribe(fn)` delivers values, starting with the current one; `events(fn)` delivers `snap`, then `ops`, or `reset`. Handle state members are stable readables, `undefined` while loading or outside the variant, and reset when their source moves. Remote state members hydrate only while subscribed and forget their value when the last listener leaves.
- **Holds and calls.** A hold's identity is its address; a second `self.get` of the same address in one run returns the same handle. A handle call without ctx, or with a task ctx, starts a fresh root in the current epoch; a ctx whose call or root already settled is refused (`aborted/expired`), one from another host `invalid/foreign_ctx`. Calling a handle inside a factory throws `not_ready`.
- **Resources and disposal.** New and replaced exclusive resources open at the gate, and so do non-exclusive resources of the same record that depend on them. A new record for an address that is still being disposed waits for that disposal. A resource open that completes after its signal aborted closes its value at once.
- **Links and the host manager.** Every received frame is validated against its schema; malformed frames, duplicate ids and control frames from the wrong side close the link. Each connection pings every `pingInterval` and closes after `pingTimeout` without a frame. The child holds a kernel lock (an abstract socket on Linux and Android, a named pipe on Windows, a probed socket file elsewhere), acquired by `childControl().lock()` before storage opens. The manager kills the child's process group on every exit path and derives `booting` and `idleFor` from the child's liveness reports. WebSocket support is structural, so Chord does not depend on `ws`.
- **The state API stays.** Objects keep named cells and derivations; giving each object exactly one state value was rejected. Do not reopen this without a new, concrete problem.

---

## Tutorial

## 1. What problem does Chord solve?

A todo list has data, operations on that data, and several people looking at it.
You could hand-write object creation, subscription cleanup, messages between
processes, and code replacement. Chord connects these pieces for you.

A **host** is the runtime that owns objects. An **object** combines state with
methods at an address, such as “the family todo list.” A **handle** is a caller's
reference to that object, not the object itself. Several handles can reach the
same object. Handles can also reach another host over a connection.

```text
browser host                         server host
handle + subscribed rows -- link --> Todos view (owner or guest)
                                           |
                                        handle
                                           v
                                   TodoStore: rows + methods
```

We will start inside one host, add observable state, then share it with a
browser. Finally we will add background work, plugins, and hot reload.
**Live state** means subscribers receive new values when data changes, without
asking for it again.

<!-- example:01 -->
```ts
const host = createHost({ name: "todo-server" });
assert.equal(host.name, "todo-server");
await host.close();
```

The assertion passes: the host's name is `todo-server`. Creating a host does
not create a todo object, start a server socket, or persist data. `close()`
shuts down its objects and connections.

> **Tip:** These are executable TypeScript examples, using assertions to show
> results. Shared imports are at the end. Later sections reuse earlier contracts
> and functions, but each section's test starts with fresh hosts. Test-only
> cleanup closes hosts even when an assertion fails; snippets omit that cleanup.

## 2. Your first object

Before callers can use an object, they need to agree on its name and members.
That agreement is a **contract**: a runtime value that also gives TypeScript its
types. A **schema** describes a value's shape. We use TypeBox's `Type` to write
schemas; `Type.Null()` means this method takes no useful argument.

Start with a label for a named list. `local` means only code inside this host
can reach it. The input `{ list: "family" }` identifies which list we want;
it is not an argument to `label`.

<!-- example:02-contract -->
```ts
const TodoLabel = local("tutorial.todos", {
	version: 1,
	input: Type.Object({ list: Type.String() }),
	members: { label: method(Type.Null(), Type.String()) },
});
```

A **factory** is a synchronous function that creates the object's behavior:
the methods and state callers will see. `serve` registers a contract and its
factory. Registration alone does not activate this lazy object; the first
`get` does.

A **root** is one short tree of calls, such as the work for a button click.
`host.root` starts it. Its **context**, called `ctx`, carries cancellation,
caller identity, and the code version for nested calls. Pass it to methods you
call from that root.

<!-- example:02-call -->
```ts
const host = createHost();
host.serve(TodoLabel, ({ list }) => ({ label: () => `Todos for ${list}` }));
const result = await host.root(async (ctx) => {
	const todos = ctx.get(TodoLabel, { list: "family" });
	return todos.label(null, ctx);
});
assert.equal(result, "Todos for family");
```

The result is `"Todos for family"`. `ctx.get` returns a handle immediately;
method calls wait for the object to become live. The handle acquired through
`ctx.get` is released when this root ends. We never receive the factory's
returned object directly. A standalone call without `ctx`, such as
`todos.label(null)`, starts its own root. Inside a root or method, pass the
existing `ctx` so nested calls stay in the same call tree.

The factory may also receive `principal` (who is asking) and `self` (the
object's declaration API). We did not need them yet.

> **Why:** The handle separates callers from implementations. Later, replacing
> code will not require replacing every caller's reference.

## 3. Give the list live state

A label is not a todo list. We need rows that can change, and a count that always
agrees with them. A **cell** owns an observable JSON value. A **derivation**
computes another observable value from cells or other readable sources.

Extend the contract with `rows`, `openCount`, and editing methods. State
members describe values, not methods. This adds members at contract version 1;
older callers that only need `label` still have everything they need.

`self.state` declares named cells. The name `rows` is important: on reload,
Chord matches that name to the existing cell and keeps its value.

<!-- example:03-contract -->
```ts
const Todo = Type.Object({ text: Type.String(), done: Type.Boolean() });
const Rows = Type.Array(Todo);
const TodoStore = local("tutorial.todos", {
	version: 1,
	input: Type.Object({ list: Type.String() }),
	members: {
		label: method(Type.Null(), Type.String()),
		rows: Rows,
		openCount: Type.Number(),
		add: method(Type.Object({ text: Type.String() }), Type.Null()),
		finish: method(Type.Object({ index: Type.Integer() }), Type.Null()),
		reset: method(Rows, Type.Null()),
	},
});
```

The factory now declares a cell and a derivation. Each method receives its
arguments and a context; changing the cell updates its readers and its derived
count together.

<!-- example:03-factory -->
```ts
const todoFactory: Factory<typeof TodoStore> = ({ list }, _principal, self) => {
	const state = self.state({ rows: cell(Rows, []) });
	const derived = self.derive({
		openCount: derivation([state.rows], (rows) => rows.filter((todo) => !todo.done).length),
	});
	return {
		label: () => `Todos for ${list}`,
		rows: state.rows,
		openCount: derived.openCount,
		add: ({ text }, ctx) => {
			state.rows.change(ctx, (draft) => {
				draft.push({ text, done: false });
			});
			return null;
		},
		finish: ({ index }, ctx) => {
			state.rows.change(ctx, (draft) => {
				const todo = draft[index];
				if (!todo) throw invalid("args", "No such todo");
				todo.done = true;
			});
			return null;
		},
		reset: (rows, ctx) => {
			state.rows.replace(ctx, rows, { diff: true });
			return null;
		},
	};
};
```

`change(ctx, fn)` gives `fn` a temporary mutable **draft**. Here `add`
pushes a row and `finish` changes one field. The draft is discarded if the
callback throws. The callback must be synchronous.

`replace(ctx, value)` replaces the whole value. We use it for resetting a
list we own completely. `{ diff: true }` asks Chord to publish just the
structural changes. Without that option, replacement diffs automatically when
the new value shares containers at the same keys with the old one; unrelated
values normally publish a whole-value replacement. Either way, subscribers
receive the same resulting value.

<!-- example:03-call -->
```ts
const host = createHost({ dev: true });
host.serve(TodoStore, todoFactory);
const todos = host.get(TodoStore, { list: "family" });
await todos.ready;
const counts: (number | undefined)[] = [];
const stop = todos.openCount.subscribe((value) => counts.push(value));
await host.root(async (ctx) => {
	await todos.add({ text: "Buy milk" }, ctx);
	await todos.finish({ index: 0 }, ctx);
	await todos.reset([], ctx);
});
assert.deepEqual(counts, [0, 1, 0]);
assert.deepEqual(todos.rows.value, []);
stop();
todos.release();
```

The count subscriber sees `0, 1, 0`: initially empty, one unfinished todo,
then no unfinished todos. Resetting to empty does not add another count
notification because the derived count is still zero. The final rows are `[]`.
`subscribe` calls back immediately with the current value and returns an
unsubscribe function. We await `ready` first so that value is not a loading
placeholder.

> **Why:** Store reloadable state in cells, not closure variables. Treat
> `cell.value`, `handle.rows.value`, and subscriber values as immutable.
> Only mutate drafts inside `change`; do not keep a draft for later use.
> A derivation runs synchronously, so use it for projections, not database work.

## 4. Let objects use objects and resources

Saving a todo may require both the list and a database connection. A **hold**
is a handle's claim that keeps an object alive. `self.get` declares a hold
owned by this object; it lasts longer than a single method call.

A **resource** is something the runtime opens and later closes, such as a
database connection. Its `open` may be asynchronous even though the factory
must be synchronous. The example database is deliberately fake: it just saves
strings in memory.

`opaque<T>("name@version")` describes a native, host-only member. It is not
JSON state and cannot be sent over a link. `self.expose` connects that member
to a declared resource, without reading the resource during the factory.

<!-- example:04-database -->
```ts
const Database = local("tutorial.database", {
	version: 1,
	input: Type.Object({}),
	members: { db: opaque<{ saved: string[] }>("tutorial.database@1") },
});
const SavedTodos = local("tutorial.saved-todos", {
	version: 1,
	input: Type.Object({ list: Type.String() }),
	members: { add: method(Type.Object({ text: Type.String() }), Type.Null()) },
});
const host = createHost();
let opens = 0;
const closed = Promise.withResolvers<void>();
host.serve(Database, (_input, _principal, self) => {
	const res = self.resources({
		db: resource({
			rev: 1,
			open: async () => {
				opens++;
				return { saved: [] as string[] };
			},
			close: () => closed.resolve(),
		}),
	});
	return { db: self.expose(res.db) };
});
```

The factory returns an exposed marker, not an opened connection. Chord runs
`open` after declarations finish. The promise named `closed` lets the test
observe eventual cleanup.

Now declare `SavedTodos` as an object that holds both the store and the database.
Its editing method uses these dependencies only after activation.

<!-- example:04-saving -->
```ts
host.serve(TodoStore, todoFactory);
host.serve(
	SavedTodos,
	({ list }, _principal, self) => {
		const database = self.get(Database, {});
		const todos = self.get(TodoStore, { list });
		return {
			add: async ({ text }, ctx) => {
				database.db!.saved.push(text);
				await todos.add({ text }, ctx);
				return null;
			},
		};
	},
	{ linger: 0 },
);
```

An outside consumer holds a `SavedTodos` handle. We also hold `Database`
directly so we can inspect what was saved.

<!-- example:04-call -->
```ts
const saved = host.get(SavedTodos, { list: "family" });
const database = host.get(Database, {});
await saved.ready;
await host.root((ctx) => saved.add({ text: "Buy milk" }, ctx));
assert.deepEqual(database.db!.saved, ["Buy milk"]);
assert.equal(opens, 1);
const statuses: string[] = [];
saved.onStatus((status) => statuses.push(status));
database.release();
saved.release();
await closed.promise;
assert.equal(saved.status, "released");
assert.ok(statuses.includes("released"));
```

After the method, the fake database contains `["Buy milk"]`. It opened once,
even though two objects held it. `SavedTodos` and `Database` become live
only after their resources and declared dependencies are ready. That is why
`database.db!` is safe inside this live object's method: activation has
already established that dependency. An outside caller must await readiness.

When both external handles are released, `SavedTodos` is disposed and
releases its own database hold. With no holds left, the database closes; we
wait for `closed.promise` to prove it. The released handle stays
`released`, and `onStatus` reports that transition. `onStatus` watches
changes; unlike state subscription, it does not deliver an initial status.

`linger` is a delay in milliseconds after the last hold leaves. Zero disposes
without a grace period; a positive value can avoid reopening an expensive
resource when a screen is briefly hidden. Linger is not persistence.

> **Tip:** A factory only declares dependencies. Never call a held method or
> read `resource.value` there, including during reload. Activation happens
> afterward. Bump a resource's `rev` when its configuration should be reopened.
> Disposal stops tasks and listeners, closes resources, then releases holds.

## 5. Who is asking? One store, two views

Owners may add todos; guests may only read them. A **principal** is the
application-defined identity of a caller. A **variant** is a named set of
members a remote object offers to that principal. It lets the UI discover
whether an editing method is available.

Do not create a separate data cell for each viewer: their lists would diverge.
Instead, each view holds the same host-local `TodoStore` and exposes its rows.
`self.get` defaults to the host principal, so owner and guest views share
that store. Remote view records themselves are separate per principal key.

<!-- example:05-views -->
```ts
const Todos = remote("tutorial.todo-view", {
	version: 1,
	input: Type.Object({ list: Type.String() }),
	variants: {
		viewer: { state: { rows: Rows } },
		editor: {
			state: { rows: Rows },
			methods: { add: method(Type.Object({ text: Type.String() }), Type.Null()) },
		},
	},
});

function serveViews(api: Pick<Host, "serve">): void {
	api.serve(Todos, ({ list }, principal, self) => {
		if (list !== "family") throw forbidden("This list is not shared");
		const store = self.get(TodoStore, { list });
		if (principal !== "owner" && principal !== hostPrincipal) {
			return { kind: "viewer", rows: store.rows };
		}
		return {
			kind: "editor",
			rows: store.rows,
			add: ({ text }, ctx) => {
				if (text.trim().length === 0) throw invalid("args", "A todo needs text");
				return store.add({ text }, ctx);
			},
		};
	});
}
```

Here principals are the strings `"owner"` and `"guest"`, assigned by
trusted application code. The built-in `hostPrincipal` can also edit.
`principalKey` maps identity to record identity. Real applications should use
stable identity, connection provenance, and grant revision, not display names.

<!-- example:05-call -->
```ts
const host = createHost({ principalKey: (principal) => String(principal) });
host.serve(TodoStore, todoFactory);
serveViews(host);
const owner = host.get(Todos, { list: "family" }, { principal: "owner" });
const guest = host.get(Todos, { list: "family" }, { principal: "guest" });
await Promise.all([owner.ready, guest.ready]);
assert.equal(owner.kind, "editor");
assert.equal(guest.kind, "viewer");
await host.root((ctx) => owner.add({ text: "Buy milk" }, ctx), { principal: "owner" });
assert.deepEqual(guest.rows.value, [{ text: "Buy milk", done: false }]);
await assert.rejects(guest.add({ text: "Not allowed" }), (error) => isChordError(error, "not_in_variant"));
await assert.rejects(owner.add({ text: " " }), (error) => isChordError(error, "invalid"));
```

The owner gets `editor`; the guest gets `viewer`. Both see the same milk
todo. Calling the guest's `add` rejects with `not_in_variant`, even though
TypeScript exposes methods from all variants on a handle. Whitespace-only text
rejects with `invalid`: it is a string, as the schema demands, but it breaks a
rule only the method knows. Use `invalid` for bad input and `forbidden` only
for callers who may not do something.

> **Why:** A variant is not all of authorization. The factory checks which
> list may be opened; the method checks the operation's arguments. Production
> code must also enforce grants that can change. Use
> `host.invalidatePrincipal(match)` to revoke matching records; held handles
> become `gone`. A UI watches `onStatus` and gets a new handle when appropriate.
> Guest-provided names or message text must never establish identity.

## 6. Reach the list from another process

A browser cannot call a host-only contract. `remote` contracts describe only
schema-checked state and methods that can travel as JSON. Our `Todos` view is
remote; the underlying `TodoStore` and database stay local.

A **link** carries ordered messages between hosts. A memory link runs both ends
in one test process, but uses the remote protocol. The accepting host stamps
the caller's principal from its authenticator, not from method arguments or a
client's claimed identity.

<!-- example:06 -->
```ts
const server = createHost({ name: "server" });
server.serve(TodoStore, todoFactory);
serveViews(server);
const [down, up] = memoryLinkPair();
server.accept(down, { principal: "owner", kind: "client" });
const browser = createHost({ name: "browser", kind: "client", upstream: up });
const todos = browser.get(Todos, { list: "family" }, { at: "server" });
const hydrated = Promise.withResolvers<void>();
const updated = Promise.withResolvers<void>();
const stop = todos.rows.subscribe((rows) => {
	if (rows !== undefined) hydrated.resolve();
	if (rows?.length === 1) updated.resolve();
});
await todos.ready;
await hydrated.promise;
assert.deepEqual(todos.rows.value, []);
await browser.root((ctx) => todos.add({ text: "Buy milk" }, ctx));
await updated.promise;
assert.deepEqual(todos.rows.value, [{ text: "Buy milk", done: false }]);
// Deliberately bypass TypeScript to simulate a malformed caller.
await assert.rejects(todos.add({ text: 123 } as never), (error) => isChordError(error, "invalid"));
stop();
assert.equal(todos.rows.value, undefined);
todos.release();
```

The browser sees an empty snapshot, then the new milk todo. `ready` means
the remote handle has bound to a live object; it does **not** guarantee that
subscribed state has arrived. That is why we separately await `hydrated` and
`updated`. A remote readable starts at `undefined` and returns to
`undefined` when its last subscriber leaves.

What crosses the wire: the input and consumer's contract description, the
provider's shape (variant and members), method arguments and results, and
subscribed state. State starts with a **snapshot**, the whole current value;
subsequent **deltas** describe changes. Rebinds and reloads can send a
`reset`, a fresh whole value. Functions, resource connections, and cell
instances do not cross the wire.

The deliberate bad argument rejects with `invalid`. Remote arguments,
results, and outgoing state are validated at the provider boundary. Local
methods do not get per-call schema validation; they still need app-level checks.
`dev: true` additionally checks cell writes while developing.

> **Tip:** Replace `memoryLinkPair` with `webSocketLink` for a WebSocket or
> `ipcLink` for a child-process IPC channel; object contracts stay the same.
> Those adapters wrap an existing connection, not an authenticator. Configure
> `accept` with an authenticated principal. A browser is `kind: "client"`;
> a trusted child host is accepted with `kind: "host"` and its configured name.

## 7. React to changes and run background work

Not all work comes from method calls. The app may update an activity indicator
when rows change, or run a background reminder. A **listener** reacts to an
observable source. A **task** is background execution owned by an object,
which is aborted when the object is disposed or its code is reloaded.

Our activity object mirrors the row count. Its task inserts a sample todo,
then waits for shutdown. The promises make those events deterministic in a
test; they are not stored application state.

<!-- example:07 -->
```ts
const Activity = local("tutorial.activity", {
	version: 1,
	input: Type.Object({}),
	members: { seen: Type.Number() },
});
const host = createHost();
host.serve(TodoStore, todoFactory);
const observed = Promise.withResolvers<void>();
const seeded = Promise.withResolvers<void>();
const stopped = Promise.withResolvers<void>();
host.serve(Activity, (_input, _principal, self) => {
	const todos = self.get(TodoStore, { list: "family" });
	const state = self.state({ seen: cell(Type.Number(), 0) });
	self.listen({
		rows: listener(todos.rows, (rows, ctx) => {
			state.seen.replace(ctx, rows?.length ?? 0);
			if (rows?.length === 1) observed.resolve();
		}),
	});
	self.tasks({
		seed: async (ctx) => {
			await todos.add({ text: "Review the list" }, ctx);
			seeded.resolve();
			await new Promise<void>((resolve) => {
				if (ctx.signal.aborted) resolve();
				else ctx.signal.addEventListener("abort", () => resolve(), { once: true });
			});
			stopped.resolve();
		},
	});
	return { seen: state.seen };
});
const activity = host.get(Activity, {});
await activity.ready;
await Promise.all([seeded.promise, observed.promise]);
assert.equal(activity.seen.value, 1);
activity.release();
await stopped.promise;
```

The final `seen` is `1`. Each listener event receives a fresh root's
`ctx`; its write belongs to that short call tree. A task is not one enormous
root: Chord method calls made with its task context start fresh short roots.
We pass that context into `todos.add` so cancellation follows the task.
Releasing the activity handle aborts its task and resolves `stopped`.

Listeners can also subscribe to a resource's event stream with
`listener(resource, select, fn)`: `select` gets the opened resource and
returns something with `subscribe`. Kept subscriptions survive reload while
the resource and selector remain unchanged; the callback switches to new code.
A selector that captures changing configuration should get a new listener name.

> **Why:** Do not wait for a person, sleep for minutes, or run an endless loop
> inside a method. That pins a root and can block state migration. Store a
> pending request in a cell and answer in another call, or use a task that obeys
> `ctx.signal`. Never retain a completed method's `ctx` for background work.

## 8. Package features as plugins

Now a plugin can contribute a menu action without editing a central switch.
A **registry** is a named table of contributions. A **facet** declares what a
plugin serves on one kind of host. A plugin can have server, worker, and browser
facets, each installing that part of the feature.

Registrations belong to eager objects: **eager** means the host creates and
holds the object at startup, even if no screen asks for it. That keeps our menu
contribution present. Lazy objects still activate only when held.

<!-- example:08 -->
```ts
const Actions = defineRegistry<(ctx: Ctx) => Promise<number>>("tutorial.actions");
const Menu = local("tutorial.menu", { version: 1, input: Type.Object({}) });
let click: (() => Promise<number>) | undefined;
const storeFacet: Facet = {
	name: "todo-store",
	...defineFacet((api) => api.serve(TodoStore, todoFactory)),
};
const menuFacet: Facet = {
	name: "todo-menu",
	...defineFacet(
		(api) => {
			api.serve(
				Menu,
				(_input, _principal, self) => {
					const todos = self.get(TodoStore, { list: "family" });
					self.register(Actions, {
						addSample: async (ctx) => {
							await todos.add({ text: "Try plugins" }, ctx);
							return todos.openCount.value!;
						},
					});
					return {};
				},
				{ eager: true },
			);
			click = () => api.root((ctx) => api.registry(Actions).get("addSample", ctx)!(ctx));
		},
		{ uses: [TodoStore] },
	),
};
const host = createHost();
await host.load([menuFacet, storeFacet], { awaitEager: false });
await host.ready();
assert.equal(await click!(), 1);
assert.equal(host.registry(Actions).table().size, 1);
```

Clicking returns `1`, and the registry has one entry. The menu's dependency
can come from a later facet in the load batch: `load` installs the whole
batch before waiting for eager activation. The facet declares `uses` so
reload can also check the contract it consumes.

The facet API supplies `serve`, `name`, `root`, and `registry`.
Our ordinary UI callback uses its saved `api.root`, not a process-global
host. Looking up a registry entry with `ctx` uses the table belonging to that
root's code version. Without `ctx`, lookup uses the current table. Duplicate
keys fail by default; `subscribe` can bridge tables to an imperative consumer.

Normally use `await host.load(facets)` (or `await host.install(facet)`),
which waits for those eager objects. This example explicitly defers that barrier
with `awaitEager: false`, then awaits `host.ready()`. That waits for a
snapshot of the host's eager holds, not for task completion or later loads.
Failures reject the readiness promise; abandoning startup requires closing the
host, because installation is not a rollback transaction.

> **Tip:** Use deferred readiness only when needed. A worker may have to await
> an independent local bootstrap handle, announce control readiness so its
> parent admits its link, and only then await `host.ready()`. Waiting for
> upstream-dependent eager objects before admission would deadlock.

For real plugin files, default-export `defineFacet(...)`. Node hosts configure
`createHost({ loader: nodeLoader })`, with `nodeLoader` imported from
`@earendil-works/chord/node`, then pass module URLs to `load` and `reload`.
The in-memory facet objects here avoid filesystem setup. Built-in facets are
trusted in-process code, not a sandbox; the current Node loader keeps old module
copies in memory, so repeated loading has that limitation.

## 9. Change running code without losing the list

A handle is useful precisely because callers keep it while implementations
change. An **epoch** identifies one committed set of code and registry tables.
A root keeps the epoch it started with. New roots use the latest one.

### Compatible code change: no waiting

Give the same named facet a new factory. It changes the label but keeps the
cell declarations. This test deliberately pauses one caller to show what an
old root sees; application methods should not pause like this.

<!-- example:09-compatible -->
```ts
const host = createHost();
const facet = (label: string): Facet => ({
	name: "todos",
	setup: (api) =>
		api.serve(TodoStore, (input, principal, self) => ({
			...todoFactory(input, principal, self),
			label: () => label,
		})),
});
await host.load([facet("Original")]);
const todos = host.get(TodoStore, { list: "family" });
await todos.add({ text: "Buy milk" });
const entered = Promise.withResolvers<void>();
const resume = Promise.withResolvers<void>();
const oldRoot = host.root(async (ctx) => {
	const first = await todos.label(null, ctx);
	entered.resolve();
	await resume.promise; // Test-only pause: pin an old caller during reload.
	return [first, await todos.label(null, ctx)];
});
await entered.promise;
const compatible = await host.reload([facet("Updated")]);
assert.deepEqual(compatible.gated, []);
assert.equal(await todos.label(null), "Updated");
resume.resolve();
assert.deepEqual(await oldRoot, ["Original", "Original"]);
assert.equal(todos.rows.value?.[0]?.text, "Buy milk");
```

Reload commits while the old root is paused: `gated` is empty. New calls see
`"Updated"`; the resumed old root sees `"Original"` twice. The milk row
survives. Compatible code changes do not wait for that old root to finish.

### State change: bump its version and migrate

Suppose a new policy converts existing todo text to uppercase. The schema is
unchanged, but the data's meaning changes. We still bump the **state version**.
This version belongs to stored cells, independently of the contract version.
A **migration** converts an old cell value to the new representation.

<!-- example:09-migrate -->
```ts
const events: string[] = [];
const stopEvents = todos.rows.events((event) => events.push(event.type));
const migrated = await host.reload([
	{
		name: "todos",
		setup: (api) =>
			api.serve(TodoStore, todoFactory, {
				state: {
					version: 2,
					migrate: {
						rows: (old, from) => {
							assert.equal(from, 1);
							return (old as Static<typeof Rows>).map((todo) => ({ ...todo, text: todo.text.toUpperCase() }));
						},
					},
				},
			}),
	},
]);
assert.equal(migrated.gated.length, 1);
assert.deepEqual(todos.rows.value, [{ text: "BUY MILK", done: false }]);
assert.deepEqual(events, ["snap", "reset"]);
stopEvents();
```

The migration receives the old rows and their state version, `1`. It returns
new rows; the handle now reads `[{ text: "BUY MILK", done: false }]`.
Subscribers get a `reset` event containing the migrated value. The event
assertion sees an initial `snap`, then that `reset`.
One record is gated. A **gate** waits for calls already inside that record to
finish before migrating a private copy, validating it, and committing. Old
roots that had not entered it cannot later use old code over migrated data:
they get `upgrade_conflict` and should retry in a new root.

Changing a cell's schema also requires a state-version bump and a migration
whose result fits the new schema. A change of meaning with the same schema,
like this example, cannot be detected automatically. Real migrations must
handle each stored version they support, not assume every installation is
exactly one version behind.

### Contract change: keep an adapter for old callers

Rename `label` to `heading`. That is a breaking contract change, so use
contract version 2. The provider's `accepts[1]` adapter builds the behavior
that version-1 consumers still expect.

<!-- example:09-contract -->
```ts
// Remove label from the new provider's contract: it is now called heading.
const { label: _label, ...members } = TodoStore.def.members;
const RenamedStore = local("tutorial.todos", {
	version: 2,
	input: TodoStore.def.input,
	members: { ...members, heading: method(Type.Null(), Type.String()) },
});
await host.reload([
	{
		name: "todos",
		setup: (api) =>
			api.serve(
				RenamedStore,
				(input, principal, self) => {
					const { label, ...behavior } = todoFactory(input, principal, self);
					return { ...behavior, heading: label };
				},
				{
					state: { version: 2 },
					accepts: {
						1: (current) => ({ ...current, label: current.heading }),
					},
				},
			),
	},
]);
assert.equal(await todos.label(null), "Todos for family");
const newer = host.get(RenamedStore, { list: "family" });
assert.equal(await newer.heading(null), "Todos for family");
assert.equal(todos.rows.value?.[0]?.text, "BUY MILK");
```

The old handle's `label` and the new handle's `heading` both return
`"Todos for family"`. Both still reach the migrated rows. The adapter maps
behaviors, not handles; forwarding the existing method preserves its context.
We keep state version 2 here so this code-only change does not repeat migration.

> **Why:** Contract versions protect callers; state versions protect stored
> data; resource revisions control reopening. Do not use one number for all
> three. Additive compatible contracts can keep their version; breaking shape
> or meaning changes need a contract bump and adapters for old consumers.
> Reload prepares candidates first; preparation failure leaves the old code
> running. A migration gate that misses its deadline aborts rather than
> switching data underneath active old code.

## 10. Test the objects, not a whole deployment

Most behavior needs only a bare host. Use real factories for state tests, and a
fake facet when you want to test delegation without a real database or service.
Here the fake records what the editing view sends to the store.

<!-- example:10 -->
```ts
const host = createHost({ dev: true });
const received: string[] = [];
const fake: Facet = {
	name: "fake-store",
	...defineFacet((api: FacetApi) => {
		api.serve(TodoStore, (input, principal, self) => ({
			...todoFactory(input, principal, self),
			add: ({ text }) => {
				received.push(text);
				return null;
			},
		}));
	}),
};
await host.load([fake]);
serveViews(host);
const owner = host.get(Todos, { list: "family" }, { principal: "owner" });
await owner.add({ text: "Test delegation" });
assert.deepEqual(received, ["Test delegation"]);
await assert.rejects(owner.add({ text: "" }), (error) => isChordError(error, "invalid"));
owner.release();
await assert.rejects(owner.add({ text: "Too late" }), (error) => isChordError(error, "released"));
```

The fake received `["Test delegation"]`. Empty text failed before reaching
the fake. The released handle rejects further calls with `released`.
`isChordError(error, code)` checks a stable error code; avoid testing only a
message's wording.

Our other tests exercise the real cells (section 3), resource cleanup (4),
principal variants (5), a client over a memory link (6), and callers held through
reload (9). For remote state tests, await the value you need, not just
`handle.ready`. Always unsubscribe and close hosts; leaked holds can hide
lifetime bugs or leave background tasks running.

> **Tip:** A fake must honor the contract it serves. This fake delegates all
> ordinary members to `todoFactory` and replaces only `add`; it deliberately
> records calls rather than updating rows. Do not confuse that with persistence.

## 11. Keep these habits

A temporary call handle should not accidentally become a permanent hold. A
screen should not lose its data merely because a button click finishes. Use
`ctx.get` for the first lifetime and `host.get` for the second.

<!-- example:11 -->
```ts
const host = createHost();
host.serve(TodoStore, todoFactory);
const screen = host.get(TodoStore, { list: "family" });
await screen.ready;
await host.root(async (ctx) => {
	const temporary = ctx.get(TodoStore, { list: "family" });
	await temporary.add({ text: "Keep roots short" }, ctx);
}); // The temporary handle is released here; screen still holds the store.
assert.equal(screen.openCount.value, 1);
screen.release(); // No hold remains; without persistence, disposal loses these rows.
```

The screen still sees count `1` after the root finishes, because it owns a
separate hold. When the screen releases, no hold remains. This tutorial's cells
are in memory: reload preserves a live record, but disposal or process restart
loses its rows. Real persistence belongs in a database resource, with an
explicit load/save policy.

### Checklist and common mistakes

- Keep reloadable state in cells, not closure variables: factories rerun.
- Change drafts, not published values: mutation outside cells bypasses updates.
- Use `change` for field edits and `replace` for owned snapshots: replacing
  can erase fields your code does not know about.
- Declare dependencies in a synchronous factory, not during methods: activation
  and reload need a complete declaration list.
- Use `ctx.get` for temporary method dependencies: their holds end with the call.
- Pass `ctx` into nested calls: cancellation and code versions must stay together.
- Keep roots short and tasks cancellable: migration and shutdown need work to settle.
- Check grants and arguments, not just variants: available methods are not a full policy.
- Stamp principals at trusted ingress, not from client payloads: names are not identities.
- Subscribe before expecting remote state: readiness is not snapshot hydration.
- Release handles and unsubscribe: otherwise unused objects remain held or observed.
- Bump state versions, contract versions, and resource revisions for their own changes:
  each protects a different boundary.
- Await eager readiness before reporting startup success: declared is not yet live.
- Keep hold dependencies acyclic: an object cannot wait for itself through another object.

### Imports and running the examples

These are the shared imports from `test/tutorial.test.ts`. The relative
path is correct from that test directory; applications import the same names
from `@earendil-works/chord`. `assert` expresses expected values; `it` and
`onTestFinished` come from the test runner; `readFileSync` is used by the
tutorial's source-matching check, not by the application.

<!-- example:imports -->
```ts
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { type Static, Type } from "typebox";
import { it, onTestFinished } from "vitest";
import {
	type Ctx,
	cell,
	createHost,
	defineFacet,
	defineRegistry,
	derivation,
	type Facet,
	type FacetApi,
	type Factory,
	forbidden,
	type Host,
	hostPrincipal,
	invalid,
	isChordError,
	listener,
	local,
	memoryLinkPair,
	method,
	opaque,
	remote,
	resource,
} from "../src/index.ts";
```

From `packages/chord`, run:

```sh
node ../../node_modules/vitest/dist/cli.js --run test/tutorial.test.ts
```

There is one test per numbered section. Every TypeScript block is matched
against its runnable source, so changing either copy without the other fails a
test. The test harness adds teardown and drift checks; it never uses a real
database, network service, or provider API.

Next read [the usage guide](guide.md) for the API reference and
[the specification](spec.md) for compatibility, lifetime, and reload
rules, including its known limitations. If a reference disagrees with
`src`, the current implementation wins.

---

## Delta Tracking

Chord Delta produces immutable JSON revisions and exact operation batches for
ordered replicas. Import it from `@earendil-works/chord/delta`.

Immutability is an ownership contract. Nothing is frozen or defensively copied,
so an illegal mutation is not detected. It silently corrupts state.

```ts
import { applyImmutable, applyImmutableBatches, track } from "@earendil-works/chord/delta";

const initial = { output: "", entries: [] as { id: number }[] };
const tracker = track(initial); // `initial` is transferred: never mutate it again

const change = tracker.beginChange();
change.state.output += "done\n"; // the draft is mutable only while the change is open
change.state.entries.push({ id: 1 }); // placed values are cloned; the caller keeps its object
const prepared = change.prepare(); // draft handles are unusable from here on

// tracker.value, prepared.base, prepared.value, and prepared.ops (including paths
// and payloads) are immutable by contract.
tracker.adopt(prepared); // tracker.value === prepared.value

// Shares containers with prepared.base and the op payloads: never mutate it either.
const replica = applyImmutable(prepared.base, prepared.ops);
```

## Mutation rights

| Value | May it be mutated? |
| --- | --- |
| Root passed to `track()`, `prepareReplace()`, `replicatedState()`, or `replace()` | No. Ownership moved to the tracker. |
| `change.state` and handles read from it | Yes, only while that change is open. After `prepare()`, `abort()`, or another adoption, every use throws. Writes through a handle whose element was removed from the draft are ignored. |
| External value after assigning or inserting it into a draft | Yes. The draft stored a validated clone. |
| `tracker.value`, `prepared.base`, retained older revisions | No. |
| `prepared.value`, `prepared.ops`, op tuples, paths, permutations, payloads | No. Payloads may be the same objects as parts of `prepared.value`. |
| `applyImmutable()` / `applyImmutableBatches()` inputs and result | No. The result shares containers with both inputs. |
| Values from replicated state and cells (`value`, listener values, in-process handles) | No. In-process consumers may share the provider's containers. |
| Mutable replica passed to `apply()` | Only through `apply()`, with batches it owns exclusively. Code that edits it between batches breaks convergence. |
| Batch passed to `apply()` | Consumed. `apply()` adopts payload containers into the replica. Use a detached copy for exactly one replica and never touch it again. |

## Replaying batches

Immutable replay is the preferred in-process path. One batch can fan out to any
number of immutable replicas:

```ts
let replica = tracker.value; // shared with authority; never mutated
// For each adopted batch, in order:
replica = applyImmutable(replica, prepared.ops); // replica must equal prepared.base
```

When only the final result of an ordered backlog is needed, replay its batches
without concatenating their operations. One copy-on-write scope is shared across
the complete call, so no intermediate revision is exposed or safe to retain:

```ts
replica = applyImmutableBatches(
  replica,
  queuedFrames.map((frame) => frame.ops),
);
```

Use separate `applyImmutable()` calls when every intermediate revision is
published or retained.

Mutable replay needs a detached starting root and a detached copy of every batch
for every replica. Never apply one in-memory batch to two mutable replicas:

```ts
import { apply } from "@earendil-works/chord/delta";

const detach = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T;

let replica = detach(tracker.value); // exclusively owned starting root
// For each adopted batch, in order:
replica = apply(replica, detach(prepared.ops)); // fresh copy for this replica only
// Only apply() may change `replica`; do not edit it in application code.
```

Parsing a separately serialized message per replica is also a valid detachment.
`decode()` does not copy payloads, so decoding one in-memory `WireOp[]` for two
mutable replicas makes them alias each other.

## Do and don't

- Do build a fresh root and then transfer it; validate untrusted roots at your ingestion boundary.
- Do keep structural sharing between revisions, for example `replace(ctx, { ...state.value, changed })`.
- Do clone or serialize before handing any published value to code that may mutate it.
- Do settle every change with `prepare()` or `abort()`.
- Don't reuse one container at two places in a transferred root.
- Don't mutate anything the tracker owns, published, or received from a batch.
- Don't keep draft handles past their change or place a settled handle.
- Don't infer meaning from op shape. Only the resulting value is contractual.

## Roots and placements

Full roots are trusted. `track()` and `prepareReplace()` take ownership in O(1)
and never walk the tree. Roots must be alias-free, acyclic strict JSON: dense
plain arrays, plain or null-prototype objects with enumerable own data
properties, strings, booleans, finite numbers, and `null`. Violations have
unspecified behavior. For example, a container shared by two keys can make
`prepared.value` diverge from what replicas compute from `prepared.ops`.

Draft placements are copied, and that copy walk also validates. Placements come
from property writes, index writes, `push`, `unshift`, `splice`, `fill`, and
`copyWithin`. A non-strict value throws `TypeError` before the draft changes;
for example, `push(valid, invalid)` inserts nothing. Rejected values include:
cycles, accessors (never invoked), symbol keys, class instances, sparse or
non-plain arrays, functions, bigint, `NaN`, infinities, and `undefined`.
Null-prototype objects are accepted and preserved. Placing a draft handle clones
its current content. Placing one value at several paths yields independent
containers.

`undefined` rules:

- `draft.obj.key = undefined` deletes `key`.
- `arr[i] = undefined`, `push(undefined)`, `unshift`, `splice`, and `fill` with `undefined` throw.
- `undefined` nested anywhere inside a placed object or array throws. It is not dropped like `JSON.stringify` does.

Arrays stay dense. Writing past the next index and deleting an element throw.
Growing `length` inserts `null`; shrinking it removes elements.

## Lifecycle

`tracker.value` is the latest adopted revision. `beginChange()` opens an overlay
draft over it and never modifies it. A draft may stay open across `await`.
`prepare()` materializes the candidate and ops and does not change authority.
`adopt()` checks the preparation and swaps the root pointer.

Several changes may be open or prepared from one revision. Adopting one makes all
others stale: open drafts become unusable and their `prepare()` throws, and
prepared competitors are rejected by `adopt()`. `adopt()` also rejects foreign,
aborted, and already consumed preparations. `Change.abort()` or
`Prepared.abort()` after `prepare()` prevents adoption. The candidate stays
readable.

No-op batches:

- Empty `ops` means `prepared.value === prepared.base`. Writes restored to their original value and deeply equal container assignments usually normalize to empty.
- Equality ignores key order and prototype. A deeply equal assignment keeps the previous revision's order and prototype, even if the draft showed the new ones.
- Structural array edits may emit a nonempty exact batch even when the result is deeply equal.
- Adopting a no-op still advances `tracker.revision` and stales competitors. Replicated state does not publish no-ops.

`prepareReplace(value)` is a whole-root operation, not a diff. If `value` is
deeply equal to the current root, `ops` is empty and the current root is kept
(the comparison may traverse both trees). Otherwise `ops` is `[["r", value]]`
and `prepared.value === value`, so replicas receive the complete root.

Array mutators: `push`, `pop`, `shift`, `unshift`, `splice`, `reverse`, `sort`,
`fill`, and `copyWithin`. Held handles follow elements through reindexing.

## Operations

Paths contain object keys and non-negative integer array indices.

| Tuple | Meaning |
| --- | --- |
| `["r", value]` | Replace the complete value. |
| `["s", path, value]` | Set an object property or array element. |
| `["d", path]` | Delete an object property or remove an array element. |
| `["a", path, text]` | Append to a string. |
| `["t", path, count]` | Remove `count` UTF-16 code units from a string's front. |
| `["p", path, index, remove, items]` | Splice an array. |
| `["m", path, permutation]` | Reorder an array: `new[i] = old[permutation[i]]`. |

Batches are exact but not canonical. The same change may use different tuples,
and large edit sets may fold into a region splice, an ancestor `s`, or `r`.

Reserved keys: the tracker never emits `__proto__`, `constructor`, or
`prototype` as a path segment. A mutation at or below such a key is folded into a
set of the nearest safe ancestor, or `r` at the root. `apply()`, `applyImmutable()`, `applyImmutableBatches()`, and `decoder()` reject
those segments with `UnsafePathError`.
The appliers write values as own data properties, never through a prototype setter.
Appliers check op shape and path safety but not payload strictness. Chord's
remote state applies batches decoded from JSON frames, so their payloads are strict
JSON; validate payloads of batches from any other source.

`encoder()` interns repeated paths into `WireOp` tuples; `decoder()` validates
and restores `Op` tuples. Use one encoder/decoder pair per ordered state stream.
Path IDs span batches and an `r` resets both dictionaries. After a decode or
apply error, discard the decoder and replica and recover from a later `r`.

## Limits and footguns

- No freezing. Mutating any immutable value corrupts state silently.
- In-process sharing: local handles, cell subscribers, and `replicatedState` subscribers receive the provider's containers. A consumer mutation corrupts authority and makes remote replicas diverge.
- A change inside a large flat array copies that array's pointer storage for the new revision.
- Placement validation costs time and memory on bulk inserts. In a benchmark unshifting 100k three-field objects, it added about 19 ms and 20 MiB of transient heap.
- Draft reads go through proxies. In one measurement, 20,000 hot nested reads took about 9 ms through the tracker versus 0.08 ms on raw objects; compare with `node --expose-gc packages/chord/test/delta-traversal.bench.ts --quick`.
- External proxies as placements, argument coercion callbacks that mutate the draft, non-primitive array indices, and non-numeric comparator results are out of contract. So are sort comparators that mutate, prepare, abort, or adopt. Behavior is unspecified.
- Object identity is not replicated. Each path is an independent value placement.
- One tracker is one revision sequence. Delivery order and persistence belong to the surrounding protocol.
