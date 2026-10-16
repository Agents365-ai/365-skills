# Chord: Typed Host Runtime
Source: `packages/chord/README.md`, `docs/guide.md`, `docs/spec.md`, `docs/tutorial.md`, `src/delta/README.md`
`@earendil-works/chord` is an application-neutral runtime used by `pi-durable`, but not by the Pi coding agent. It is not covered by the Pi user docs. Release 1.2.0 replaced the facet and service runtime with a typed host runtime (contracts, hosts, links, hot reload) and removed `PLANNING.md`, the `./bundler` export, and the `pi-client`/`pi-protocol`/`pi-server` packages. The specification and the guide describe the current runtime; the tutorial is a worked example.

---

> **Auto-built from individual doc pages.**
> Sources: https://raw.githubusercontent.com/earendil-works/pi/main/packages/chord/README.md, https://raw.githubusercontent.com/earendil-works/pi/main/packages/chord/docs/guide.md, https://raw.githubusercontent.com/earendil-works/pi/main/packages/chord/docs/spec.md, https://raw.githubusercontent.com/earendil-works/pi/main/packages/chord/docs/tutorial.md, https://raw.githubusercontent.com/earendil-works/pi/main/packages/chord/src/delta/README.md

## Overview

Chord builds applications out of **objects** that live in several processes (a server, workers, browser tabs) and can be **hot reloaded** while they run.

- An **object** is state plus code at an address. It is created on demand and lives while someone references it.
- Everyone gets a **reference**, never the object. References work the same locally and across processes, and survive reloads.
- Every object knows its **principal**: an owner and a guest get different objects, with different methods.
- **State** is observable JSON. Remote viewers get a snapshot followed by deltas.
- **Hot reload** swaps code while it runs. Work in flight finishes on the code it started with, state is kept, and incompatible changes migrate at a safe point.

Contracts are runtime values described with [TypeBox](https://github.com/sinclairzx81/typebox) schemas. Hosts exchange JSON frames over links: in memory, a Node IPC channel, or a WebSocket.

## Entry points

| Import | Contents | Runs in |
|--------|----------|---------|
| `@earendil-works/chord` | Contracts (`local`, `remote`, `method`, `opaque`), declarations (through the factory's `self`: `state`, `derive`, `resource`, `on`, `task`), hosts (`createHost`, `defineFacet`, `defineRegistry`), links (`memoryLinkPair`, `ipcLink`, `webSocketLink`, `acceptWebSockets`), errors (`ChordError`, `isChordError`, `forbidden`, `invalid`). Also the shared base: `Context`, `JsonValue`, `JsonRepresentation`, `Draft`, `copyJson`, `isJsonValue`, and `replicatedState` with its types. | Node and browsers |
| `@earendil-works/chord/node` | Child host processes: `createHostManager`, `forkDriver`, `childControl`, `processLock`; the facet module loader `nodeLoader`. | Node |
| `@earendil-works/chord/context` | Explicit cancellation and invocation values: `BACKGROUND_CONTEXT`, `withCancel`, `withAbortSignal`, `withoutAbortSignal`, `withContextValue`, `awaitWithContext`. | Node and browsers |
| `@earendil-works/chord/delta` | The transactional JSON tracker, structural diff, immutable apply, and the wire encoder/decoder for operation batches. | Node and browsers |
| `@earendil-works/chord/output` | Bounded output streams and paced progress: `OutputBuffer` (head or tail window of a stream, `OutputLimits`, `OutputSkip`), `boundOutput`, `sanitizeOutput`, `utf8ByteLength`, and `Progress` (adaptive commits of a changing value). | Node and browsers |

## Quick start

```ts
import { Type } from "typebox";
import { createHost, hostNamed, method, remote } from "@earendil-works/chord";

// contract.ts: shared by provider and consumers
export const Counter = remote("demo.counter", {
	version: 1,
	input: Type.Object({ name: Type.String() }),
	host: hostNamed("server"), // where its objects live; callers never name a host
	variants: {
		default: {
			state: { count: Type.Number() },
			methods: { increment: method(Type.Object({ by: Type.Number() })) },
		},
	},
});

const host = createHost({ name: "server", self: { kind: "server" } });

host.serve(Counter, ({ name }, _principal, self) => {
	const count = self.state("count", Type.Number(), 0);
	return {
		variant: "default",
		count,
		increment: async ({ by }, ctx) => {
			count.change(ctx, (n) => n + by);
		},
	};
});

await host.root(async (ctx) => {
	const clicks = await ctx.get(Counter, { name: "clicks" }); // ready, with its state; released when this root ends
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
throws, the original value and sequence remain unchanged. Draft references become
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

- An **object type** is declared by a contract: a name, an input (the object's address) and members. A plugin's
  **facet** (its code for one host: server, worker, browser) serves object types.
- An **object** is one instance of an object type: state plus code at an address. It is created on demand and lives
  while someone references it.
- Everyone gets a **reference**, never the object. References work the same locally and across processes, and survive reloads.
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
- [References](#references)
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
import { createHost, method, remote } from "@earendil-works/chord";

// contract.ts: shared by provider and consumers
export const Counter = remote("demo.counter", {
	version: 1,
	input: Type.Object({ name: Type.String() }),
	variants: {
		default: {
			state: { count: Type.Number() },
			methods: { increment: method(Type.Object({ by: Type.Number() })) },
		},
	},
});

const host = createHost({ name: "server", self: { kind: "server" } });

host.serve(Counter, ({ name }, _principal, self) => {
	const count = self.state("count", Type.Number(), 0);
	return {
		variant: "default",
		count,
		increment: async ({ by }, ctx) => {
			count.change(ctx, (n) => n + by);
		},
	};
});

await host.root(async (ctx) => {
	const clicks = await ctx.get(Counter, { name: "clicks" });  // ready, with its state; released when this root ends
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
	host: hostFamily("session:", "session"),  // lives on `session:S1` for `{ session: "S1", … }`
	variants: {
		viewer: {
			state: { view: ConversationViewSchema },
		},
		participant: {
			state: { view: ConversationViewSchema },
			methods: {
				send: method(SendInputSchema, Type.Object({ submissionId: Type.Number() })),
				stop: method(),  // no arguments, no result: `chat.stop(ctx)`
			},
		},
	},
});
```

**Where a remote type lives** is part of its contract, so no caller names a host:

- `host: hostNamed("server")`: every object lives on the host named `server`.
- `host: hostFamily("session:", "session")`: an object lives on `session:` + its input's `session` field, a required
  string. TypeScript checks the field name against the input.

A `get` normalizes the input (defaults count), resolves the host, and acquires the object here if that is this host,
otherwise over the link to it. `serve` refuses a type whose placement does not include the serving host, so a misplaced
type fails at startup or at the reload that adds it. The host that gets a hold checks that its own contract places the
input on itself, and a relay checks the hold's target against its contract token: a client never chooses where an
object lives. The placement is part of the description and the fingerprint: moving a type is a breaking change, and
references to it get `upgrade_required`.

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
host.serve(Type, (input, principal, self) => implementation, options);
```

- The **factory** runs synchronously. It declares what the object needs and returns its implementation: methods and state members, plus `variant` for remote types. Returning a promise throws.
- There is one **object** per `(type, input, principal)`. It holds the object's state, resources and references, and survives reloads. Only the implementation is replaced.
- **Options:**
  - `accepts`: adapters for consumers built against older contract versions;
  - `lifetime`: `"referenced"` (default) creates the object at its first `get` and disposes it after the last reference
    is released; `"host"` creates it when the plugin loads and keeps it until the host closes (see [Lifetime](#lifetime));
  - `linger`: how long to keep a referenced object after the last reference is released.

## Declarations

A reload runs the factory again over the same object. Declarations that keep something across a reload have a **name**: the new code's `status` cell is the old code's `status` cell, with its value. Derivations and tasks hold nothing across a reload and have no name.

```ts
host.serve(StatusStore, ({ session }, _host, self) => {
	const status = self.state("status", StatusSchema, { running: false, tasks: 0 });
	const errors = self.state("errors", Type.Array(Type.String()), []);
	const catalog = self.get(Catalog, {});
	const db = self.resource("db", {
		version: 1,
		open: async ({ signal }) => openSqlite(statusPath(session), { signal }),
		close: async (db) => db.close(),
	});
	self.on("catalogChanges", catalog.rows, (rows, ctx) => errors.replace(ctx, checkRows(rows)));
	self.task(async (ctx) => {
		while (!ctx.signal.aborted) {
			await sleep(10_000, ctx.signal);
			await db.value.run("INSERT INTO history VALUES (?)", [JSON.stringify(status.value)]);
		}
	});
	const summary = self.derive([status, errors], (s, e) => ({ ...s, failing: e.length > 0 }));
	return { summary, report: reportMethod(status) };  // exposed state is what the implementation returns
});
```

| Declaration | What it is | On reload |
| --- | --- | --- |
| `self.state(name, schema, initial \| { init }, { version?, migrate? })` | an observable JSON cell; the schema is required | same cell and value (`init` does not run); migrated when its version rises |
| `self.get(Type, input, { at? })` | a reference to another object; its identity is the address | kept if declared again, otherwise released |
| `self.resource(name, { version, deps?, exclusive?, open, close? })` | a connection, watch, socket, port | kept; reopened only if `version`, `deps` or `exclusive` change |
| `self.on(name, source, handler)` or `self.on(name, source, select, handler)` | reacts to state or to an event source | the same subscription, with the new handler, as long as the source and `select` are unchanged |
| `self.task(async (ctx) => ...)` | long-running background work | the old run is aborted through `ctx.signal`; the new code starts once it finished (at most `taskStopDeadline`, default 5 s) |
| `self.derive(sources, fn)` | live projection of state; `fn` is synchronous | a new derivation, computed when the reload commits |
| `self.register(Registry, { key: value })` | an entry in a registry | replaced at commit |
| `self.expose(resource)` | a member backed by a resource (local types) | follows the resource |

Names are strings: declaring one twice in a run fails (`invalid/duplicate`). Each kind has its own names, so a cell and a resource may share one.

A listener keeps its subscription across reloads when it is declared on the same resource (or source) with the same `select`: the same function, or one with the same source text. `select` is not called again, so a source that accepts a single subscriber (a Durable watch) survives reloads, and `select` may wrap the value in a new adapter object. A `select` whose result depends on captured values that change between reloads is not noticed; give such a listener a new name.

**A listener on state reconciles.** A listener on state (a cell, a derivation, a reference's state member) gets the current value when it starts, then every new value. When a reload replaces its source (a derivation is new at every reload), it subscribes again and gets the current value again. Write its handler to bring things in line with the value it gets (set, compare, start or stop what the value says), not to count or append per call. An event source (a resource's events) delivers no current value.

A name you no longer declare is released, closed or stopped, after the old code has finished what it was doing.

**State that must survive a reload lives in cells,** never in closure variables. A closure variable lasts as long as one version of the code.

```ts
// wrong: reset on every reload
host.serve(Visits, (_, _p, self) => {
	let visits = 0;
	return { hit: async (ctx) => ++visits };
});

// right
host.serve(Visits, (_, _p, self) => {
	const visits = self.state("visits", Type.Number(), 0);
	return {
		hit: async (ctx) => {
			visits.change(ctx, (n) => n + 1);
			return visits.value;
		},
	};
});
```

**Methods** are declared with `method(args?, result?)` in the contract. Without `args` a method takes none: callers write `ref.hit(ctx)` (or `ref.hit()`), and its implementation is `(ctx) => …`. Without `result` it returns nothing: the implementation returns nothing, and callers get `undefined`. `method(undefined, Type.Number())` takes no arguments and returns a number.

## Activation

The factory is synchronous, but activation isn't. `self.get` and `self.resources` only *declare*; the slow work happens afterwards:

```text
get(Index, { session: "S1" })
 1. run the factory               → declarations
 2. open declared resources        → e.g. connect to SQLite
 3. wait for declared refs        → dependencies activate first
 4. run the cells' init           → e.g. read the rows into a cell
 5. live                           → refs become "live"; listeners and tasks start
```

```ts
host.serve(Index, ({ session }, _host, self) => {
	const db = self.resource("db", { version: 1, open: () => openSqlite(indexPath(session)), close: (db) => db.close() });
	return {
		search: async ({ query }, ctx) => db.value.all("SELECT entryId, text FROM fts WHERE fts MATCH ?", [query]),
	};
});

host.serve(Chat, ({ session, conversation }, principal, self) => {
	const index = self.get(Index, { session });  // a placeholder until Index is live
	return {
		variant: "participant",
		find: async ({ query }, ctx) => index.search({ query }, ctx),  // only ever runs once Chat (and Index) are live
		// ...
	};
});
```

**Rules:**
- Inside the factory, never use what you declared: `db.value` and `index.someState.value` throw `not_ready`, and calling a reference throws. Use them in methods, listeners, tasks and `init`.
- **The object goes live only with its references ready**: live, and (for a remote reference) every state member of its variant hydrated. The same holds for state it forwards or derives from a remote reference it holds some other way: it goes live once that state has its value. A reference that is not ready after the host's `readyTimeout` (default 60 s) fails the activation with `unavailable/ready_timeout`; a reference cycle across hosts ends that way instead of hanging.
- **Concurrent `get`s** of one address share one activation, so the database opens once.
- **Failure propagates:** if `openSqlite` throws, `Index` fails, `Chat` fails with that cause, and every waiting `get` rejects. The next `get` tries again.
- **Abandoned activations:** if everyone releases before activation finishes, the result is disposed.

### Startup readiness and parent admission

`await host.load(facets)` and `await host.install(facet)` wait for the `lifetime: "host"` objects they install to
become live: resources are open, declared references are live, and registrations are published. All facets in a load
are installed before activation is awaited, so a host object can use a provider in a later facet. Referenced objects
are created only when something references them. Factory, dependency and resource errors reject startup with the
reference's activation error; host object failures also reach `onError`. Installation is not rolled back on failure: close the host
when abandoning startup. `install` registers synchronously, so setup/registration errors still throw synchronously.

`await host.ready()` waits for the host objects present when called, including direct
`host.serve(..., { lifetime: "host" })` and previously deferred loads. It is an activation barrier, not a continuous health check, a wait for tasks to
finish. Later installations require another readiness wait.

A worker may need to open its local Harness and announce control readiness **before** the parent accepts its link.
A host object reporting to the server's SessionStatus cannot become live before that acceptance. Awaiting the
whole load before announcing control readiness would deadlock. Defer the whole barrier explicitly:

```ts
// Connect the upstream link first; its outgoing references can queue until the parent accepts it.
await worker.load(workerFacets, { awaitHostObjects: false });  // also supported by install
const harness = await worker.get(Harness, {});        // local bootstrap only; no upstream dependency
announceControlReady();                               // parent can now accept the worker link
await worker.ready();                                 // every host object live, including upstream references
harness.release();
```

`awaitHostObjects: false` still starts every host object; it skips waiting, not activation. There is no
automatic classification of upstream dependencies. Choose a local bootstrap reference with no upstream dependency,
connect before loading upstream consumers, and let the parent admit the link before the full barrier. Control
readiness means admission is possible, not that every host object is live. Keep worker bootstrap counted as busy
until the full barrier settles, and report a later failure through the worker's fatal/startup-error path. Never await a
reference whose object needs the parent (a remote one, or a local one that holds one) before the parent admits the link.

To hand out a native object a resource opens (a local type's `opaque` member), expose the resource. References read its value once the object is live, and `undefined` before:

```ts
host.serve(Harness, (_, _host, self) => {
	const durable = self.resource("durable", { version: 1, open: () => DurableHarness.open(storage), close: (h) => h.close() });
	return { harness: self.expose(durable) };  // contract member: harness: opaque<DurableHarness>("pi.durable-harness@1")
});

const harness = await ctx.get(Harness, {});
harness.harness.resume();  // the DurableHarness itself
```

## Principals and variants

The application defines its principals and how they're keyed. Chord invents none: the app gives every principal a
request can act as.

```ts
type Principal =
	| { kind: "owner"; access: "local" | "relay" }
	| { kind: "guest"; id: string; name: string; session: string; mode: "view" | "full"; revision: number }
	| { kind: "worker"; session: string; generation: number }
	| { kind: "server" }   // the parent's own requests, as a worker sees them
	| { kind: "host" };    // a host's own code

const host = createHost<Principal>({
	name: "server",
	self: { kind: "host" },
	principalKey: (p) =>
		p.kind === "owner" ? `owner:${p.access}` :
		p.kind === "guest" ? `guest:${p.id}:r${p.revision}` :
		p.kind === "worker" ? `worker:${p.session}:${p.generation}` :
		p.kind,
});
```

- `createHost<Principal>` types every factory's `principal`, `ctx.principal`, routes, `accept` and
  `invalidatePrincipal` patterns, so code narrows on `kind` without casts. Facet modules say it too:
  `defineFacet<Principal>((api) => …)` (an app usually exports its own `defineFacet` and `Ctx` aliases). Without a type
  argument, principals are `unknown`.
- There is one object per principal key: two tabs of the owner share an object, and a guest gets its own.
- Code inside a host acts as `self`, so internal objects are shared. A principal with the same key as `self` is the
  host's own, whichever object carries it.
- A link stamps the principal of whatever connects to it. Callers can never supply their own.
- A child host names what its parent's own requests act as: `connect(link, { principal })` (or
  `upstream: { link, principal }`). Requests the parent relays act as the caller it forwards.
- A route names what the hosts it resolves act as when they call back: `route(prefix, { …, principal: (name) => … })`.

**A remote factory picks a variant:**

```ts
host.serve(Chat, ({ session, conversation }, principal, self) => {
	if (!canView(principal, session)) throw forbidden();
	const c = self.get(Conversation, { session, conversation });  // as host: one shared instance
	if (!canSend(principal)) return { variant: "viewer", view: c.view };
	const author = authorOf(principal);
	return {
		variant: "participant",
		view: c.view,
		send: async (input, ctx) => c.submit(input, author, ctx),
		stop: async (ctx) => {
			await c.stop(author, ctx);
		},
	};
});
```

```ts
const chat = await ctx.get(Chat, { session: "S1", conversation: 1 });  // on session:S1
if (chat.variant === "participant") showComposer(chat.send);  // narrows: `send` exists only there
else showReadOnly();
```

**What a variant doesn't do:**
- **It isn't complete authorization.** Methods still check their arguments: that a submission belongs to this conversation, or a session ID to this principal.
- **It doesn't cover flags that change while you hold the object.** Those are state, for example `you: { canDraw: boolean }`.
- **Revocation** is `host.invalidatePrincipal(match)`. It force-disposes matching objects, here and over links, and their references become `gone`. A new `get` runs the factory with the new grants.

Local types have no variants. Their only callers are inside the host, acting as its `self`. If a local object needs to know who's acting, pass that explicitly, like `author` above.

## References

| Where | API | Released |
| --- | --- | --- |
| a factory | `self.get(Type, input)`: synchronous; the object goes live after it is ready | with the object (or its replaced declaration) |
| a call | `await ctx.get(Type, input, { state? })` | when the call settles |
| outside Chord | `await host.get(Type, input, { signal?, state? })` | `ref.release()` |
| a UI runtime | `host.hold(Type, input)`: synchronous, possibly `loading` | `ref.release()` |

```ts
const chat = await ctx.get(Chat, input);  // ready: live, every state member of its variant hydrated
chat.status;  // "loading" | "live" | "released" | "gone"
chat.variant;  // the current variant; a multi-variant reference narrows on it
chat.shape;  // { variant, members, contract }
const send = chat.send;  // a stable function: always dispatches to the current code
chat.view.value;  // the current value, typed T
chat.view.subscribe((v) => render(v));
chat.onStatus((status, error) => { if (status === "gone") reconnect(error); });
chat.release();
```

- **A reference you hold is usable:** an awaited `get` resolves once the object is live and every state member of its variant has its first snapshot, local or remote. It rejects with the activation error (`forbidden`, unreachable, …), with `aborted` (a `ctx.get` whose ctx is aborted or whose call settles first; `host.get`'s `signal`), or with `unavailable/ready_timeout` after the host's `readyTimeout`. Only that reference is released then.
- **A held reference stays subscribed** to the state of its variant, with or without listeners, until it is released. After a link loss the last values stay readable while it re-holds (status `loading`).
- **Reading state before the first hydration throws `not_ready`** (a `hold` that is still loading, a member read inside a factory). A member outside the current variant throws `not_in_variant`; an ended reference throws its end (`released`, or the `gone` error). A listener added before the hydration gets its snapshot then.
- **`state: false`** gives a method-only reference: it receives no state (unless another reference to the same object wants it) and is ready once its object is live.
- **Calls on a `loading` reference wait** until it's live, respecting `ctx` cancellation and a deadline.
- A member missing from the current variant rejects with `not_in_variant`.
- After `release()`, every member rejects with `released`.
- **`gone`** means the object was forced away while referenced: revocation, archive, its host dying. Call `get` again, or show "unavailable". `onStatus` reports every status change (`live`, `loading` while a link reconnects, `released`, `gone` with the error), so a UI needn't poll.
- **References to one remote object share one binding** per host and key (type, normalized input, principal key, contract fingerprint): one hold over the link, one stream per state member, calls over the same hold. Each reference keeps its own status, observers and `release`. With `createHost({ linger: { types: { [typeName]: ms }, cap } })`, a binding whose last reference is released stays held (and hydrated) for `ms`, at most `cap` (default 4) at a time, so taking the reference again costs nothing on the link.
- **Return values are values.** Anything long-lived you want to share is an object you reach with `get`.

## State

```ts
const todos = self.state("todos", Type.Array(TodoSchema), []);

todos.change(ctx, (draft) => {
	draft.push({ id: "t1", text: "Write docs", done: false });
});
todos.change(ctx, (draft) => {
	draft[0].done = true;
});
todos.replace(ctx, []);

todos.value;  // immutable
todos.subscribe((value) => render(value));

// mirroring an external immutable store: subscribers get a diff, not the whole value
view.replace(ctx, conversation.view);                    // diffs when the new value reuses old containers
view.replace(ctx, rebuilt, { diff: true });              // always diff
```

- A `change` is atomic: one revision, or nothing if the callback throws.
- `change` only touches the paths you mutate, so fields your code doesn't know about survive. Use `replace` only where your code owns the whole value.
- Values are immutable. Never mutate what you read or receive.
- Remote references get a snapshot of each state member of their variant, then deltas. After a reconnect or a reload they get a `reset` snapshot, and nothing is replayed.
- `replace` sends a structural diff when the new value shares containers with the old one (a new revision of the same state), and a single replacement otherwise. `{ diff: true | false }` forces either. The value is the same either way.
- An implementation may expose another object's state member as its own: `return { variant: "viewer", view: conversation.view }`. The object goes live only once that member has its value, local or remote.

**A cell whose first value comes from a source** declares `{ init }` instead of an initial value:

```ts
const db = self.resource("db", { version: 1, open: () => openSqlite(path), close: (db) => db.close() });
const notes = self.state("notes", Type.Array(NoteSchema), { init: () => db.value.all("SELECT * FROM notes") });
```

`init(ctx)` runs once the resources are open and the references live, before the object goes live, so no method,
listener, task or subscriber sees a value that did not come from the source. A task that loads the value instead
starts only after the object is live: a method called in between answers from the placeholder (a note that exists
reads as unknown), and an async load can overwrite a write made during its `await`. `init` may be async and gets a
`ctx` to call other objects. The `init`s of one object run in parallel, so one must not read another's cell. A throw or
an invalid value fails the activation. A reload keeps the cell and its value and does not run `init` again; a cell the
reload adds runs its `init` while the reload prepares, and a failure refuses the reload.

`init` reads a source the object has anyway. It saves nothing: what must outlive the process is written to that source
(a database, a file, a Durable document) by the code that changes it.

```ts
const visible = self.derive([catalog.rows], (rows) => rows.filter((r) => visibleTo(principal, r)));
const openCount = self.derive([todos], (t) => t.filter((x) => !x.done).length);
```

Derivation functions are synchronous. A derivation has no name: every reload makes a new one, computed when the
reload commits.

## Calls, ctx and roots

Every method gets `(args, ctx)`, or `(ctx)` when it takes no arguments. Pass `ctx` on to everything you call:

```ts
send: async (input, ctx) => {
	ctx.signal.throwIfAborted();
	const uploads = await ctx.get(Uploads, {});  // a reference owned by this call; released when it settles
	const files = await uploads.resolve({ ids: input.uploads }, ctx);
	return c.submit({ ...input, files }, author, ctx);
},
```

A **root** is a short tree of calls, started at ingress:
- by a link, for a request that arrives without one;
- by `host.root(fn)`, for timers and scripts;
- by each event delivered to a listener (`self.on`);
- by each Chord call made from a `task` or a Durable phase.

A root runs on the code that was current when it started (its **code version**), across hosts, until it ends. Keep roots short. Long-running work is a `task`, and long waits are state.

```ts
// wrong: holds a root (and its version of the code) open for minutes
approve: async (ctx) => waitForHuman(ctx),

// right: record the request as state; the answer is a separate call
request: async (req, ctx) => {
	pending.change(ctx, (d) => {
		d.push(req);
	});
},
answer: async ({ id, value }, ctx) => {
	pending.change(ctx, (d) => {
		settle(d, id, value);
	});
},
```

## Lifetime

An object lives while it's **referenced**, and every reference has an owner:

| Owner | Acquired with | Released when |
| --- | --- | --- |
| another object | `self.get` | that object is disposed, or no longer declares it |
| a call | `ctx.get` | the call settles |
| a connection | a remote host's `get` | release, disconnect, revocation |
| the host | `lifetime: "host"` | host shutdown (or a reload removing its facet) |
| UI | `useObject` | unmount |

- **Disposal** runs after the last reference is released, plus `linger`. Tasks are aborted, listeners removed, resources closed in reverse order (every close runs, and errors are collected), then the object's own references are released, which can dispose further objects.
- **A resource's `close` may still use the objects its object references.** That holds for host shutdown and revocation too: `host.close()` and `invalidatePrincipal` dispose referrers before what they reference, and close links last. Bound remote calls in `close` with a signal: a call over a link that is already down waits for a reconnect.
- **Forced disposal** (revocation, archive) makes references `gone` at once and aborts in-flight calls.
- **References must not form cycles.** Inside one host this is checked at `get`.

```ts
host.serve(Conversation, conversationFactory, { linger: 30_000 });  // switching back quickly doesn't reopen its watch
host.serve(Index, indexFactory, { lifetime: "host" });              // one object from load to host shutdown
```

**`lifetime: "host"`** is for local types with an empty input (or only defaults): the type has exactly one object,
created for the host principal when its facet loads. Every `get` reaches that object, whoever asks; a `get` with
another input is invalid. References others hold do not change its lifetime, and it cannot `linger`. Only such
objects may register into registries. TypeScript refuses `lifetime: "host"` for a remote type, for an input with a
required field and together with `linger`; `serve` checks the same at runtime, for callers without types.

## Registries

```ts
export const Routes = defineRegistry<RouteHandler>("http.routes", { conflict: "error" });

// contribute (only from `lifetime: "host"` objects)
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
}, { lifetime: "host" });

// consume: a request sees the table of its own code version
server.on("request", (req, res) =>
	host.root(async (ctx) => {
		const route = host.registry(Routes).get(`${req.method} ${pathOf(req)}`, ctx);
		return route ? route(req, principalOf(req), ctx) : notFound(res);
	}),
);
```

- Each code version has one complete table. A reload never leaves a moment where an entry is missing.
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

The facet's `setup` argument is its host, scoped to what a plugin needs: `serve`, `name`, `root(fn)`, `registry(R)` and `signal`, which aborts once this run of the facet is no longer installed (a reload replaced or removed it, or the reload that loaded it aborted). Code that is not a Chord method, listener or task (Durable tools and hooks, callbacks of native libraries) keeps it to start roots and read registries, instead of reaching for a process-global host:

```ts
export default defineFacet((host) => {
	host.serve(Sessions, sessionsFactory);
	tools.register("rename_session", (args) =>
		host.root(async (ctx) => (await ctx.get(Sessions, {})).rename(args, ctx)),
	);
});
```

## Hot reload

```ts
await host.reload([new URL("../plugins/chat/worker.ts", import.meta.url)]);  // or reload every changed plugin
```

### What happens

1. **Load** the new modules.
2. **Prepare:** run the new factories over the existing objects, without side effects. Cell writes throw, listeners and tasks don't start, registrations are collected, and changed resources are opened next to the old ones. Contracts are checked against every live consumer. Any failure leaves everything as it was.
3. **Gate:** only if a cell's version was raised or an exclusive resource changes.
4. **Commit:** in one synchronous step, install the new code, swap registry tables, restart tasks, rebind listeners, and send `reset` and shape updates to subscribers.
5. **Retire:** old code keeps running the roots it started. Once they end, it's dropped, along with whatever it alone declared. If they are still running when the next reload starts, that reload waits up to `retireDeadline`, then aborts them (their `ctx.signal`) before it closes what only the old code used.

### Compatible changes: no waiting

Bug fixes, new methods, new cells, new resources and registration changes all switch immediately. A root that started on the old code finishes on it, and new roots get the new code.

### Changing what state looks like or means: bump the cell's version

```ts
// v1: { running, tasks } where tasks counted phases
// v2: tasks counts tasks, and usage is new
host.serve(StatusStore, ({ session }, _host, self) => {
	const status = self.state("status", StatusV2, { running: false, tasks: 0, usage: emptyUsage() }, {
		version: 2,
		migrate: (old, from) => (from < 2 ? { running: old.running, tasks: 0, usage: emptyUsage() } : old),
	});
	return {
		status,
		report: async (s, ctx) => {
			status.replace(ctx, s);
		},
	};
});
```

At the gate, for each live `StatusStore`:
1. **Roots already inside finish.** Their re-entrant calls are let in.
2. **Old roots that haven't touched it yet get `upgrade_conflict`** instead of old code over migrated state. They retry as a new root.
3. **`migrate` runs** on a private copy, and the result is validated against the new schema.
4. **Commit.** New roots use the new code and the migrated state.

If the roots inside don't finish within the deadline (5 s), the reload is **aborted** and nothing changes. The error names the blocking roots.

The version belongs to the cell (default 1); other cells of the object are not migrated. The runtime compares each
cell's schema and version between old and new code:
- unchanged: compatible;
- version raised: migrate (without `migrate`, the value is kept and must fit the new schema);
- schema changed **without** a raised version, or a lowered version: the reload is refused.

A change of meaning with an identical schema needs a bump too. Nothing can detect that one for you.

### Resources

```ts
const db = self.resource("db", { version: 2, open: () => openSqlite(path, { wal: true }), close: (db) => db.close() });  // 1 → 2: reopen
const port = self.resource("port", { version: 1, exclusive: true, open: () => listen(8787), close: (s) => s.close() });
```

- A reload keeps a resource's open value unless its `version`, `deps` or `exclusive` change: `open` doesn't run
  again. The version is required: a native value has no schema to detect a change. The kept resource still takes the
  new code's declaration at the commit, so a later `close` is the new one.
- A changed resource opens next to the old one during prepare. The old one is closed with its own `close` once the
  old code retires.
- An `exclusive` resource can't exist twice, so it's swapped at the gate: close the old one, open the new one, and reopen the old one if that fails.

### Contract changes

| Change | What happens |
| --- | --- |
| Additive, same version | reloads; consumers keep working |
| Breaking, version bumped, with `accepts[old]` | reloads; old consumers go through the adapter |
| Breaking, without an adapter | refused, unless the consumers reload in the same batch |
| Breaking, version not bumped | refused: "consumer needs member …" |

The host's own **reference to a `lifetime: "host"` object** is a lifecycle pin, not an old-version consumer. When a reload replaces
its provider, that reference adopts the new contract at commit; it does not require an `accepts` adapter for itself.
The object, cells and unchanged resources stay alive without reactivation. A refused reload keeps the original
reference and contract. Other references (`self.get`, `ctx.get`, `host.get`, peers) still obey the compatibility rules above;
state-version bumps and migrations are still required when stored state changes.

### Several plugins at once

Reload them together: `host.reload([a, b])`. Prepare sees all new code at once, so a changed contract and its updated consumer check against each other.

On the server, `host.reload(serverFacets, { remote: { "session:": workerFacets } })` reloads every connected worker too. Its report covers the server; `report.children["session:S1"]` says what each worker changed, prepared and gated.

## Hosts and links

```ts
// server
const server = createHost<Principal>({ name: "server", self: { kind: "host" }, principalKey });
server.accept(webSocketLink(wss, { principal: (req) => authenticate(req) }));  // stamps owner or guest from cookies
server.route("session:", {
	authorize: (principal, host) => canReach(principal, host),  // before resolving or spawning
	resolve: (host) => workers.ensure(host),  // a link to the worker, spawned if needed
	principal: (host) => workers.principal(host),  // what the worker acts as when it calls the server
});

// worker
const worker = createHost<Principal>({
	name: `session:${id}`,
	self: { kind: "host" },
	principalKey,
	upstream: { link: ipcLink(process), principal: { kind: "server" } },  // the server's own requests act as this
});

// anywhere
const chat = await ctx.get(Chat, { session: "S1", conversation: 1 });  // browser → server → worker session:S1
const sessions = self.get(Sessions, {});  // `hostNamed("server")`: worker → server, acting as worker{S1}
```

- **The server relays** between its children: worker to worker, and browser to worker.
- **Disconnects:** when a browser disconnects, exactly the references it had in workers are released.
- **Principals across links:**
  - a forwarded principal is accepted only from the parent link;
  - calls an object makes itself act as its host;
  - links ping, and a dead link releases everything held through it.
- **Client origins:** a hold that comes from a browser carries an opaque id of its connection (`origin`), forwarded by the server when it relays the hold, so a worker can tell its clients apart. A client cannot set it. A disconnect releases that client's holds at once.
- **Slow peers:** a peer acknowledges what it processed. While a window (`window`, default 256 KiB) of frames is unacknowledged, state waits and is coalesced per member's stream; calls, results and the first snapshots of a new reference are never held back, so a `get` does not wait behind other references' state. Waiting ops are capped per link (`pendingCap`, default four windows): beyond, the oldest streams are replaced by their current value. So under load a result can arrive before the state change it caused: wait for the state you need instead of assuming it is there when the call returns.
- **Reloads across hosts:** the server coordinates prepare and commit for every host.
- **Workers that start behind** (spawned after a reload) are caught up to the server's code version before anything is routed to them. Calls their roots make to the server meanwhile run in the server's current code version instead of failing `superseded`.
- **Protocol version:** both ends announce the link protocol version in their hello. A peer of another version is not
  talked to: the link closes, and `onProtocolMismatch` (a `LinkOptions` field of `connect` and `accept`) tells the
  side that has to load new code. A browser reloads its page instead of reconnecting:

  ```ts
  host.connect(webSocketLink(socket), { onProtocolMismatch: () => location.reload() });
  ```
- **Browsers** don't take part in commits. They learn about new code through shape and `reset` messages, and an incompatible contract makes their calls fail with `upgrade_required`.

## Durable

A worker's host provides the Durable Harness as a local object of lifetime `"host"`. A Durable phase isn't a root: it's pinned to its registry snapshot by Durable itself. Each Chord call a hook or tool makes starts a fresh short root.

```ts
host.serve(Harness, (_, _host, self) => {
	const durable = self.resource("durable", {
		version: 1,
		open: () => DurableHarness.open(storage, { models, registry: durableRegistry(host, Extensions) }),  // a reader over the code version tables
		close: (h) => h.close(),
	});
	return { conversation: (id: number) => durable.value.conversation(id) };
}, { lifetime: "host" });

// a plugin contributes a Durable extension like any registration
host.serve(Guard, (_, _host, self) => {
	self.register(Extensions, {
		guard: defineExtension({
			name: "guard",
			hooks: [hook(ToolTask, { beforeTool: (call) => (isDangerous(call) ? { block: "Needs approval" } : undefined) })],
		}),
	});
	return {};
}, { lifetime: "host" });
```

A reload changing the guard: Durable phases already running keep the old snapshot, the next phase uses the new one, and there's never a phase without a guard.

## Errors

| Code | Meaning |
| --- | --- |
| `forbidden` | The factory or a method refused this principal |
| `invalid` | Input, arguments or a result failed validation |
| `not_ready` | A declared resource or reference was used inside a factory, or state read before its reference's first hydration |
| `not_in_variant` | The member doesn't exist in the variant you have |
| `released` | The reference was released |
| `gone` | The object was forced away while referenced. Call `get` again. |
| `contract_mismatch` | The provider's contract doesn't cover the consumer's, and no adapter exists |
| `upgrade_conflict` | An old root reached an object migrated meanwhile. Retry as a new root. |
| `superseded` | The root's code version is no longer available on this host. Retry. |
| `upgrade_required` | A browser's contract is outdated. Reload its web facets. |
| `unavailable` | The target host can't be reached or started; reason `ready_timeout`: a reference was not ready within `readyTimeout` |
| `aborted` | The call's `ctx` was cancelled |

## Rules of thumb

| Do | Not |
| --- | --- |
| Keep reloadable state in cells | Closure variables (lost on reload) |
| Bump the cell's version, with `migrate`, when a cell's shape or meaning changes | Changing a schema without a bump (refused) or a meaning without a bump (silent) |
| Bump the contract version on breaking changes; add `accepts` for old consumers | Renaming or removing members at the same version (refused) |
| Do slow setup in a resource's `open` | Awaiting inside the factory (it's synchronous) |
| Do side effects in resources, listeners, tasks and registrations | Effects in the factory body (they run during prepare) |
| Use `ctx.get` inside methods | `self.get` inside methods (a new reference per call) |
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
| facet | A plugin's code for one host (surface): it serves object types (`defineFacet`). |
| object type | Name + contract. `remote` (addressable from other hosts; schemas for input, variant state members, method args/results) or `local` (host-only; members may be anything, including functions and native objects, but must be listed in the contract: `method`, `opaque` or a state schema). |
| factory | `(input, principal, self) => implementation`. Synchronous. Registered with `host.serve(type, factory, options)` from a plugin facet. |
| object | One instance of an object type. Stable identity per `(type, canonicalInput, principalKey)`. Owns cells, resources, references, listeners, tasks, registrations. Survives reloads. |
| implementation | The object's code: what a factory run returns (methods + state members; `variant` for remote types). Immutable, per code version. |
| reference | What `get` returns: a late-bound claim on an object, never the object or its implementation. An object lives while referenced. |
| principal | App-defined. Stamped by links. In-host code acts as the `host` principal. |
| root | One short Chord call tree, admitted at trusted ingress (link request without root, UI event, timer, `host.root`). Carries `{ rootId, codeVersion }`. |
| code version | One committed set of implementations/registrations per host (server-issued id). |
| code holder | Long-lived execution that is NOT a root: Durable phases/tool runs, browsers, `self.task` loops. Every Chord call they make starts a fresh short root. |

## 2. Contracts

Contracts are runtime values for every type (shipped bundles have no TypeScript; third-party plugins are built separately). TS types are inferred from them.

```ts
export const Chat = remote("pi.chat", {
	version: 1,                                   // contract version: a plain number, bumped only on breaking changes
	input: Type.Object({ session: Type.String(), conversation: Type.Number() }),
	host: hostFamily("session:", "session"),       // where its objects live: `session:` + input.session
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
- Local contracts list every member (`members: { search: method(...), harness: opaque(...), status: Schema }`). A reference that is still `loading` must know whether `h.x` is a method (a caller that waits until live), a state member (a readable) or an opaque value, before any implementation exists. Members missing from the contract are found only once the reference is live.
- Every bundle embeds the contract tokens it was built against (its own copy). Fingerprint = hash of the canonical description.
- Placement (remote types, required): `host: hostNamed(name)` (one host) or `hostFamily(prefix, key)` (the host `prefix` + the input's required string field `key`). Data only, in the description (and so the fingerprint and the `hold` token); there is no `at` option. A `get` normalizes the input with the caller's contract, resolves the host and acquires locally if that is this host, else remotely. `serve` (and a reload that loads a facet) refuses a type whose placement excludes the host's name. A host refuses a hold whose input its own contract places elsewhere (`invalid/placement`), and a relay refuses a hold whose target disagrees with its token's placement and input. Coverage requires equal placements, and an `accepts` adapter never bridges two placements: a moved type is a breaking change. A remote reference's address is the type, the normalized input and the principal: no host name.

### Compatibility rule

A consumer built against version M binds to a provider at version N iff N = M and the provider's description covers the consumer's; otherwise only through `accepts[M]` adapters declared by the provider (`serve(type, factory, { accepts: { 1: (current) => v1View } })`); else `contract_mismatch`.

Covers: every consumer member exists with the same kind; methods: both take arguments or neither does, the provider accepts every argument the consumer can send (new fields optional, nothing newly required or retyped), and the provider's result fits the consumer's expected result (extra fields fine; a void consumer accepts any); state: provider value fits consumer schema (extra fields fine); opaque: same name@version.

Additive changes need no bump. Breaking changes (remove/rename/retype, newly required, or a change of meaning with the same shape) bump the number. Same version + non-covering description = forgotten bump, refused. Meaning changes without a bump are undetectable (author's responsibility, as with Durable document versions).

Checked at: `get` binding, reload prepare (new provider token vs every surviving consumer holding the type and every loaded plugin importing it), remote references (consumer token in the `hold` frame).

The exact host-owned reference to a `lifetime: "host"` object is a lifecycle pin, not a surviving old-contract consumer. When its
provider is replaced, commit replaces that reference with one bound to the new provider contract, acquiring it before
releasing the old one so the same object, state and unchanged resources survive. It needs no `accepts` adapter
for its own previous contract. Prepare/abort do not change that reference. All other consumers retain their own tokens
and the normal coverage/adapter checks; state-version and migration checks are unchanged.

## 3. Factory and declarations

Factories are synchronous; returning a promise throws. A declaration has a name only if something of it survives a reload and must be found again: state (its value) and resources (the open value), plus listeners (a kept subscription). Names are strings, unique per object per declaration kind (a repeated name is `invalid/duplicate`); kinds have separate names. Derivations and tasks have no names: a reload makes new ones. References are identified by their address.

```ts
host.serve(StatusStore, ({ session }, _host, self) => {
	const status = self.state("status", StatusSchema, { running: false, tasks: 0 },  // schema required, initial value
		{ version: 2, migrate: (old, from) => upgrade(old, from) });                     // per cell; default version 1
	const errors = self.state("errors", Type.Array(Type.String()), []);
	const catalog = self.get(Catalog, {});                         // reference; identity = canonical address (+ at)
	const watch = self.resource("watch", {
		version: 1, deps: [catalog], exclusive: false,
		open: async ({ signal }) => openWatch(session, signal),
		close: async (w) => w.close(),
	});
	self.on("changes", watch, (w) => w.events, (event, ctx) => status.change(ctx, (d) => { d.tasks = event.tasks; }));
	self.task(async (ctx) => { /* loop until ctx.signal aborts */ });
	const visible = self.derive([status], (s) => project(s));      // synchronous
	self.register(Routes, { "GET /status": handler });              // registry keys are the registry's own keys; `lifetime: "host"` objects only
	return { status: visible, errors, report: (args, ctx) => { status.replace(ctx, args); } };  // exposed state = what is returned
}, {
	linger: 30_000,                                                  // with lifetime "referenced" (the default) only
});
```

| Declaration | Survives reload | Notes |
| --- | --- | --- |
| `state(name, schema, initial \| { init }, { version?, migrate? })` | same cell and value (`initial` ignored, `init` not run); migrated when its version rises; a cell the reload adds runs `init` at prepare (gated objects: at the gate) | Schema required (no TypeScript at runtime). `change(ctx, draft => void)`, `replace(ctx, value)`, `value`, `subscribe`. Writes through `change` touch only mutated paths. Private state is a cell the implementation does not return. `init(ctx)` (may be async) gives the first value, see activation |
| `get(type, input, { at? })` | kept if declared again (same address) | returns a reference |
| `resource(name, { version, deps?, exclusive?, open, close? })` | kept unless `version`, `deps` or `exclusive` change; a kept resource adopts the new declaration (its `close`) at commit | `open` runs at prepare (non-exclusive) or at the gate (exclusive); returns a resource whose `.value` is the open value; a replaced resource closes with its own declaration's `close` |
| `on(name, source, [select,] handler)` | same subscription while source and `select` (identity or source text) are unchanged; `handler` swapped | each event starts a fresh root in the current code version; `select` is not re-run for a kept subscription. State sources deliver their current value at start and after every reload that replaced them |
| `task(fn)` | restarted with new code at commit: the old run is aborted via ctx.signal, and the new one starts once it finished (at most `taskStopDeadline`, default 5 s, then anyway, reported) | a code holder; calls inside start fresh roots |
| `derive(sources, fn)` | a new derivation, computed at commit | synchronous fn |
| `register(registry, { key: value })` | value swapped at commit | `lifetime: "host"` objects only |
| `expose(resource)` | follows the resource | a local member (usually `opaque`) whose reference value is the resource's value once live |

State members of an implementation may be cells, derivations, or state members of references the object holds (they are defined once the object is live). `cell.replace(ctx, value, { diff? })` publishes a structural diff when the new value shares containers with the old one (or `diff: true`), else `r`. Facet `setup` receives `{ serve, name, root, registry, signal }` of its host; `signal` aborts once this run of the facet is no longer installed (a committed reload replaced or removed it, the reload that loaded it aborted, or the host closed).

`migrate` per cell is `(old, fromVersion) => new`. A cell may be several versions behind (author bumped more than once between reloads). Without `migrate`, a raised version keeps the value, which must fit the new schema.

**Listeners on state reconcile.** A listener whose source is state (a cell, a derivation, a reference's state member) is subscribed when it starts and gets the current value, then every new value. A reload that replaces its source (every derivation is new; a reference to another address is another source) subscribes it again, so it gets the current value again: its handler must reconcile (be idempotent), not count events. An event source (a resource's events, any other `subscribe`) delivers no current value; a kept subscription to it is not touched by a reload.

**Methods.** `method(args?, result?)`: without `args` the method takes none (callers `ref.name(ctx?)`, implementation `(ctx) => …`; `method(undefined, result)` for one that returns something); without `result` it is void (callers get `undefined`, whatever the implementation returned). The description records both (absent fields), and the `call` frame carries no `args` and the `result` frame no `value` for them. A consumer and provider must agree on whether a method takes arguments; a consumer without a result accepts a provider's.

Removed vs guide: `self.own`, `holdWhile`, async factories, inferred dependencies.

### Synchronous factory, asynchronous activation

`self.get` and `self.resource` only declare and return placeholders. Activation of an object:

1. run the factory synchronously (declarations);
2. await declared resources' `open()` (e.g. connect a DB);
3. await declared references becoming live (dependencies activate first, coalesced);
4. run the `init` of every cell declared with one, in parallel, each in a root of its own acting as the host principal; validate and install the values;
5. attach derivations, start listeners and tasks;
6. object is live: references `live`, `ready` resolves.

Inside the factory, placeholders must not be used (`resource.value` and an `init` cell's `value` throw `not_ready`; reference calls throw). An `init` that throws, or returns a value its schema refuses, fails the activation like a failed `open`. An `init` must not wait for its own object or one that holds it (it is not live yet), and must not read another `init` cell of its object (they run in parallel). `init` gives a first value from a source the object reads anyway; it does not persist anything, and a cell is not saved anywhere by having one. Methods/listeners/tasks run only on live objects, so their dependencies are live. An object goes live only once its references are ready (live and, for remote ones, hydrated) and the state sources it exposes or derives from have their values, also where they forward a remote reference held some other way; waiting for references is bounded by the host's `readyTimeout` (default 60 s, `unavailable/ready_timeout`, also for a reference cycle across hosts). External consumers holding a `loading` reference (`host.hold`): calls wait until live (ctx cancellation, deadline); state members throw `not_ready` until the first hydration. Activation failures propagate to dependents and all waiting gets; the next get retries.

### Lifetime

`serve(type, factory, { lifetime })`:

| `lifetime` | Created | Ends | `linger` |
| --- | --- | --- | --- |
| `"referenced"` (default) | at the first `get` of its address | after the last reference is released, plus `linger` | allowed (default 0) |
| `"host"` | when its facet loads (or at `serve`); loading waits until it is live | when the host closes, or a reload removes its facet | refused |

- `"host"` is refused at `serve` for remote types, for an input that does not accept `{}`, and together with `linger`;
  the types (`ServeOptionsFor`) refuse the same at compile time, where such an input is one with a required field.
  The type has exactly one object: the empty input (defaults applied), created for the host principal. Every `get`
  reaches it, whatever its principal (the factory sees the host principal); a `get` with another input is
  `invalid/input`. Other references do not change its lifetime: the host keeps its own until it closes.
- Only `"host"` objects may register (`invalid/not_host_lifetime` otherwise).
- A `"host"` object whose activation fails is started again by the next reload that changes its type. A reload that
  makes a type `"host"` creates its object; one that makes it `"referenced"` releases the host's reference, so the
  object lives on only while others reference it.

### Host objects readiness

- `host.install(facet, { awaitHostObjects? })` installs declarations synchronously and returns a promise for this
  facet's host object activations. `host.load(facets, { awaitHostObjects? })` installs the entire batch before awaiting
  its host object activations. `awaitHostObjects` defaults to true. Unreferenced objects are not activated.
- Factory, resource-open, dependency and activation-finalization failures reject the returned promise with the
  activation error (ChordError codes preserved; ordinary errors wrapped as `unavailable`). Host object failures also
  reach `onError`. Installation is not a rollback transaction; setup/registration errors from `install` throw
  synchronously. Abandoned startup should close the host.
- `{ awaitHostObjects: false }` starts the same host objects but resolves after installation, without waiting for
  their activation. `host.ready()` awaits a snapshot of the host's references to its host objects at call time
  (including direct `serve` and deferred loads), rejects their activation failures, and does not acquire additional
  references. It is not an ongoing health check and does not await task completion or remote state hydration.
- Local bootstrap readiness and upstream admission are separate. A worker connects its upstream link, loads with
  `{ awaitHostObjects: false }`, awaits its local bootstrap reference (e.g. Harness, with no upstream dependency), then
  announces control readiness so its parent can accept the link. Only after admission does it await `host.ready()`.
  Otherwise a host object reporting to the server's SessionStatus deadlocks with the parent waiting for control
  readiness. Deferred loads skip the whole barrier, not selected dependencies; callers explicitly choose local
  bootstrap references, keep bootstrap busy until full readiness, and propagate later startup errors.

## 4. Principals, variants, references

- Principals are the app's type `P` (`createHost<P>`, `Host<P>`, `defineFacet<P>`, `Factory<C, P>`, `Ctx<P>`; default `unknown`). Chord invents none: `createHost({ self })` is the principal of the host's own code (roots, code inside objects, `lifetime: "host"` objects), `connect(link, { principal })` what the parent's own requests act as, `accept(link, { principal })` what a link acts as, `Route.principal(hostName)` what a routed host acts as when it calls back. All are required.
- `createHost({ principalKey })` maps principal to a key that includes connection provenance and grant revision. Objects are per principal key. The host's own principal is recognized by key (`principalKey(p) === principalKey(self)`), not by object identity, so an equal principal never creates a second object.
- Remote factories return `{ variant, ...members }`; `variant` must be a declared variant; members must match it. Local factories return any object. `variant` is reserved as a member name.
- Reference: `status` (`loading | live | released | gone`), `ready` promise, `variant`, `shape` (`{ variant, members, contract }`), `onStatus(listener)` (every status change, with the error for `gone`), late-bound members, `release()`. `self.get` is synchronous (the object goes live after its references are ready); `ctx.get` and `host.get` resolve once the reference is ready: live, and every state member of its variant hydrated (`state: false`: live only). They reject with the activation error, `aborted` (ctx aborted or settled, `signal`), or `unavailable/ready_timeout`, releasing only that reference. `host.hold` is the synchronous form for UI runtimes. A held remote reference stays subscribed to its variant's state until released; after a link loss its last values stay readable while it re-holds. State members are typed `T`; reading before the first hydration throws `not_ready`, outside the variant `not_in_variant`, after the end the end's error. A remote reference type is a union discriminated by `variant`. Shape changes (reload, variant) are pushed; members missing from the current variant reject `not_in_variant`; released references reject `released`; forced disposal makes references `gone`.
- Shared bindings: remote references on a host with the same key (type, normalized input identity, principal key, consumer contract fingerprint) are views onto one binding: one hold, one stream per state member, calls over that hold. Views have their own owner (object, call, external), status, observers and `release`; the binding ends (gone) or re-holds for all of them. Without views a binding closes, or lingers for `linger.types[typeName]` ms (`createHost({ linger: { types, cap } })`, at most `cap`, default 4, least recently released first) while staying held and hydrated.
- Methods are `(args, ctx) => Promise<result>`. Factories still check arguments; variants are not complete authorization.
- Revocation: `host.invalidatePrincipal(match)` force-disposes matching objects on this host and propagates over links; links re-stamp or close.

## 5. Lifetime

- Reference owners: object (declared `get`), call (`ctx.get`, released at settle), connection (remote references; relay maps per origin connection), host (`lifetime: "host"`), UI.
- Activation coalesced per address; if all requesters leave before it completes, the result is disposed. Factory throw: unwind declarations, reject gets, next get retries.
- Disposal after the last reference is released + `linger`: tasks aborted, listeners removed, resources closed (reverse order; all run; errors aggregated), the object's references released (cascade).
- Bulk forced disposal (`host.close`, `invalidatePrincipal`) goes in waves, referrers before what they reference, so a resource's `close` can still use its object's references; `host.close` closes links after the objects.
- Forced disposal: references `gone` immediately, new calls rejected, in-flight call contexts aborted, then cooperative cleanup.
- Reference graph acyclic in-host (checked at get); across hosts by convention.
- Links have ping/timeout; a dead link releases everything held through it.

## 6. Roots and code versions

- `Ctx = { signal, rootId, codeVersion, get(...): Promise<Ref>, principal? }`. Explicit; no AsyncLocalStorage dependency (may be used in dev to warn).
- A link creates a root for a request that carries none; nested remote calls carry `{rootId, codeVersion}`.
- Dispatch: a call with code version E runs the object's implementation for E. A host retains at most `current` and `previous` code versions (two-version rule). A call for a code version the host doesn't have (older than previous, or host started later) is rejected `superseded` (retryable by starting a new root). Never substitute another code version.
- Browsers never carry code versions into the server: browser calls start roots at the server. Browsers learn of changes via shape/reset pushes and a server `Manifest` object; incompatible contract fingerprint -> `upgrade_required`.

## 7. Reload

Explicit trigger (`reload_plugins` tool, button, API). Serialized; no nesting.

1. Build/type-check gate (application tooling, outside Chord): dependency-closed set; refuse breaking remote contract changes without a contract version bump.
2. Load: on every affected host, import new facet modules (cache-busted).
3. Prepare: for each live object of each affected type, run the new factory in recording mode: existing cells readable, writes throw; listeners/tasks/registrations recorded, not started; references recorded; non-exclusive resources whose name is new or whose `version`/`deps` changed are opened as candidate-owned (closed on abort). Validate keys, variants, registry collisions. New objects activated during prepare use the current code version (old code). Any failure: abort, discard candidates. Vote.
4. Gate (only objects with a cell whose version was raised or which replace an exclusive resource, plus objects depending on those resources):
   - Admission cut: from now, an old-code-version root that has not touched the object gets `upgrade_conflict` (retryable), not queued. Roots that already hold an activation lease on it are grandfathered; their re-entry is admitted.
   - Wait for grandfathered activations to finish, deadline (default 5 s). Missed deadline: abort the reload, reopen, nothing changed (report blocking roots).
   - Exclusive resources: close old, open new; on failure reopen old and abort.
   - Run `migrate` into private copies; validate.
5. Commit (server commits itself, then sends commit to children; the decision is not persisted, see section 12; FIFO links guarantee no host receives a new-code-version root before committing): each host in one synchronous step installs migrated cell values and cell versions, installs implementations as code version E', swaps registry tables, restarts tasks with new code, rebinds listeners, pushes shape/reset to subscribers, opens gates. E' current, E previous.
   The coordinator's result carries `children`: each participating child's prepared report (its vote).
6. Retire: when no roots of `previous` remain (and, on a child, the parent retired it), drop its implementations and release declarations only it declared. The next reload first waits for that, at most `retireDeadline`; then it aborts the roots still running on `previous` (their ctx signals), gives them up to 1 s to stop, and retires anyway. A coordinator retires before it sends `prepare`, so its `retire` frames reach the children first.

Compatible changes (no state bump, no exclusive resource change) skip the gate: no waiting.

State compatibility rule: reload prepare compares each cell's old and new schema and version. Unchanged: compatible (no gate). Version raised: gate + `migrate` (or the kept value), validated against the new schema. Schema changed without a raised version: reload refused. A lowered version: refused. A change of meaning with an identical schema needs a bump too (undetectable; author's responsibility). Initial values and migrate outputs are validated; per-write validation in dev mode.

## 8. Registries

```ts
export const Routes = defineRegistry<RouteHandler>("http.routes", { conflict: "error" });
self.register(Routes, { "GET /download": handler });       // in a `lifetime: "host"` object; keys are the registry's keys
host.registry(Routes).get("GET /download", ctx);            // table of ctx.codeVersion (or current without ctx)
host.registry(Routes).subscribe((table, codeVersion) => ...);     // bridges for imperative consumers (Durable)
```

Per-code-version immutable tables; order = first registration order, kept on replace. An application can implement Durable's `RegistryReader` from the table (snapshot per code version) so phases pin a complete snapshot; Chord does not ship that bridge.

## 9. Hosts and links

- `createHost({ name, self, principalKey, upstream?: { link, principal } })`; `host.accept(link, { principal })` for children; `host.connect(link, { principal })` for the parent; `host.route(prefix, { authorize(principal, hostName), resolve(hostName) => Promise<Link>, principal(hostName) })`.
- Links: `memoryLinkPair()` (tests), Node IPC (child_process), WebSocket (server `ws`, browser `WebSocket`).
- Principal stamping: the accepting side stamps the principal of what connects (from its authenticator); forwarded principals accepted only from the parent link; the parent's own requests (no forwarded principal) act as the principal given to `connect`; payload principal fields ignored.
- A child that connects behind its parent's code version is fenced (nothing routed to it) and reconciled by a reload of its modules to the parent's code version. Calls its roots of the old code version make upstream are admitted in the parent's current code version (the parent never ran that code version), not rejected `superseded`.
- Relay: server forwards a hold to the child link of its target host (`at`, resolved by the consumer from the contract's placement and the normalized input, and checked against both), mapping references per origin connection; authorizes before resolving/spawning and re-checks after.
- Wire frames (JSON): `hello`/`bye`, `hold`/`release` (a reference over a link: `hold` returns `shape` or `gone`; there is no separate `get`), `shape`, `call`/`result`/`cancel`, `sub`/`unsub`/`resync` and `state`, `gone`, `root_end`, `retire`, `invalidate`, `ping`/`pong`, `ack`, reload control (`prepare`/`vote`/`commit`/`abort`).
- State: a `hold` implies the state of its variant (`state: false`: none until `sub`; `unsub` stops it). The provider answers with units: a `shape` whose `state` lists the members the consumer lacks, followed by one `state` frame `as: "snap"` per listed member; the consumer applies the shape once those snapshots are here. Later `state` frames of a member (addressed by hold id and member `m`) are `ops` (per-stream delta encoder), `reset`, or `error`; a `snap`/`reset` without `value` carries `undefined`. A failed snapshot before the first hydration ends the reference with its error. A reload or variant change sends a unit with the members that are new; members that left stop. `again` marks a re-hold after a link loss (the consumer has values). `origin` names the client connection a hold comes from (stamped by the host that accepted the client, forwarded by relays, honored only from the parent link).
- Protocol version: `hello` carries `protocol` (`PROTOCOL_VERSION`, now 4; absent means 1). A side that sees another version processes nothing more, calls `LinkOptions.onProtocolMismatch({ local, peer })` and closes the link with reason `protocol-version <its version>`; the other side's connection reads that reason and reports the mismatch too. Peers do not negotiate: the outdated side must load the current code (a browser reloads its page). Frame fields follow the version: the `shape` frame names the variant `variant`, code versions travel as `codeVersion` (2); remote contract tokens carry their placement (`host`), and a `hold` carries the input normalized by the consumer (3); a hold implies its state, units, `origin`, and `shape` without a code version (4).
- Flow control: both ends announce `acks` in their hello and acknowledge what they processed (`ack`, a cumulative count of every frame but `ack`). While the frames not yet acknowledged exceed the window (`window`, default 256 KiB of JSON text), state waits at the sender in slots flushed in creation order: one per member stream (ops are appended, a snapshot or reset replaces it, a release or `unsub` drops it) and one per hold for a unit (lazy: built from the current values when sent; a newer unit merges into it). Waiting ops are capped per link (`pendingCap`, default four windows): beyond, the oldest streams become a reset of their current value built at flush (a relay sends `resync` downstream and drops that member's ops until the reset arrives). The first unit of a hold that is not `again` and every frame but state are sent at once. Links that report no frame sizes (IPC) are never windowed; a peer without `acks` is neither windowed nor acknowledged. An acceptor can limit the calls a peer has in progress (`maxCalls`); calls beyond it are answered at once with `unavailable/too_many_calls`. Nothing outside the connection may add frames to a link: acknowledgements count them.

## 10. Host manager (library)

`createHostManager({ driver, keepAlive })`: fork driver (entry, init, lock, env), serialized start/stop/replace, exit-before-replace, process-tree kill after grace, control channel (ready/fatal/shutdown), liveness callback (booting, activeCalls, viewers with heartbeats, durable tasks, idleFor).

## 11. Test coverage

The tests cover at least: lifetime/references/linger/forced disposal/gone; activation coalescing and abandonment; principals and variants; remote calls over memory links incl. relay and principal forgery attempts; state snap/ops/reset over a link with reconnect; registries per code version; reload: compatible (no wait, pinned roots), prepare isolation (writes throw, failing factory leaves everything unchanged), state bump with migrate and gate, `upgrade_conflict` for late old roots, deadline abort, exclusive resource replacement, cross-host commit ordering, two-version retirement and `superseded`.

## 12. Known limitations and decisions

### Still open

- **Retirement across hosts.** A child retires a code version only after its parent retired it (`retire` frame) and its own roots of that code version ended; the server decides from its own roots. A child that comes in step (hello or reconciliation) is told which code versions the parent retired before. A root started on a worker that calls up to a server which has already retired the code version both had still gets `superseded` (retryable).
- **The commit decision is not persisted** (section 7, step 5). A server crash between its own commit and a child's commit leaves that child on the old code version until it reconnects and is reconciled.
- **One level of reload participants.** Only the coordinator's direct child hosts take part; a child does not forward `prepare` to its own children.
- **Reconciliation needs the child's module list.** It is remembered from cluster reloads (`host.remoteModules`), so a server restart forgets it, and a child behind a restarted server then reloads no modules: it gets the code version id with its own code. The reconciliation vote deadline is fixed at 30 s; a failed reconciliation closes the link, so the host manager restarts the worker.
- **Links do not resume.** The provider releases everything held through a closed link at once, so re-held objects are new ones. Keeping references for a reconnect window would need session ids on links. Calls in flight when a link drops reject `unavailable`; whether they ran is unknown.
- **Refused clients cannot tell.** The WebSocket adapter closes unauthenticated sockets; the client sees a dropped upstream and its calls wait for a reconnect until their ctx is aborted.
- **The publication queue is process-wide and synchronous.** A slow observer delays every later notification in the process, including those of other hosts in the same process.
- **No automatic restart.** A terminal host failure is picked up by the host manager's `keepAlive` or `fatal` path, not inside Chord.
- **The Node loader leaks.** Every reload imports fresh module copies that are never evicted, and it does not isolate plugins (`TODO(loader)`).
- **Stale socket locks.** On Unix systems other than Linux, two processes that probe the same stale socket file at the same moment could both take the lock. Managers serialize starts per lock name.
- **Listener `select` identity.** A listener's subscription is kept across factory runs when its origin and `select` are unchanged; `select` counts as unchanged when identical or with the same source text, so a `select` whose implementation depends on captured values that change between runs is not detected.
- **Shutdown and dead links.** `host.close()` disposes objects in waves (referrers before what they reference) and closes links last. A `close` that awaits a remote call over a link that is already down waits for a reconnect; bound such calls.

### Decisions

- **Errors.** The guide's codes; a `reason` field carries the detail, for example `invalid/args`, `invalid/cycle`, `invalid/duplicate`, `invalid/read_only`, `invalid/not_host_lifetime`, `invalid/registry_conflict`, or `unavailable/unknown_type`. A `ChordError` thrown by a factory or a dependency keeps its code through every dependent; other errors become `unavailable`, with the original as `cause`.
- **Reload errors.** There is no `reload_aborted` code. A failed reload throws the cause's code and reason with the message `reload aborted: …` (the cause is attached). Reasons of its own are `aborted/gate_deadline` (with the blocking roots in `details`), `aborted/deadline`, `aborted/vote_deadline` and `unavailable/reload_running`. Across hosts, the message names the host that failed. A child cannot reload on its own (`unavailable/not_coordinator`).
- **New objects during prepare.** A reload pre-allocates the next code version ("pending"). Types the same reload adds are served from it; their objects install implementation only for the pending code version and are force-disposed if the reload aborts.
- **Gate admission.** From the gate until commit or abort, creating a new object of a changed type fails with `upgrade_conflict` (retryable, reason `gate`); nothing is paused, so nothing can deadlock. Gated objects get `minCodeVersion = E'`: calls and writes carrying an older code version are rejected `upgrade_conflict` permanently, and a gated object drops its previous-code-version implementation at commit. Only objects whose cell versions or exclusive resources change are gated.
- **Tasks and listeners during the gate.** Tasks of gated objects are aborted at the admission cut and restart with new code at commit, or with the old code on abort. Listener events for gated objects are queued and replayed through the new listener at commit, or the old one at abort.
- **Grandfathered roots** are the roots that called into the object and are still running at the cut. Every host remembers on which links a root's calls went out and sends `root_end` on them when the root ends, so leases outlive calls across hosts.
- **Removed types and missed retirement.** Objects of removed types are force-disposed at commit. When a retirement deadline is missed, retirement is forced: those roots are aborted first (their ctx signal, reason `superseded`; a relayed call's root cancels its downstream call), then what only that code version declared is closed, and their next call is `superseded`.
- **Joining during a reload.** Participants are the child hosts in step when a reload starts. A child whose hello arrives while it runs is decided when it ends: in step, or reconciled to the committed code version; a child already behind is fenced at once, so the calls its roots make meanwhile are admitted in the parent's code version. A reconciliation that is running when a reload starts syncs its child only after that reload ended, against the code version it committed. A reconciliation announces the parent's retired code versions before its `prepare`.
- **Two-version rule.** An object of a changed type created after a commit has only new code; a previous-code-version root calling it gets `superseded`.
- **Validation.** Remote calls are validated at reference dispatch, in-host too: a direct binding against the provider's schema, a binding through an adapter against the consumer's. A provider validates each snapshot and reset of a remote state member once per (re)subscription, against the consumer's contract through an `accepts` adapter and the provider's otherwise; ops are validated only in dev mode. At reload, the new provider's description must cover the old provider's when the version is unchanged, in addition to the check against live consumers and facets' `uses`.
- **Contracts.** Local contracts list their members, so a loading reference knows whether a member is a method, state or opaque. Canonical identity omits input fields equal to their default; with TypeBox, use `Type.Optional(Type.X({ default }))` to let callers omit them. Provider variants must cover consumer variants; members the consumer's contract does not list are hidden. Schema change detection compares canonical JSON, so reordering `anyOf` branches counts as a change. Fingerprints use a non-cryptographic 64-bit hash: synchronous and browser-safe; contracts are trusted.
- **Principals.** A root ctx at ingress acts as its principal (`host.root(fn, { principal })`); contexts inside objects act as `host`. The acceptor decides a link's kind and name (`accept(link, { principal, kind, name })`); only configured host links are addressable, carry roots and may vote, and control frames are accepted only from the parent. Clients never carry roots or code versions. Relaying needs a matching `route`; `authorize(principal, hostName)` runs before `resolve` and again after, and revoking or re-stamping a principal closes its relays at once. `invalidatePrincipal(match)` re-stamps or closes matching links and propagates pattern matches to child hosts.
- **Cells and readables.** A value returned from `change` replaces the value and is always validated; `replace` transfers ownership without copying; by default (`{ diff }` overrides) it publishes a diff when the new value reuses a container of the old one at the same key, else `r`. `subscribe(fn)` delivers values, starting with the current one; `events(fn)` delivers `snap`, then `ops`, or `reset`. Reference state members are stable readables that throw `not_ready` while loading and `not_in_variant` outside the variant, and reset when their source moves; a listener added before they are readable gets its snapshot then. Remote state members stay hydrated while the reference is held.
- **References and calls.** A reference's identity is its address; a second `self.get` of the same address in one run returns the same reference. A reference call without ctx, or with a task ctx, starts a fresh root in the current code version; a ctx whose call or root already settled is refused (`aborted/expired`), one from another host `invalid/foreign_ctx`. Calling a reference inside a factory throws `not_ready`.
- **Resources and disposal.** New and replaced exclusive resources open at the gate, and so do non-exclusive resources of the same object that depend on them. A new object for an address that is still being disposed waits for that disposal. A resource open that completes after its signal aborted closes its value at once.
- **Links and the host manager.** Every received frame is validated against its schema; malformed frames, duplicate ids and control frames from the wrong side close the link. Each connection pings every `pingInterval` and closes after `pingTimeout` without a frame. The child holds a kernel lock (an abstract socket on Linux and Android, a named pipe on Windows, a probed socket file elsewhere), acquired by `childControl().lock()` before storage opens. The manager kills the child's process group on every exit path and derives `booting` and `idleFor` from the child's liveness reports. WebSocket support is structural, so Chord does not depend on `ws`.
- **Flow control holds back state only.** A relay (Cloudflare to a browser) can hide a slow reader, so transport backpressure cannot be relied on; acknowledgements are end to end. Results must not wait behind state, so links are FIFO except that waiting state frames can be overtaken: a result may arrive before state changes made before it. Frames of one subscription stay in order. Waiting state is coalesced rather than queued and capped per link, so a stalled peer costs bounded memory, and the next frame it gets is current. The first unit of a new reference is not held back, so a `get` never waits behind other streams.
- **The state API stays.** Objects keep named cells and unnamed derivations; giving each object exactly one state value was rejected. Do not reopen this without a new, concrete problem.

---

## Tutorial

## 1. What problem does Chord solve?

A todo list has data, operations on that data, and several people looking at it.
You could hand-write object creation, subscription cleanup, messages between
processes, and code replacement. Chord connects these pieces for you.

A **host** is the runtime that owns objects. An **object** combines state with
methods at an address, such as “the family todo list.” A **reference** is a caller's
reference to that object, not the object itself. Several references can reach the
same object. References can also reach another host over a connection.

```text
browser host                         server host
ref + subscribed rows -- link --> Todos view (owner or guest)
                                           |
                                        ref
                                           v
                                   TodoStore: rows + methods
```

We will start inside one host, add observable state, then share it with a
browser. Finally we will add background work, plugins, and hot reload.
**Live state** means subscribers receive new values when data changes, without
asking for it again.

<!-- example:01 -->
```ts
const host = createHost({ self: "server", name: "todo-server" });
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
schemas. `method(args, result)` declares a method by its argument and result
schemas: `method()` takes no arguments and returns nothing, and
`method(undefined, Type.String())`, used below, takes no arguments and returns a
string.

Start with a label for a named list. `local` means only code inside this host
can reach it. The input `{ list: "family" }` identifies which list we want;
it is not an argument to `label`.

<!-- example:02-contract -->
```ts
const TodoLabel = local("tutorial.todos", {
	version: 1,
	input: Type.Object({ list: Type.String() }),
	members: { label: method(undefined, Type.String()) },
});
```

A **factory** is a synchronous function that creates the object's implementation:
the methods and state callers will see. `serve` registers a contract and its
factory. Registration alone does not activate this lazy object; the first
`get` does.

A **root** is one short tree of calls, such as the work for a button click.
`host.root` starts it. Its **context**, called `ctx`, carries cancellation,
caller identity, and the code version for nested calls. Pass it to methods you
call from that root.

<!-- example:02-call -->
```ts
const host = createHost({ self: "server" });
host.serve(TodoLabel, ({ list }) => ({ label: () => `Todos for ${list}` }));
const result = await host.root(async (ctx) => {
	const todos = await ctx.get(TodoLabel, { list: "family" });
	return todos.label(ctx);
});
assert.equal(result, "Todos for family");
```

The result is `"Todos for family"`. `await ctx.get` resolves once the object is
live (and, as we will see, has its state). The reference acquired through
`ctx.get` is released when this root ends. We never receive the factory's
returned object directly. A standalone call without `ctx`, such as
`todos.label()`, starts its own root. A method without arguments takes only
the context: `todos.label(ctx)`; its implementation is `(ctx) => …`. Inside a root or method, pass the
existing `ctx` so nested calls stay in the same call tree.

The factory may also receive `principal` (who is asking) and `self` (the
object's declaration API). We did not need them yet.

> **Why:** The reference separates callers from implementations. Later, replacing
> code will not require replacing every caller's reference.

## 3. Give the list live state

A label is not a todo list. We need rows that can change, and a count that always
agrees with them. A **cell** owns an observable JSON value. A **derivation**
computes another observable value from cells or other readable sources.

Extend the contract with `rows`, `openCount`, and editing methods. State
members describe values, not methods. This adds members at contract version 1;
older callers that only need `label` still have everything they need.

`self.state(name, schema, initial)` declares a cell and returns it. The name
`rows` is important: on reload, Chord matches that name to the existing cell and
keeps its value. `self.derive(sources, fn)` declares a derivation; it has no
name, because it holds nothing a reload must keep.

<!-- example:03-contract -->
```ts
const Todo = Type.Object({ text: Type.String(), done: Type.Boolean() });
const Rows = Type.Array(Todo);
const TodoStore = local("tutorial.todos", {
	version: 1,
	input: Type.Object({ list: Type.String() }),
	members: {
		label: method(undefined, Type.String()),
		rows: Rows,
		openCount: Type.Number(),
		add: method(Type.Object({ text: Type.String() })),
		finish: method(Type.Object({ index: Type.Integer() })),
		reset: method(Rows),
	},
});
```

The factory now declares a cell and a derivation. It is wrapped in `todoStore`,
which takes the cell's options (section 9 raises its version); for now
`todoFactory` uses the defaults. Each method receives its arguments and a
context; changing the cell updates its readers and its derived count together.
`add`, `finish` and `reset` declare no result, so they return nothing.

<!-- example:03-factory -->
```ts
/** The store's factory; `options` versions its rows (section 9). */
const todoStore =
	(options?: StateOptions<Static<typeof Rows>>): Factory<typeof TodoStore> =>
	({ list }, _principal, self) => {
		const rows = self.state("rows", Rows, [], options);
		const openCount = self.derive([rows], (todos) => todos.filter((todo) => !todo.done).length);
		return {
			label: () => `Todos for ${list}`,
			rows,
			openCount,
			add: ({ text }, ctx) => {
				rows.change(ctx, (draft) => {
					draft.push({ text, done: false });
				});
			},
			finish: ({ index }, ctx) => {
				rows.change(ctx, (draft) => {
					const todo = draft[index];
					if (!todo) throw invalid("args", "No such todo");
					todo.done = true;
				});
			},
			reset: (next, ctx) => {
				rows.replace(ctx, next, { diff: true });
			},
		};
	};
const todoFactory = todoStore();
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
const host = createHost({ self: "server", dev: true });
host.serve(TodoStore, todoFactory);
const todos = await host.get(TodoStore, { list: "family" });
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
unsubscribe function. The awaited `get` makes sure there is a value: a reference
you hold is live, with its state.

> **Why:** Store reloadable state in cells, not closure variables. Treat
> `cell.value`, `ref.rows.value`, and subscriber values as immutable.
> Only mutate drafts inside `change`; do not keep a draft for later use.
> A derivation runs synchronously, so use it for projections, not database work.

## 4. Let objects use objects and resources

Saving a todo may require both the list and a database connection. A
**reference** keeps the object it refers to alive. `self.get` declares a
reference owned by this object; it lasts longer than a single method call.

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
	members: { add: method(Type.Object({ text: Type.String() })) },
});
const host = createHost({ self: "server" });
let opens = 0;
const closed = Promise.withResolvers<void>();
host.serve(Database, (_input, _principal, self) => {
	const db = self.resource("db", {
		version: 1,
		open: async () => {
			opens++;
			return { saved: [] as string[] };
		},
		close: () => closed.resolve(),
	});
	return { db: self.expose(db) };
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
			},
		};
	},
	{ linger: 0 },
);
```

An outside consumer holds a `SavedTodos` reference. We also hold `Database`
directly so we can inspect what was saved.

<!-- example:04-call -->
```ts
const saved = await host.get(SavedTodos, { list: "family" });
const database = await host.get(Database, {});
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
even though two objects referenced it. `SavedTodos` and `Database` become live
only after their resources and declared dependencies are ready. That is why
`database.db!` is safe inside this live object's method: activation has
already established that dependency. An outside caller awaits its `get`.

When both external references are released, `SavedTodos` is disposed and
releases its own database reference. With no references left, the database closes; we
wait for `closed.promise` to prove it. The released reference stays
`released`, and `onStatus` reports that transition. `onStatus` watches
changes; unlike state subscription, it does not deliver an initial status.

`linger` is a delay in milliseconds after the last reference is released. Zero disposes
without a grace period; a positive value can avoid reopening an expensive
resource when a screen is briefly hidden. Linger is not persistence.

> **Tip:** A factory only declares dependencies. Never call a referenced object's method or
> read `resource.value` there, including during reload. Activation happens
> afterward. Bump a resource's `version` when its configuration should be reopened.
> Disposal stops tasks and listeners, closes resources, then releases references.

## 5. Who is asking? One store, two views

Owners may add todos; guests may only read them. A **principal** is the
application-defined identity of a caller. A **variant** is a named set of
members a remote object offers to that principal. It lets the UI discover
whether an editing method is available.

Do not create a separate data cell for each viewer: their lists would diverge.
Instead, each view holds the same host-local `TodoStore` and exposes its rows.
`self.get` acts as the host's own principal, so owner and guest views share
that store. Remote view objects themselves are separate per principal key.
A remote contract also says where its objects live: `host: hostNamed("server")`
puts every `Todos` object on the host named `server`. Section 6 uses that.

<!-- example:05-views -->
```ts
const Todos = remote("tutorial.todo-view", {
	version: 1,
	input: Type.Object({ list: Type.String() }),
	host: hostNamed("server"),
	variants: {
		viewer: { state: { rows: Rows } },
		editor: {
			state: { rows: Rows },
			methods: { add: method(Type.Object({ text: Type.String() })) },
		},
	},
});

/** Who may ask: the owner, a guest, or the server's own code. */
type Principal = "owner" | "guest" | "server";

function serveViews(api: Pick<Host<Principal>, "serve">): void {
	api.serve(Todos, ({ list }, principal, self) => {
		if (list !== "family") throw forbidden("This list is not shared");
		const store = self.get(TodoStore, { list });
		if (principal === "guest") {
			return { variant: "viewer", rows: store.rows };
		}
		return {
			variant: "editor",
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
trusted application code, and `"server"`, the host's own code: every host is
created with `self`, the principal its own roots and objects act as. Chord
invents no principals. The `Principal` type parameter of `createHost` and
`Host` makes `principal` in the factory that type, so TypeScript checks the
comparisons. `principalKey` maps identity to object identity. Real
applications should use stable identity, connection provenance, and grant
revision, not display names.

<!-- example:05-call -->
```ts
const host = createHost<Principal>({ name: "server", self: "server", principalKey: (principal) => principal });
host.serve(TodoStore, todoFactory);
serveViews(host);
const owner = await host.get(Todos, { list: "family" }, { principal: "owner" });
const guest = await host.get(Todos, { list: "family" }, { principal: "guest" });
assert.ok(owner.variant === "editor"); // narrows the reference to the editor variant
assert.equal(guest.variant, "viewer");
await host.root((ctx) => owner.add({ text: "Buy milk" }, ctx), { principal: "owner" });
assert.deepEqual(guest.rows.value, [{ text: "Buy milk", done: false }]);
// @ts-expect-error A viewer has no add: TypeScript refuses it, and so does the provider.
await assert.rejects(guest.add({ text: "Not allowed" }), (error) => isChordError(error, "not_in_variant"));
await assert.rejects(owner.add({ text: " " }), (error) => isChordError(error, "invalid"));
```

The owner gets `editor`; the guest gets `viewer`. Both see the same milk
todo. A reference is typed as the union of its variants: `add` is reachable only
after narrowing on `variant` (`assert.ok(owner.variant === "editor")` does that).
The guest's `add` is refused by TypeScript, and, called anyway, rejects with
`not_in_variant`. Whitespace-only text
rejects with `invalid`: it is a string, as the schema demands, but it breaks a
rule only the method knows. Use `invalid` for bad input and `forbidden` only
for callers who may not do something.

> **Why:** A variant is not all of authorization. The factory checks which
> list may be opened; the method checks the operation's arguments. Production
> code must also enforce grants that can change. Use
> `host.invalidatePrincipal(match)` to revoke matching objects; held references
> become `gone`. A UI watches `onStatus` and gets a new reference when appropriate.
> Guest-provided names or message text must never establish identity.

## 6. Reach the list from another process

A browser cannot call a host-only contract. `remote` contracts describe only
schema-checked state and methods that can travel as JSON. Our `Todos` view is
remote; the underlying `TodoStore` and database stay local. A caller never
names a host: `browser.get(Todos, …)` goes to `server` because the contract
says so, and the server refuses to serve, or to be asked for, a type it is not
the place of. A type that lives on one host per session says
`host: hostFamily("session:", "session")`: its input's `session` field picks
the host (`{ session: "S1" }` lives on `session:S1`).

A **link** carries ordered messages between hosts. A memory link runs both ends
in one test process, but uses the remote protocol. The accepting host stamps
the caller's principal from its authenticator, not from method arguments or a
client's claimed identity. The connecting side names the principal its parent's
own requests act as (`upstream: { link, principal }`, or `connect(link, {
principal })`).

<!-- example:06 -->
```ts
const server = createHost<Principal>({ self: "server", name: "server" });
server.serve(TodoStore, todoFactory);
serveViews(server);
const [down, up] = memoryLinkPair();
server.accept(down, { principal: "owner", kind: "client" });
const browser = createHost({
	self: "browser",
	name: "browser",
	kind: "client",
	upstream: { link: up, principal: "server" },
});
const todos = await browser.get(Todos, { list: "family" });
assert.ok(todos.variant === "editor");
assert.deepEqual(todos.rows.value, []);
const updated = Promise.withResolvers<void>();
const stop = todos.rows.subscribe((rows) => {
	if (rows.length === 1) updated.resolve();
});
await browser.root((ctx) => todos.add({ text: "Buy milk" }, ctx));
await updated.promise;
assert.deepEqual(todos.rows.value, [{ text: "Buy milk", done: false }]);
// Deliberately bypass TypeScript to simulate a malformed caller.
await assert.rejects(todos.add({ text: 123 } as never), (error) => isChordError(error, "invalid"));
stop();
// A held reference keeps its state without listeners.
assert.deepEqual(todos.rows.value, [{ text: "Buy milk", done: false }]);
todos.release();
```

The browser sees an empty snapshot, then the new milk todo. `ready` means
the remote reference has bound to a live object **and** has its state: every
state member of its variant has a snapshot. A held reference stays subscribed,
with or without listeners, until it is released.

What crosses the wire: the input and consumer's contract description, the
provider's shape (variant and members), method arguments and results, and the
state of the reference's variant. State starts with a **snapshot**, the whole current value;
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
const host = createHost({ self: "server" });
host.serve(TodoStore, todoFactory);
const observed = Promise.withResolvers<void>();
const seeded = Promise.withResolvers<void>();
const stopped = Promise.withResolvers<void>();
host.serve(Activity, (_input, _principal, self) => {
	const todos = self.get(TodoStore, { list: "family" });
	const seen = self.state("seen", Type.Number(), 0);
	self.on("rows", todos.rows, (rows, ctx) => {
		seen.replace(ctx, rows?.length ?? 0);
		if (rows?.length === 1) observed.resolve();
	});
	self.task(async (ctx) => {
		await todos.add({ text: "Review the list" }, ctx);
		seeded.resolve();
		await new Promise<void>((resolve) => {
			if (ctx.signal.aborted) resolve();
			else ctx.signal.addEventListener("abort", () => resolve(), { once: true });
		});
		stopped.resolve();
	});
	return { seen };
});
const activity = await host.get(Activity, {});
await Promise.all([seeded.promise, observed.promise]);
assert.equal(activity.seen.value, 1);
activity.release();
await stopped.promise;
```

The final `seen` is `1`. Each listener event receives a fresh root's
`ctx`; its write belongs to that short call tree. A task is not one enormous
root: Chord method calls made with its task context start fresh short roots.
We pass that context into `todos.add` so cancellation follows the task.
Releasing the activity reference aborts its task and resolves `stopped`.

`self.on(name, source, handler)` declares a listener; `self.task(fn)` a task.
A listener on state, like `rows` here, gets the current value when it starts,
then every change. It gets the current value again whenever a reload replaced
its source (a derivation is new at every reload), so its handler must
reconcile (`seen` is set from the rows, not counted up). Listeners can also
subscribe to a resource's event stream with `self.on(name, resource, select,
handler)`: `select` gets the opened resource and returns something with
`subscribe`; an event stream delivers no current value. Kept subscriptions
survive reload while the resource and selector remain unchanged; the handler
switches to new code. A selector that captures changing configuration should
get a new listener name. Tasks have no names: a reload restarts them all.

> **Why:** Do not wait for a person, sleep for minutes, or run an endless loop
> inside a method. That pins a root and can block state migration. Store a
> pending request in a cell and answer in another call, or use a task that obeys
> `ctx.signal`. Never retain a completed method's `ctx` for background work.

## 8. Package features as plugins

Now a plugin can contribute a menu action without editing a central switch.
A **registry** is a named table of contributions. A **facet** is a plugin's code
for one kind of host: it serves object types. A plugin can have server, worker, and browser
facets, each installing that part of the feature.

Registrations belong to objects of **lifetime `"host"`**: the host creates such
an object when its facet loads and keeps it until the host closes, even if no
screen asks for it. That keeps our menu contribution present. Objects of the
default lifetime, `"referenced"`, are still created only when referenced.

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
							return todos.openCount.value;
						},
					});
					return {};
				},
				{ lifetime: "host" },
			);
			click = () => api.root((ctx) => api.registry(Actions).get("addSample", ctx)!(ctx));
		},
		{ uses: [TodoStore] },
	),
};
const host = createHost({ self: "server" });
await host.load([menuFacet, storeFacet], { awaitHostObjects: false });
await host.ready();
assert.equal(await click!(), 1);
assert.equal(host.registry(Actions).table().size, 1);
```

Clicking returns `1`, and the registry has one entry. The menu's dependency
can come from a later facet in the load batch: `load` installs the whole
batch before waiting for host objects to activate. The facet declares `uses` so
reload can also check the contract it consumes.

The facet API supplies `serve`, `name`, `root`, and `registry`.
Our ordinary UI callback uses its saved `api.root`, not a process-global
host. Looking up a registry entry with `ctx` uses the table belonging to that
root's code version. Without `ctx`, lookup uses the current table. Duplicate
keys fail by default; `subscribe` can bridge tables to an imperative consumer.

Normally use `await host.load(facets)` (or `await host.install(facet)`),
which waits for those host objects. This example explicitly defers that barrier
with `awaitHostObjects: false`, then awaits `host.ready()`. That waits for a
snapshot of the host's objects, not for task completion or later loads.
Failures reject the readiness promise; abandoning startup requires closing the
host, because installation is not a rollback transaction.

> **Tip:** Use deferred readiness only when needed. A worker may have to await
> an independent local bootstrap reference, announce control readiness so its
> parent admits its link, and only then await `host.ready()`. Waiting for
> upstream-dependent host objects before admission would deadlock.

For real plugin files, default-export `defineFacet(...)`. Node hosts configure
`createHost({ loader: nodeLoader })`, with `nodeLoader` imported from
`@earendil-works/chord/node`, then pass module URLs to `load` and `reload`.
The in-memory facet objects here avoid filesystem setup. Built-in facets are
trusted in-process code, not a sandbox; the current Node loader keeps old module
copies in memory, so repeated loading has that limitation.

## 9. Change running code without losing the list

A reference is useful precisely because callers keep it while implementations
change. An **code version** identifies one committed set of code and registry tables.
A root keeps the code version it started with. New roots use the latest one.

### Compatible code change: no waiting

Give the same named facet a new factory. It changes the label but keeps the
cell declaration. This test deliberately pauses one caller to show what an
old root sees; application methods should not pause like this.

<!-- example:09-compatible -->
```ts
const host = createHost({ self: "server" });
const facet = (label: string): Facet => ({
	name: "todos",
	setup: (api) =>
		api.serve(TodoStore, (input, principal, self) => ({
			...todoFactory(input, principal, self),
			label: () => label,
		})),
});
await host.load([facet("Original")]);
const todos = await host.get(TodoStore, { list: "family" });
await todos.add({ text: "Buy milk" });
const entered = Promise.withResolvers<void>();
const resume = Promise.withResolvers<void>();
const oldRoot = host.root(async (ctx) => {
	const first = await todos.label(ctx);
	entered.resolve();
	await resume.promise; // Test-only pause: pin an old caller during reload.
	return [first, await todos.label(ctx)];
});
await entered.promise;
const compatible = await host.reload([facet("Updated")]);
assert.deepEqual(compatible.gated, []);
assert.equal(await todos.label(), "Updated");
resume.resolve();
assert.deepEqual(await oldRoot, ["Original", "Original"]);
assert.equal(todos.rows.value?.[0]?.text, "Buy milk");
```

Reload commits while the old root is paused: `gated` is empty. New calls see
`"Updated"`; the resumed old root sees `"Original"` twice. The milk row
survives. Compatible code changes do not wait for that old root to finish.

### State change: bump its version and migrate

Suppose a new policy converts existing todo text to uppercase. The schema is
unchanged, but the data's meaning changes. We still bump the cell's **state
version** (`self.state`'s `version` option, default 1). It belongs to one cell,
independently of the contract version. A **migration** (`migrate`) converts an
old value of that cell to the new representation.

<!-- example:09-migrate -->
```ts
const events: string[] = [];
const stopEvents = todos.rows.events((event) => events.push(event.type));
const migrated = await host.reload([
	{
		name: "todos",
		setup: (api) =>
			api.serve(
				TodoStore,
				todoStore({
					version: 2,
					migrate: (old, from) => {
						assert.equal(from, 1);
						return (old as Static<typeof Rows>).map((todo) => ({ ...todo, text: todo.text.toUpperCase() }));
					},
				}),
			),
	},
]);
assert.equal(migrated.gated.length, 1);
assert.deepEqual(todos.rows.value, [{ text: "BUY MILK", done: false }]);
assert.deepEqual(events, ["snap", "reset"]);
stopEvents();
```

The migration receives the old rows and their state version, `1`. It returns
new rows; the reference now reads `[{ text: "BUY MILK", done: false }]`.
Subscribers get a `reset` event containing the migrated value. The event
assertion sees an initial `snap`, then that `reset`.
One object is gated. A **gate** waits for calls already inside that object to
finish before migrating a private copy, validating it, and committing. Old
roots that had not entered it cannot later use old code over migrated data:
they get `upgrade_conflict` and should retry in a new root.

Changing a cell's schema also requires a version bump, and a migration unless
the old value already fits the new schema. A change of meaning with the same schema,
like this example, cannot be detected automatically. Real migrations must
reference each stored version they support, not assume every installation is
exactly one version behind.

### Contract change: keep an adapter for old callers

Rename `label` to `heading`. That is a breaking contract change, so use
contract version 2. The provider's `accepts[1]` adapter builds the implementation
that version-1 consumers still expect.

<!-- example:09-contract -->
```ts
// Remove label from the new provider's contract: it is now called heading.
const { label: _label, ...members } = TodoStore.def.members;
const RenamedStore = local("tutorial.todos", {
	version: 2,
	input: TodoStore.def.input,
	members: { ...members, heading: method(undefined, Type.String()) },
});
await host.reload([
	{
		name: "todos",
		setup: (api) =>
			api.serve(
				RenamedStore,
				(input, principal, self) => {
					const { label, ...implementation } = todoStore({ version: 2 })(input, principal, self);
					return { ...implementation, heading: label };
				},
				{
					accepts: {
						1: (current) => ({ ...current, label: current.heading }),
					},
				},
			),
	},
]);
assert.equal(await todos.label(), "Todos for family");
const newer = await host.get(RenamedStore, { list: "family" });
assert.equal(await newer.heading(), "Todos for family");
assert.equal(todos.rows.value?.[0]?.text, "BUY MILK");
```

The old reference's `label` and the new reference's `heading` both return
`"Todos for family"`. Both still reach the migrated rows. The adapter maps
implementations, not references; forwarding the existing method preserves its context.
We keep the cell at version 2 here so this code-only change does not repeat
migration.

> **Why:** Contract versions protect callers; state versions protect stored
> data; resource versions control reopening. Do not use one number for all
> three. Additive compatible contracts can keep their version; breaking shape
> or meaning changes need a contract bump and adapters for old consumers.
> Reload prepares candidates first; preparation failure leaves the old code
> running. A migration gate that misses its deadline aborts rather than
> switching data underneath active old code.

## 10. Test the objects, not a whole deployment

Most implementation needs only a bare host. Use real factories for state tests, and a
fake facet when you want to test delegation without a real database or service.
Here the fake records what the editing view sends to the store.

<!-- example:10 -->
```ts
const host = createHost<Principal>({ name: "server", self: "server", dev: true });
const received: string[] = [];
const fake: Facet = {
	name: "fake-store",
	...defineFacet((api: FacetApi) => {
		api.serve(TodoStore, (input, principal, self) => ({
			...todoFactory(input, principal, self),
			add: ({ text }) => {
				received.push(text);
			},
		}));
	}),
};
await host.load([fake]);
serveViews(host);
const owner = await host.get(Todos, { list: "family" }, { principal: "owner" });
assert.ok(owner.variant === "editor");
await owner.add({ text: "Test delegation" });
assert.deepEqual(received, ["Test delegation"]);
await assert.rejects(owner.add({ text: "" }), (error) => isChordError(error, "invalid"));
owner.release();
await assert.rejects(owner.add({ text: "Too late" }), (error) => isChordError(error, "released"));
```

The fake received `["Test delegation"]`. Empty text failed before reaching
the fake. The released reference rejects further calls with `released`.
`isChordError(error, code)` checks a stable error code; avoid testing only a
message's wording.

Our other tests exercise the real cells (section 3), resource cleanup (4),
principal variants (5), a client over a memory link (6), and callers kept through
reload (9). After an awaited `get` the state is there; for later changes, await
the value you need. Always unsubscribe and close hosts; leaked references can hide
lifetime bugs or leave background tasks running.

> **Tip:** A fake must honor the contract it serves. This fake delegates all
> ordinary members to `todoFactory` and replaces only `add`; it deliberately
> objects calls rather than updating rows. Do not confuse that with persistence.

## 11. Keep these habits

A temporary call reference should not accidentally become a permanent one. A
screen should not lose its data merely because a button click finishes. Use
`ctx.get` for the first lifetime and `host.get` for the second.

<!-- example:11 -->
```ts
const host = createHost({ self: "server" });
host.serve(TodoStore, todoFactory);
const screen = await host.get(TodoStore, { list: "family" });
await host.root(async (ctx) => {
	const temporary = await ctx.get(TodoStore, { list: "family" });
	await temporary.add({ text: "Keep roots short" }, ctx);
}); // The temporary reference is released here; screen still holds the store.
assert.equal(screen.openCount.value, 1);
screen.release(); // No reference remains; without persistence, disposal loses these rows.
```

The screen still sees count `1` after the root finishes, because it owns a
separate reference. When the screen releases it, no reference remains. This tutorial's cells
are in memory: reload preserves a live object, but disposal or process restart
loses its rows. Real persistence belongs in a database resource, with an
explicit load/save policy.

### Checklist and common mistakes

- Keep reloadable state in cells, not closure variables: factories rerun.
- Change drafts, not published values: mutation outside cells bypasses updates.
- Use `change` for field edits and `replace` for owned snapshots: replacing
  can erase fields your code does not know about.
- Declare dependencies in a synchronous factory, not during methods: activation
  and reload need a complete declaration list.
- Use `ctx.get` for temporary method dependencies: their references end with the call.
- Pass `ctx` into nested calls: cancellation and code versions must stay together.
- Keep roots short and tasks cancellable: migration and shutdown need work to settle.
- Check grants and arguments, not just variants: available methods are not a full policy.
- Stamp principals at trusted ingress, not from client payloads: names are not identities.
- Await `get` before reading state: a reference you hold is live and hydrated, a
  loading one (`host.hold`) throws `not_ready`.
- Release references and unsubscribe: otherwise unused objects remain referenced or observed.
- Bump state versions, contract versions, and resource versions for their own changes:
  each protects a different boundary.
- Await host object readiness before reporting startup success: declared is not yet live.
- Keep reference dependencies acyclic: an object cannot wait for itself through another object.

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
	createHost,
	defineFacet,
	defineRegistry,
	type Facet,
	type FacetApi,
	type Factory,
	forbidden,
	type Host,
	hostNamed,
	invalid,
	isChordError,
	local,
	memoryLinkPair,
	method,
	opaque,
	remote,
	type StateOptions,
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
