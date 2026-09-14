# Chord: Application-Composition Runtime

Source: `packages/chord/README.md`, `src/delta/README.md`, `PLANNING.md`
Not a Pi package: `@earendil-works/chord` is an application-neutral runtime that depends on no other Pi workspace package, and it is not covered by the Pi user docs. `PLANNING.md` is an active implementation plan, not a stable API contract.

---

> **Auto-built from individual doc pages.**
> Sources: <https://raw.githubusercontent.com/earendil-works/pi/main/packages/chord/README.md>, <https://raw.githubusercontent.com/earendil-works/pi/main/packages/chord/src/delta/README.md>, <https://raw.githubusercontent.com/earendil-works/pi/main/packages/chord/PLANNING.md>

## Overview

Chord is an application-composition runtime for systems assembled from
plugins/extensions. It provides facets, services, replicated state, and a
pluggable remote-service boundary. It is developed as a standalone package in
the Pi monorepo, but it is not a Pi package: it does not depend on any other Pi
workspace package and can be used by unrelated applications.

## What Chord is for

A single application feature may need to run in several environments: for
example, an agent worker, a terminal UI, and a remote WebUI.  Chord provides the
generic machinery to write such extensions in a way that is both delightful for
humans as well as agents.

The design has a few connected pieces:

- **Plugins** are synchronous setup units that declare the services they provide
  and require. After every plugin has declared its shape, a host validates the
  complete dependency graph, binds services, activates providers before consumers,
  and disposes resources in reverse dependency order.  These units are called
  *facets*.

- **Facets** are parts of a plugin.  Each facet is bundled up separately and runs
  in the process or environment where it's supposed to run.  You can use facets
  to split a plugin into separate pieces that need to be loaded into different
  processes and environments (think backend, browser, TUI etc.)

- **Services** are typed, stable tokens with either one provider (**singleton**)
  or dynamic keyed instances (**keyed**).  A service can be process-local, with
  an unrestricted JavaScript contract, or remotely exposable. Consumers retain a
  stable facade while a provider disconnects or is replaced.

- **Replicated state** exposes authoritative state to local and remote
  connected consumers. Producers mutate the tracked `state` proxy and call
  `publish(context)`; consumers receive complete immutable values. Chord flushes
  one decoded operation batch per publication, while each remote client/state
  stream owns independent path-codec state. Replicas become unready on disconnect
  or replacement until they are rehydrated.

- **Delta tracking** derives compact operations from tracked plain JSON at
  flush time. It preserves string append/front-truncation and array-append
  behavior without retaining mutation history, supports durable base batches,
  and validates untrusted operations as they are applied.

- **Remote service sources** advertise services available outside a facet host
  and open bindings for the services its facets require. Bindings carry logical
  calls and subscriptions through an application-supplied adapter. Chord
  requires strict-JSON arguments, results, snapshots, updates, and catalogues,
  but does not prescribe framing, routing, transport, or an application wire
  envelope. `JsonRepresentation<T>` derives a wire-safe type for application data
  with unknown payloads, while `isJsonValue()` validates received values at an
  adapter boundary. Symmetric RPC peers are planned as one optional
  implementation of this boundary.

- **Context** Chord provides a Go-like context system for cancellation and
  invocation-scoped application values. Applications can carry permissions or
  telemetry through those values without Chord depending on either.

The current runtime exports service tokens, singleton and keyed providers,
remote bindings, replicated state, facet hosts, and facet loaders from
`@earendil-works/chord`. Import public types and general runtime APIs from the
package root. Context constants and functions live in
`@earendil-works/chord/context` because their generic names should not pollute
the root API.
Chord-owned identifiers use the `chord.*` namespace and its reserved service
prefix is `$chord.*`.

## Remote service adapters

Chord owns its transport-independent service wire grammar. Consumer adapters
use `createServiceCatalogueCall()`, `createServiceSubscribeCall()`, and
`createServiceUnsubscribeCall()` for `$chord.service` control calls.
`createRemoteServiceEndpoint()` handles those calls for one provider consumer,
including subscription activation and cleanup. `parseServiceCall()`,
`parseServiceCatalogue()`, and the decoded/wire snapshot and update parsers
validate Chord semantics after an adapter has established a strict-JSON
boundary. `RemoteServiceErrorCode` and `REMOTE_SERVICE_ERROR_CODES` define the
service errors that may cross that boundary.

Replicated state operations use one `createServiceStateEncoder()` at the
provider side and one `createServiceStateDecoder()` at the consumer side for
each subscription. Those registries create an independent Delta path dictionary
for every instance/member state and reset it on replacement, unavailability,
close, or fresh hydration. Applications may place these values inside any
routing, request, response, or event envelope; Chord does not prescribe that
outer protocol.

## Tracking JSON deltas

Import the standalone delta primitive from `@earendil-works/chord/delta`:

```ts
import { apply, track } from "@earendil-works/chord/delta";

const changes = track({ output: "", count: 0 });
changes.flush(); // opening base batch
changes.state.output += "done\n";
changes.state.count += 1;

const ops = changes.flush();
const replica = apply({ output: "", count: 0 }, ops);
```

The first flush is always a complete base batch. Later flushes contain path-based
changes. `applyImmutable()` applies those batches while preserving prior replica
revisions. `replicatedState(initial)` uses tracking directly:

```ts
const status = env.replicatedState({ output: "", count: 0 });
status.state.output += "done\n";
status.state.count += 1;
status.publish(context);
```

`publish()` flushes once; remote connection plumbing encodes that operation batch
independently for every client/state pairing. String assignments preserve pure
appends and rolling-window movement as append and front-truncate operations;
unrelated rewrites fall back to a set. Values inserted into tracked state become
tracker-owned and must subsequently be mutated only through `state`. See the
[Delta guide](src/delta/README.md) for mutation, array, lifecycle, and
consumer-ownership rules.

## Bundling and loading facets

`@earendil-works/chord/bundler` uses esbuild to turn ESM or TypeScript application
entries into independent, content-addressed CommonJS files. The package-level API
reads plugin identity and build configuration from `package.json`, then applies
facet path conventions supplied by the host application:

```json
{
  "name": "@example/my-plugin",
  "version": "1.0.0",
  "type": "module",
  "peerDependencies": {
    "@earendil-works/chord": "^0.84.4"
  },
  "chord": {
    "facets": {
      "worker": "./src/custom-worker.ts",
      "presentation": false
    }
  }
}
```

```ts
import { bundleFacetPackage } from "@earendil-works/chord/bundler";

await bundleFacetPackage({
 packagePath: "/path/to/my-plugin",
 outdir: "/application-owned/plugin-builds/my-plugin",
 defaultFacets: {
  worker: "src/worker.ts",
  presentation: "src/presentation.ts",
 },
});
```

Existing conventional files become entries unless `chord.facets` overrides or
disables them. Peer dependencies are externalized and resolved against the host
when loading. Chord never installs dependencies or runs package lifecycle
scripts. `bundleFacets()` remains available as the lower-level API for callers
that already have explicit plugin identity and entry mappings.

The output directory contains one `.cjs` file per entry plus
`chord-facets.json`. Load one application-selected entry through the Node-only
loader:

```ts
import { createFacetBundleLoader } from "@earendil-works/chord/node";

const loader = createFacetBundleLoader({
 manifestPath: "/application-owned/plugin-builds/my-plugin/chord-facets.json",
 entry: "worker",
 resolveExternal: (specifier) => import.meta.resolve(specifier),
});
const loaded = await loader.load();
```

Each `load()` verifies SHA-256 integrity and compiles the CommonJS body directly
with `node:vm` instead of putting the plugin into Node's CommonJS or ESM module
cache. Externals are resolved by the host and loaded through a restricted
`require`; esbuild lowers dynamic imports so they use the same path. Disposing a
retired generation releases the loader's facet references, making its compiled
code eligible for garbage collection once plugin-owned resources are also gone.

For transport to another Node host, `readFacetBundleArtifact()` packages one
verified manifest entry with its source, and `createFacetBundleArtifactLoader()`
materializes fresh temporary generations while resolving externals against the
receiving host.

To reload, load a candidate, pass its facets to `FacetHost.reload()`, dispose the
candidate on failure, and dispose the retired `LoadedFacets` only after a
successful cutover. The host activates and validates the candidate while the old
providers remain routed, then replaces each singleton directly without an
unavailable interval. Stable service handles therefore do not become disconnected
during an ordinary reload. Keyed instances
remain incarnation-specific and replacements receive fresh generations. The
bundler writes a complete temporary directory before replacing the previous
output, so loaders do not observe partially built generations.

See [PLANNING.md](PLANNING.md) for the broader RPC and generation-loading
architecture.

---

## Delta Tracking

Chord Delta synchronizes JSON values from an authoritative producer to an
ordered replica. It is available from `@earendil-works/chord/delta`.

A change is represented by an `Op`: a JSON tuple for replacing, setting,
deleting, updating a string, or splicing an array. Producers use `track()`;
replicas use `apply()` or `applyImmutable()`.

```ts
import { apply, track } from "@earendil-works/chord/delta";

const tracker = track({ output: "", entries: [] as string[] });
let replica = apply(undefined, tracker.flush());

tracker.state.output += "done\n";
tracker.state.entries.push("result");
replica = apply(replica, tracker.flush());
```

The first `flush()` returns one operation containing the complete value. Each
later flush returns the operations needed to transform the previously published
value into the current value. It returns `[]` when the value has not changed.

`applyImmutable()` copies only containers along changed paths and shares
unchanged subtrees. It does not mutate, clone, or freeze either complete input.
Chord's replicated-state producers mutate a tracked proxy and publish operation
batches; consumers still observe complete immutable values.

## Sending or storing changes

`flush()` produces decoded `Op[]` with complete paths. This is convenient for
local use but repeats long paths on the wire or disk.

`encoder()` compresses those paths and returns `WireOp[]`. `decoder()` validates
the encoded tuples, restores complete paths, and returns the `Op[]` required by
`apply()`:

```ts
import { apply, decoder, encoder, track } from "@earendil-works/chord/delta";

const tracker = track({ output: "" });
const enc = encoder(); // producer side
const dec = decoder(); // consumer side
let replica: { output: string } | undefined;

const send = () => {
 const ops = tracker.flush();
 const wire = enc.encode(ops); // serialize or store WireOp[] here
 const received = dec.decode(wire);
 replica = apply(replica, received);
};
```

Encoding is optional for local application. Never pass `WireOp[]` directly to
`apply()`.

An encoder and decoder are stateful. Use one pair for each ordered stream. The
encoder assigns numeric IDs to paths used across batches; the decoder remembers
the corresponding definitions. A complete-value operation resets both path
dictionaries, so replay can begin at that batch with a fresh decoder.

Path omission is local to one batch. Numeric path IDs may span batches. Each
independently hydrated replicated-state stream needs its own encoder and decoder.
Do not share a pair between state members or subscriptions, even when their
batches use the same ordered transport connection.

## Operation vocabulary

A path is an array of object keys and array indices:

```ts
["operation", "message", "content", 0, "text"]
```

### Decoded `Op`

`track().flush()` returns these tuples, and `apply()` accepts them:

| Tuple | Meaning |
| --- | --- |
| `["r", value]` | Replace the complete value. |
| `["s", path, value]` | Set a property or array element. |
| `["d", path]` | Delete an object property. |
| `["a", path, text]` | Append to a string. |
| `["t", path, count]` | Remove UTF-16 code units from a string's front. |
| `["p", path, index, remove, items]` | Splice an array. |

Except for `r`, every decoded operation carries its complete path. `s`, `d`,
`a`, and `t` cannot address the root. `p` may address a root array.

### Encoded `WireOp`

A `PathRef` is either an inline path or a non-negative numeric path ID.
`WireOp` supports the following tuples:

| Tuple | Meaning |
| --- | --- |
| `["r", value]` | Complete replacement; identical to decoded form. |
| `["#", id, path]` | Define a numeric path ID. |
| `["s", pathRef, value]` | Set with an inline or interned path. |
| `["s", value]` | Set using the previous path in this batch. |
| `["d", pathRef]` | Delete with an inline or interned path. |
| `["d"]` | Delete using the previous path. |
| `["a", pathRef, text]` | Append with an inline or interned path. |
| `["a", text]` | Append using the previous path. |
| `["t", pathRef, count]` | Front-truncate with an inline or interned path. |
| `["t", count]` | Front-truncate using the previous path. |
| `["p", pathRef, index, remove, items]` | Splice with an inline or interned path. |
| `["p", index, remove, items]` | Splice using the previous path. |

For example, adjacent decoded operations on one path:

```ts
[
 ["t", ["output"], 200],
 ["a", ["output"], "next chunk"],
]
```

encode to:

```ts
[
 ["t", ["output"], 200],
 ["a", "next chunk"], // reuses ["output"]
]
```

When `output` is used again in a later batch, the encoder defines an ID on its
second explicit use:

```ts
[
 ["#", 0, ["output"]],
 ["a", 0, "more"],
]
```

Later batches can use `0` directly until a complete-value operation resets the
dictionary.

## Producing changes

Read and mutate `tracker.state` as a normal object:

```ts
tracker.state.status = "running";
tracker.state.settings.theme = "dark";
tracker.state.messages.push(message);
delete tracker.state.retry;
```

Only the value at flush time is published:

```ts
tracker.state.status = "starting";
tracker.state.status = "running";
tracker.flush(); // one set to "running"
```

Replacing an object or array is valid. Delta compares its properties and elements
with the previously published value:

```ts
tracker.state.settings = {
 ...plainSettings,
 theme: "dark",
};
```

Unchanged properties produce no operations. Changed nested strings and arrays
still use string and splice operations.

### Strings

Appending text produces an `a` operation:

```ts
tracker.state.output += "next line\n";
```

Moving a bounded text window forward produces `t` followed by `a` when the old
suffix matches the new prefix:

```ts
tracker.state.output = tracker.state.output.slice(200) + nextChunk;
```

An unrelated replacement produces `s`.

### Arrays

Use normal array methods:

```ts
tracker.state.messages.push(first);
tracker.state.messages.push(second);
tracker.state.messages.splice(3, 1, replacement);
```

All `push()` calls before one flush produce one tail `p`. Changes to older
elements remain separate, regardless of whether they happen before or after the
pushes. Changes to newly pushed elements are included in the pushed values.

Front or middle insertion, removal, sorting, reversing, `fill()`, and
`copyWithin()` are supported. A structural change combined with edits to elements
whose indices moved may compare and publish the retained suffix positionally:

```ts
tracker.state.items.shift();
tracker.state.items[0].status = "changed";
// A shift followed by push in the same flush has the same issue.
```

The emitted data can then scale with the retained suffix, or with the complete
array, rather than only the changed element. When batching is under your control,
flush the structural change before editing elements at their new indices.

Sparse arrays are unsupported. Writing beyond the next index throws. Increasing
`length` creates explicit `null` elements; decreasing it removes elements.

`fill()` and `copyWithin()` keep normal JavaScript reference semantics. Do not use
them to place one mutable object at multiple live paths.

### Optional properties

Optional object properties use absence. They do not require `null`:

```ts
type Settings = { label?: string; count: number };
const tracker = track<Settings>({ count: 0 });

tracker.state.label = "active";
tracker.state.label = undefined; // produces d
// `delete tracker.state.label` is equivalent
```

`undefined` is accepted only as assignment syntax for deleting an object
property. It is not a JSON value. Initial and assigned objects cannot contain own
`undefined` values, and array elements cannot be `undefined`. Use `null` when an
array position or explicit empty value must remain present.

## State ownership

The object passed to `track()` becomes tracker-owned. The same applies to objects
later assigned into state or inserted into arrays.

After insertion, a retained reference may be read but must not be mutated or
inserted at another live location. The tracker relies on this ownership rule; it
does not recursively validate values or detect aliases:

```ts
const item = { status: "new" };
tracker.state.item = item;

tracker.state.item.status = "ready"; // supported: tracked mutation
item.status = "broken"; // unsupported: bypasses tracking
tracker.state.other = item; // unsupported: one object at two live paths
```

The same restriction applies across separate array calls:

```ts
tracker.state.items.push(item);
tracker.state.items.push(item); // unsupported alias
```

Use distinct objects when values must appear at multiple paths. Perform
mutations through `tracker.state`; do not put a proxy read from `tracker.state`
back into tracked state.

Tracked state must be a mutable JSON tree:

- strings, booleans, finite numbers, `null`, arrays, and plain objects;
- no cycles or one mutable object stored at multiple locations;
- no sparse arrays, accessors, frozen objects, symbols, classes, functions,
  `Map`, or `Set`.

Do not keep a child proxy across an array operation that changes indices. Read
the child again from its new index.

## Tracker lifecycle

```ts
tracker.flush(); // publish changes since the previous flush
tracker.rebase(); // make the next flush a complete replacement
tracker.discard(); // accept current changes without publishing them
tracker.state = replacement; // replace the root; next flush is complete
```

`discard()` intentionally prevents current changes from reaching existing
replicas. Use it only when those replicas do not need the discarded changes.

`apply()` adopts object and array payloads from its input batch. Do not freeze a
batch before applying it, and do not apply one in-memory batch to multiple
mutable replicas unless each replica owns that batch. A serialized and decoded
batch is already detached. `applyImmutable()` instead treats its previous value
and operation payloads as immutable, so one batch can safely fan out in-process.

A `decode()`, `apply()`, or `applyImmutable()` error terminates that stream.
Discard its decoder and replica, then recover from a later base batch. `apply()`
is not transactional; operations before the failing operation may already have
changed the replica.

## Limits

- Delta assumes one authoritative writer and ordered delivery. Sequence numbers,
  gap detection, retries, and persistence policy belong to the surrounding
  protocol or storage format.
- Object identity is not replicated. Tracked mutable state must be a tree;
  immutable inputs may share references, but replicas need not preserve them.
- Object key insertion order is not replicated. Do not compare or hash replicas
  using serialized key order.
- Array operations that change indices may publish a wider array region, as
  described under Arrays.
- Object-valued keys named `__proto__`, `constructor`, or `prototype` can be read
  and serialized, but cannot be mutated through that key. Replace the nearest
  ordinarily named parent instead.

---

## Implementation Plan

## 1. Goal

Chord will be the application-neutral foundation for:

1. loading, composing, unloading, reloading, and bundling plugins;
2. declaring and consuming local or remote services;
3. transporting service calls and subscriptions over symmetric RPC plumbing; and
4. replicating authoritative latest-value state to local and remote consumers.

The current Pi experiments prove many required behaviors, but Chord will be implemented from scratch. Existing source may be used as test and design evidence, not copied into this package. Compatibility with experimental APIs or wire messages is not a requirement.

## 2. Dependency boundary

The dependency direction is strict:

```text
@earendil-works/chord
        ↑
Pi agent, protocol, server, coding agent, TUI, and future applications
```

Chord must:

- have no dependency on another Pi workspace package;
- contain no imports from `@earendil-works/pi-*` or relative paths outside `packages/chord`;
- use application-neutral vocabulary in source, errors, tests, and examples;
- own any generic runtime types required by its public API, including strict JSON values and invocation cancellation context;
- keep Node-specific loading and bundling separate from the platform-neutral runtime; and
- be buildable, testable, packable, and usable without resolving another Pi package.

A generic third-party dependency is not prohibited, but each dependency must be justified. The runtime should initially prefer standard JavaScript APIs. The bundler may use one pinned implementation behind a Chord-owned adapter.

The following terms must not become Chord concepts: Session, Harness, AgentLane, server, client, attachment, TUI, model, tool, hook, provider credential, or workspace. Those belong to consumers.

## 3. Architectural model

### 3.1 Working vocabulary

The names below are provisional, but the distinctions are required.

- **Plugin**: one independently activated composition unit with a stable ID and synchronous setup function.
- **Plugin module**: a JavaScript module exporting one or more plugins for one application-selected entry.
- **Loaded generation**: plugins plus the resources owned by loading their module generation.
- **Host**: one assembled plugin and service graph.
- **Service token**: a stable runtime service ID plus type information and locality policy.
- **Provider**: the owner of one singleton service or one keyed service collection.
- **Connection**: a transport-neutral source of services outside the current host.
- **Peer**: one endpoint of a symmetric RPC channel. Either peer may provide and consume services.
- **Replicated state**: initialized mutable source state with read-only local or remote replicas.

A product feature may ship multiple plugin-module entries for different application environments. Chord does not group those entries into a cross-process runtime object and does not interpret their entry names.

### 3.2 Layering

The implementation should be divided into these layers:

```text
plugin loader and bundler
        ↓
plugin host, lifecycle, and dependency graph
        ↓
service tokens, providers, facades, and keyed instances
        ↓
replicated state and service subscriptions
        ↓
symmetric RPC peer and transport adapter
        ↓
strict JSON, invocation context, cancellation, and errors
```

The local service path must not require RPC serialization. The remote path must use the same service semantics through a strict wire boundary.

## 4. Invocation context and strict JSON

Current experiments depend on Pi's Harness `Context`, which Chord cannot import. Chord therefore needs a small neutral invocation context.

The initial context should provide:

- an optional `AbortSignal` for cancellation of one invocation or observation;
- immutable typed local values through Chord-owned context keys;
- a background root;
- child derivation, cancellation, and cancellation-aware waiting helpers; and
- no built-in telemetry, identity, authentication, or application values.

Applications may define their own context keys. A Pi adapter can carry telemetry and authenticated identity through such keys without Chord knowing their types.

A context object never crosses RPC as a business value. The calling peer sends cancellation control and, if configured, an opaque strict-JSON metadata carrier. The receiving adapter constructs a fresh local context. The adapter, not remote business arguments, installs authenticated local identity.

Chord owns the static `JsonValue` contract and provides `JsonRepresentation<T>` plus `isJsonValue()` for adapter boundaries. The service runtime deliberately performs no automatic recursive validation; concrete serializers remain responsible for rejecting unsupported values. Remote arguments, results, errors, snapshots, updates, catalogues, and RPC envelopes are expected to be finite strict JSON:

- finite numbers only;
- no `undefined`, sparse arrays, symbols, prototypes, cycles, classes, functions, `Map`, or `Set`; and
- `null`, rather than `undefined`, for business-level absence.

Application schema validation remains the application's responsibility. Chord validates structural control envelopes, but runtime enforcement of the strict-JSON boundary is currently deferred to serializers.

## 5. Plugins and lifecycle

### 5.1 Plugin shape

The intended author model is equivalent to:

```ts
interface Plugin {
  readonly id: string;
  setup(environment: PluginEnvironment): void;
}
```

Setup is synchronous declaration. It may:

- provide a singleton service;
- declare ownership of a keyed service;
- acquire a singleton service handle;
- declare an observation of keyed service instances;
- create replicated state;
- register an activation callback;
- register owned resource cleanup; and
- register final deactivation work.

Setup must not:

- invoke a service or read replicated state through an acquired facade;
- perform asynchronous work;
- introduce a new service dependency later from an event handler or activation callback; or
- mutate the active host generation.

The host records setup calls in a private generation ledger. Plugin authors do not maintain a parallel `requires`/`provides` manifest.

### 5.2 Assembly

After every plugin has completed setup, the host must:

1. collect local provisions and catalogues from configured remote service sources;
2. resolve every hard requirement to exactly one local or connected provision;
3. reject missing providers, duplicate providers, ambiguous source offers, and singleton/keyed mismatches;
4. reject duplicate plugin IDs;
5. derive provider-to-consumer lifecycle edges;
6. reject dependency cycles;
7. construct local and remote service bindings while handles are still inaccessible;
8. hydrate required connected services; and
9. activate providers before consumers.

A plugin may provide and consume the same token without creating a self-cycle. Optional dependencies are not part of the first contract; they require a distinct acquisition API later.

### 5.3 Resource ownership

Every plugin generation owns:

- activation callbacks;
- explicit cleanup functions;
- keyed instances added through its provider handle;
- keyed observations and their tasks; and
- service provisions.

Disposal is idempotent. Consumers deactivate before providers, and each plugin's resources dispose in reverse registration order. Cleanup continues after individual failures and reports one error or an `AggregateError` after all cleanup attempts finish.

Keyed observation handlers receive a fresh cancellable context. Closing or replacing the instance aborts only that handler task. A handler failure is reported through host policy unless its context was cancelled as normal cleanup.

### 5.4 Loaded module generations

Module loading and plugin activation are separate ownership domains:

```ts
interface LoadedPlugins {
  readonly plugins: readonly Plugin[];
  dispose(): Promise<void>;
}

interface PluginLoader {
  load(): Promise<LoadedPlugins>;
}
```

Required loaders:

- a static loader for built-ins and tests;
- an ordered combined loader with reverse disposal and startup-failure cleanup; and
- a bundle/module loader for one selected manifest entry.

The loader owns one source generation. The host owns active plugin lifecycles. A coordinator must deactivate a retired generation before disposing its `LoadedPlugins`.

Node's default ESM loader retains every imported module generation in its process-wide cache. Chord therefore bundles Node facets as CommonJS and compiles each generation directly with `node:vm`, without inserting plugin code into either Node module cache. Chord's unload contract remains deactivation, removal of service reachability, cleanup, and release of loader-owned references/resources. Once no plugin-created timer, listener, callback, or other escaped reference remains, V8 can garbage-collect the compiled generation; collection timing is not deterministic.

## 6. Loading, unloading, and reload

### 6.1 Host updates

Host updates are serialized and have two forms.

#### Shape-preserving replacement

A targeted replacement is shape-preserving when each replaced plugin keeps the same:

- plugin ID;
- required service IDs and modes;
- provided service IDs and modes; and
- remotely exposable singleton member names and kinds.

The sequence is:

```text
load replacement module generation
→ run replacement setup
→ validate replacement shape and remote implementations
→ activate replacements in dependency order while the old providers remain routed
→ replace each local or remote singleton directly without withdrawing it
→ deactivate replaced plugins in reverse dependency order
→ dispose the retired loaded generation
```

Properties:

- existing local and remote singleton facades keep object identity;
- captured local and remote methods dispatch to the old provider before cutover and the replacement after cutover;
- replicated-state facades install the replacement snapshot without becoming unhydrated;
- every singleton switches directly from its old target to its replacement, but a multi-service reload is not graph-transactional;
- keyed instances from the old plugin close; instances staged by the replacement use fresh generations;
- setup, shape-validation, or replacement-activation failure leaves the active generation unchanged;
- named host resources acquired during activation support overlapping staged replacements, so candidate cleanup restores the old registration and retired cleanup cannot remove the replacement; and
- any failure after replacement begins terminates the host rather than attempting to preserve a partially transitioned graph.

There is no rollback after cutover. Terminal cleanup revokes every facet handle before best-effort disposal; only pre-cutover candidate cleanup and ordinary host disposal guarantee dependency-ordered cleanup. Committed application effects are outside the reload transaction.

#### Structural replacement

Adding or removing plugins, changing service shape, or changing connection selection is structural. The first implementation should replace the complete host generation rather than attempt a partial affected-subgraph update:

```text
load and synchronously set up the complete desired generation
→ resolve and validate its graph without activation effects
→ begin cutover
→ withdraw old providers and deactivate the old graph
→ install and activate the new graph
→ dispose the old loaded generation
```

Rules:

- validation failure before cutover leaves the old graph active;
- after cutover starts, failure disposes the complete host because the retired graph cannot be restored;
- removing a provider while retaining a hard consumer is rejected during candidate validation;
- service facades owned outside plugin lifecycles remain stable when service ID and mode survive the replacement;
- removed services become permanently disconnected for the retired generation; and
- a future optimization may retain unaffected plugins, but it is not required for the initial structural update.

This full-generation path supplies actual plugin load and unload semantics without first implementing a complex partial-graph transaction.

### 6.2 Calls during unload

Replacement never leaves a singleton facade without a target: an invocation resolves either the old implementation or its replacement. Work already running in a retired facet is not drained; later use of that facet's revoked handles may fail as stale work. A future killable-isolate host terminates such work directly. Transport disconnect still cancels only connection-owned invocations; it does not imply application-level cancellation or rollback.

### 6.3 Update failure reporting

An update result must distinguish:

- load failure;
- setup or graph validation failure before cutover;
- old-generation deactivation failure;
- replacement activation failure;
- service rebinding failure; and
- retired loader disposal failure.

Multiple failures are aggregated without hiding the first transition failure. Concurrent update, unload, and host-dispose requests are serialized or rejected with a stable lifecycle error.

## 7. Services

### 7.1 Tokens and modes

A service token has:

- a non-empty stable string ID;
- a TypeScript contract type;
- a locality policy: remotely exposable by default or explicitly process-local; and
- no provider instance of its own.

Chord reserves a prefix for control-plane IDs. Duplicate IDs in one catalogue are invalid.

Two modes are required:

- **singleton**: one provider, many consumers; and
- **keyed**: one collection owner, dynamic instances, many observers.

One token has one mode in one host graph. Mixing singleton and keyed use is an assembly or protocol error.

### 7.2 Local services

Process-local services:

- may expose arbitrary objects, synchronous methods, classes, functions, native handles, or non-JSON values;
- are never included in a remote catalogue;
- use the same graph ordering, stable handles, keyed generations, and lifecycle behavior as remote services; and
- are trusted composition, not a security boundary.

A local singleton consumer receives a stable lazy facade, not the provider object. This removes setup-order dependence and lets provider replacement update captured methods.

Remotely exposable services use the provider/binding path even when provider and consumer share a host. An internal loopback binding keeps replacement, replicated-state, and keyed-generation semantics independent of placement. Only explicitly process-local services bypass that path.

### 7.3 Remote service contracts

A remotely exposable implementation may contain only own data properties classified as:

- asynchronous methods whose business arguments and result are strict JSON, with one Chord invocation context in the declared position; or
- branded replicated-state values.

The provider derives a runtime member table from the implementation. Plugin authors do not maintain a second method/state descriptor. Unsupported accessors, fields, or member kinds are rejected before publication.

Type-level checks should reject obviously invalid remote contracts. Runtime checks remain mandatory because types do not authenticate peers or survive JavaScript consumption.

Remote methods:

- return promises;
- return strict JSON or `void`;
- receive a fresh local invocation context;
- map caller cancellation to exactly one request;
- do not queue while disconnected; and
- expose stable error codes and sanitized messages across the wire.

Arbitrary returned object references, callbacks, function serialization, and general object-graph remoting are outside the initial scope.

### 7.4 Stable singleton facades

`use(token)` returns a facet-owned capability view over a source-independent host service slot. Repeated acquisition within one facet returns the same view; different facet lifecycles receive different views. Member slots are created lazily on property access and validated against provider metadata when bound.

Required behavior:

- inaccessible during setup and after the owning facet lifecycle ends;
- directly bound after local graph assembly or remote hydration;
- stable across provider withdrawal and replacement;
- method invocation fails while disconnected;
- state reads return `undefined` while unhydrated;
- a remotely exposable replacement preserves the complete member name/kind table; and
- a provider omitting an already-accessed member is a binding error.

### 7.5 Keyed services

`provideMany(token)` declares one keyed owner during setup and returns a generation-owned `ServiceSpawner`. While active, `spawn(key, implementation)`:

- requires a non-empty key unique among live instances;
- creates a host-owned monotonically increasing generation for that key;
- publishes methods and initial state atomically;
- returns an idempotent close function; and
- is automatically closed during plugin disposal.

An instance address is `(service ID, key, generation)`. Reusing a closed key creates a new generation. Stale facades cannot call the replacement.

`observe(token, handler)`:

- reconciles a complete initial instance directory;
- starts one task per instance only after all initial state members hydrate;
- preserves ordered additions, replacements, and removals;
- aborts the instance task on close, replacement, disconnect, or observation disposal;
- gives each observation an observer-lifetime service view that becomes inaccessible when its task is aborted; and
- never represents service facades inside replicated JSON state.

## 8. Replicated state

Replicated state is authoritative one-writer latest-value replication.

The source API has an initialized value, `set(value, context)`, and subscriptions. A remote or disconnected replica has `value === undefined` until hydration.

Required semantics:

1. The source is always initialized.
2. Source and replica values are strict JSON for remotely exposable state.
3. Subscribing to initialized local or hydrated replica state immediately delivers the current value with a fresh delivery context.
4. Subscribing to cold state registers without immediate delivery.
5. Subscription establishment installs update capture before taking the snapshot.
6. Updates racing the snapshot are buffered and delivered after the snapshot with no gap.
7. The source API exposes a tracked mutable state and explicit publication. Each publication flushes one decoded operation batch; connection adapters encode it independently per client/state stream, and replicas apply batches only in sequence order.
8. A sequence gap clears readiness and triggers complete resubscription or reports a terminal binding error; stale state must not continue as current silently.
9. Disconnect, provider withdrawal, route change, and replacement clear replica readiness.
10. Reconnect or replacement installs a complete fresh snapshot in the existing state facade before later updates.
11. Listener exceptions are isolated and reported through host policy.
12. Values are immutable data. Chord does not defensively clone local reads, local writes, or local listener delivery. Delta application preserves prior values and may structurally share unchanged data, but callers must not depend on identity.

State identity is structural:

```text
provider binding + service ID + optional keyed address + member name
```

There is no separate state ID.

Explicit non-goals:

- durability or reconstruction after process restart;
- event history;
- CRDT merging or multiple writers;
- offline mutation replay;
- automatic unchanged-value suppression; and
- high-frequency stream transport.

Chord exposes an intent-preserving JSON delta primitive and uses its operation batches internally for remote replicated state. Initial hydration and reconnection carry a complete root replacement; producers mutate tracked state and flush compact operations on publication. Replicated-state sources do not select reducers or interact with path encoders. Every client/state pairing owns an independent encoder, and sequence handling rejects gaps before a later operation can be applied.

## 9. Symmetric RPC plumbing

### 9.1 No client/server mode

Chord must not expose `Client`, `Server`, `SessionConnection`, or similar topology classes. It exposes a symmetric peer over an application-supplied duplex channel. Either endpoint may register handlers, provide services, call methods, or subscribe to state.

Application adapters own:

- sockets, pipes, WebSockets, workers, or loopback delivery;
- framing and reconnect policy;
- authentication and authorization;
- routing and target selection;
- process ownership;
- attachment or selection state; and
- application protocol envelopes surrounding a Chord message.

Chord sees one connected peer and already-decoded strict-JSON messages.

### 9.2 RPC layer

The generic RPC peer should own:

- request ID allocation scoped to one peer connection;
- request/response correlation;
- handler registration;
- cancellation frames and one request-local `AbortController`;
- disconnect rejection and cleanup;
- stable serializable error envelopes;
- ordered notification delivery;
- malformed-message rejection; and
- optional context metadata hooks.

The channel contract should be small: send one strict-JSON message, receive messages in order, observe close, and close. `send()` should be awaitable so adapters can provide backpressure.

A peer disconnect:

- rejects outbound requests;
- aborts inbound request contexts;
- closes service subscriptions and keyed observation tasks; and
- does not cancel application-owned jobs or perform durable business mutations.

### 9.3 Service protocol over RPC

The service layer adds transport-neutral operations for:

- catalogue discovery;
- singleton and keyed subscription open/close;
- complete subscription snapshots;
- method invocation;
- invocation cancellation;
- replicated-state updates;
- singleton unavailable/replaced events; and
- keyed instance spawned/closed events.

The wire protocol contains no server ID, session ID, attachment ID, route, user identity, or host kind. A Pi router may wrap or forward Chord envelopes using its own control fields without parsing service business payloads.

Provider catalogue and subscription state must come from actual service provisions, not a handwritten application inventory.

### 9.4 Wire errors and validation

Chord needs stable generic error codes for:

- service not allowed or absent;
- mode mismatch;
- member absent or used with the wrong kind;
- keyed instance absent or stale;
- invalid strict-JSON value;
- cancellation;
- malformed RPC message;
- peer disconnected; and
- internal provider failure.

Unexpected provider exceptions become a sanitized internal error by default. Stack traces and arbitrary exception fields do not cross the wire. Applications may register or map additional stable error codes through an adapter, but Chord does not own application error taxonomies.

### 9.5 Protocol evolution

The first implementation must version Chord's RPC/service envelope independently of any application protocol. Version negotiation can be a peer handshake or an adapter-guaranteed constructor parameter, but incompatible peers must fail before service calls are admitted.

Member and DTO compatibility across plugin-generation skew is an application responsibility. Chord guarantees only its generic envelope semantics.

## 10. Bundling

### 10.1 Purpose

The bundler turns one or more application-declared ESM or TypeScript plugin entries into independently loadable Node CommonJS artifacts. It is not a package manager or plugin registry.

Each entry is built independently. Chord does not assume names such as `server`, `session`, `tui`, or `web`; entry names are opaque application data.

### 10.2 Initial input and output

The initial bundler should accept:

- plugin identity and optional version metadata;
- a mapping of opaque entry names to TypeScript or JavaScript source files;
- an output directory;
- an application-supplied external-module allowlist;
- source-map and minification options; and
- optional define/platform settings needed for the Node CommonJS build.

The package-level API additionally accepts a plugin package directory, derives identity and version from `package.json`, applies application-supplied conventional entry paths when those files exist, and lets `chord.facets` override or disable conventions. Package discovery does not install dependencies or run lifecycle scripts.

It should emit:

- one content-addressed CommonJS file per entry;
- source maps when enabled;
- a versioned strict-JSON manifest;
- content hashes or integrity values;
- declared external imports; and
- enough metadata for diagnostics and fresh generation loads.

Writes should use a temporary output directory followed by an atomic rename so a loader never sees a half-written generation.

### 10.3 Bundle rules

- `@earendil-works/chord` must be externalized so a plugin uses the host's one runtime and branding symbols.
- Other dependencies are bundled by default. The explicit bundler API uses an application external allowlist; the package-level API also externalizes peer dependencies because the host provides them.
- Built-in module use may be allowed for Node entries but is not a trust or sandbox policy.
- Dynamic imports must be lowered through the loader's restricted `require`, and unresolved externals must be reported deterministically.
- Bundle output must not depend on Pi's repository path aliases.
- Rebuilding unchanged inputs should produce stable content except for documented metadata.
- Diagnostics must identify the entry and original source location.

The concrete bundler engine is an implementation detail. Select it with a spike covering TypeScript and ESM inputs, CommonJS output, source maps, externals, content hashing, and programmatic diagnostics before adding a dependency.

### 10.4 Bundle loading

The bundle loader must:

1. parse and validate the manifest;
2. select one application-requested entry;
3. verify integrity before activation when integrity is present;
4. compile it directly with `node:vm` as a fresh generation outside Node's module caches;
5. validate that its exports are plugins with unique non-empty IDs;
6. return `LoadedPlugins`; and
7. provide idempotent loader disposal.

Plugin discovery, installation, version resolution, download, signature trust, and update policy remain application responsibilities.

## 11. Pi migration boundary

The following existing files describe behavior that should become Chord responsibility through a rewrite:

| Existing area | Chord responsibility |
| --- | --- |
| `packages/agent/src/plugins/services/types.ts` | service tokens, modes, remote contract checks, strict JSON, snapshots, updates, connection interfaces |
| `packages/agent/src/plugins/services/replicated-state.ts` | authoritative replicated state and delivery semantics |
| `packages/agent/src/plugins/services/provider.ts` | provider classification, calls, singleton replacement, keyed generations, snapshots |
| `packages/agent/src/plugins/services/namespace.ts` | stable remote facades, hydration, state updates, keyed observation |
| `packages/coding-agent/src/experimental/facets.ts` | plugin environment, dependency ledger, lifecycle graph, host, reload |
| `packages/coding-agent/src/experimental/facet-loader.ts` | static and combined loaders plus loaded-generation ownership |
| generic service sections of `packages/protocol/src/protocol.ts` | Chord-owned versioned service/RPC envelope |

The following must remain outside Chord:

| Existing area | Downstream responsibility |
| --- | --- |
| `packages/coding-agent/src/experimental/services/connection.ts` | Pi connection state, selected-session attachment, route rebinding, Pi client adapter |
| `packages/coding-agent/src/experimental/services/server.ts` | server-wide session directory and management implementations |
| `packages/coding-agent/src/experimental/services/worker.ts` | Session worker host construction and Pi protocol publication adapter |
| `packages/server`, `packages/client`, and process managers | framing, routing, authentication, attachment, process lifecycle, reconnect policy |
| slash-command, model, account, transcript, TUI, and agent-controller services | application contracts and plugin implementations |
| `source-resolver.ts` and Pi internal process entrypoints | Pi source execution and process policy |

`packages/agent/docs/plugins.md`, `packages/agent/docs/rpc.md`, the experimental service tests, and the remote plugin fixture are behavioral input. They are not normative Chord APIs. Once migration finishes, generic semantics should be documented in Chord and Pi documents should cover only their host-specific contracts and adapters.

Migration should happen only after Chord passes its standalone conformance suite:

1. implement Chord without changing Pi callers;
2. add thin Pi adapters and migrate generic service imports;
3. migrate the experimental plugin host and loaders;
4. adapt Pi's routed protocol to carry Chord envelopes;
5. run local, loopback, framed, keyed-generation, reload, and TUI integration tests; and
6. delete duplicate experimental generic implementations only after all consumers use Chord.

No compatibility shim is required unless separately requested.

## 12. Proposed source layout

This is a planning aid, not a requirement to create all files immediately.

```text
packages/chord/
  src/
    index.ts                 platform-neutral public API
    api.ts                   root-exported functions
    types.ts                 root-exported types, including strict JSON values
    context/
      index.ts               invocation context constants and functions
    errors.ts                lifecycle, service, and RPC errors
    services/
      types.ts               tokens, contracts, modes, snapshots
      state.ts               source and replica state primitives
      state-internals.ts     private replicated-state metadata
      provider.ts            singleton/keyed provider runtime
      facade.ts              stable local and remote facades
      host-bindings.ts       graph-facing service slots
    rpc/
      peer.ts                symmetric request/cancel plumbing
      protocol.ts            versioned generic envelopes and parsing
      services.ts            service protocol over a peer
      loopback.ts            deterministic in-memory duplex transport
    plugins/
      types.ts               plugin and environment types
      lifecycle.ts           activation and resource ownership
      graph.ts               validation and ordering
      host.ts                start, update, reload, dispose
      loader.ts              static and combined loaders
    node/
      bundle.ts              Node CommonJS bundler
      bundle-loader.ts       manifest validation and generation loading
  test/
    ...
  test-fixtures/
    bundled-plugin/
  README.md
  PLANNING.md
```

If Node-only APIs are exported, they should use a separate package export such as `@earendil-works/chord/node` or `@earendil-works/chord/bundler`; importing the main runtime must not load Node-only modules.

## 13. Work packages

### WP0 — Contract decisions and test harness

Deliver:

- settle public vocabulary and the invocation-context shape;
- settle the admitted-call unload policy;
- settle protocol version negotiation;
- choose whether remote context position is fixed and trailing;
- create deterministic in-memory duplex and controllable race test helpers;
- add package-boundary checks preventing Pi imports; and
- add compile-only fixtures for valid and invalid remote contracts.

Exit condition: every later work package can target explicit behavior without importing experimental implementations.

### WP1 — Foundations and replicated state

Deliver:

- strict JSON type/checking;
- neutral context, cancellation, and cancellation-aware waiting;
- mutable authoritative state;
- cold replica state;
- snapshot hydration, ordered updates, clear, and rehydrate;
- borrowed immutable value contract; and
- listener error reporting.

Tests include cold/hydrated subscriptions, immediate delivery, source update order, snapshot/update races, sequence gaps, cancellation, invalid JSON, and listener failure isolation.

### WP2 — Symmetric RPC peer

Deliver:

- versioned peer envelopes and validation;
- request/response correlation;
- inbound handler dispatch;
- cancellation and disconnect behavior;
- serializable sanitized errors;
- ordered notifications; and
- loopback transport.

Tests include requests initiated from both peers, crossed concurrent requests, duplicate/unknown IDs, pre-aborted requests, cancellation isolation, malformed messages, send failure, disconnect during calls, and handler exceptions.

### WP3 — Service provider and facades

Deliver:

- service tokens and locality policy;
- singleton and keyed provider registration;
- implementation member classification;
- local service slots and stable facades;
- remote method invocation over `RpcPeer`;
- catalogues generated from provisions;
- keyed generations and stale-call fencing; and
- service error mapping.

Tests include local and loopback paths, captured method stability, provider withdrawal/replacement, mode errors, unsupported members, strict-JSON argument/result checks, local-only isolation, keyed reuse, and concurrent callers.

### WP4 — Remote state and service subscriptions

Deliver:

- complete singleton and keyed subscription snapshots;
- atomic snapshot/update buffering;
- state update publication;
- singleton unavailable/replaced events;
- keyed directory hydration and ordered reconciliation;
- observer task cancellation; and
- clear/rehydrate on connection replacement.

Tests include late subscribers, updates racing hydration, multiple state members, provider replacement, keyed hydration before handlers, disconnect, reconnect, sequence gaps, stale frames, and observer errors.

### WP5 — Plugin host and graph

Deliver:

- plugin/environment APIs;
- setup-derived ledger;
- graph validation and topological ordering;
- local and connected service resolution;
- lifecycle ownership;
- startup failure cleanup;
- host disposal; and
- static loader integration.

Tests include consumer-before-provider setup, missing/duplicate/ambiguous providers, mode mismatch, cycles, asynchronous setup rejection, activation order, reverse cleanup, cleanup aggregation, connection hydration failure, and service access guards.

### WP6 — Generation loading, unload, and reload

Deliver:

- combined loaders;
- complete structural generation replacement;
- shape-preserving targeted reload;
- stable surviving service slots;
- keyed instance retirement;
- generation fencing for late calls and updates;
- admitted-call drain/cancel policy; and
- precise failure reporting and loader disposal order.

Tests include load failure cleanup, setup failure with old generation retained, unload with retained hard consumer rejection, provider gaps, captured local and remote methods, replacement snapshots, activation failure after cutover, disposal failure aggregation, concurrent update/dispose, and old-generation late publication.

### WP7 — Node CommonJS bundler and bundle loader

Deliver:

- bundler-engine spike and decision;
- programmatic bundler API;
- versioned manifest;
- independent content-addressed entries;
- source maps and diagnostics;
- Chord externalization;
- atomic output replacement;
- manifest/integrity validation; and
- fresh VM-compiled generation loading outside Node's module caches.

Tests bundle an application-neutral fixture with two opaque entries and a third-party dependency, load each independently, activate it, reload changed source, prove unchanged source hashes are stable, reject corrupt manifests/integrity, and prove output resolves no Pi packages.

### WP8 — Pi adoption

This work is downstream of Chord rather than an implementation dependency.

Deliver:

- Pi adapters for context metadata and routed RPC transport;
- migration of experimental service and plugin host consumers;
- preservation of selected-session and TUI behavior outside Chord;
- framed integration and reload coverage; and
- removal of superseded generic experimental code.

Exit condition: Pi depends on Chord, while Chord remains independently packable and contains no Pi imports.

## 14. Required conformance matrix

The standalone suite must cover at least:

### Plugin graph and lifecycle

- declaration only during setup;
- setup service access rejection;
- deterministic graph ordering;
- missing, duplicate, ambiguous, and cyclic dependencies;
- activation and reverse disposal;
- startup and disposal failure aggregation;
- local and connected providers in one graph;
- complete structural load/unload; and
- shape-preserving reload.

### Services

- singleton and keyed modes;
- unrestricted local contracts;
- remote member classification;
- strict JSON and `void` results;
- stable local and remote facades;
- provider withdrawal and replacement;
- keyed generation fencing;
- per-call cancellation; and
- connection and host access guards.

### Replication

- initialized source and cold replica;
- immediate hydrated subscription delivery;
- snapshot/update race freedom;
- ordered updates and gap handling;
- disconnect clearing;
- replacement and reconnect rehydration;
- keyed state before observer startup; and
- listener/handler cleanup.

### RPC

- symmetric calls in both directions;
- request correlation and cancellation isolation;
- malformed and oversized-message policy;
- sanitized errors;
- disconnect cleanup;
- subscription cleanup;
- protocol-version mismatch; and
- deterministic in-memory and framed-adapter tests.

### Loading and bundling

- loader order and reverse disposal;
- fresh generation evaluation and garbage-collection eligibility;
- manifest validation and integrity;
- independent entries;
- dependency bundling and explicit externals;
- source maps and diagnostics;
- atomic output; and
- packed-package execution outside the monorepo.

Race tests should control exact points rather than use timing: subscription capture versus state update, request admission versus cancellation, provider withdrawal versus invocation, instance close versus call, reload cutover versus update publication, and host dispose versus activation.

## 15. Non-goals for the initial implementation

- Pi host APIs or built-in Pi services;
- plugin discovery, installation, download, registry, or package resolution;
- trust policy, code signing, sandboxing, or capability security;
- network listeners, socket framing, reconnect loops, routing, or authentication;
- server/client roles or fixed process topologies;
- durable state, database integration, migrations, or transactional application writes;
- CRDTs, offline writes, or mutation replay;
- arbitrary object remoting, callbacks, remote references, or garbage collection of references;
- serialized UI trees, remote tools, or remote hooks;
- generic contribution registries; applications can expose these as process-local services;
- automatic retries of mutating calls after uncertain disconnects; and
- backward compatibility with experimental Pi APIs or wire formats.

## 16. Decisions required before implementation

The following decisions should be recorded in this document or small ADRs before WP1/WP2/WP7 begins:

1. Final public names: `Plugin` versus `Facet`, `Host`, `Peer`, and `Connection`.
2. The exact neutral context API and remote method context position.
3. Whether context metadata propagation is in the first RPC envelope or added with a compatible optional field.
4. Wait-versus-cancel policy for admitted provider calls during unload.
5. Peer protocol negotiation and maximum message-size ownership.
6. State sequence-gap recovery: automatic resubscribe versus terminal binding failure.
7. Bundler engine and its runtime/development dependency placement.
8. Manifest schema, integrity algorithm, and external-module resolution contract.
9. Whether browser-compatible core behavior is an immediate tested requirement or only an architectural constraint.

None of these decisions should introduce Pi concepts into Chord.

## 17. Definition of done

Chord's initial scope is complete when:

- a standalone application unrelated to Pi can define local and remote singleton/keyed services;
- two symmetric peers can call each other, cancel calls, subscribe, disconnect, and rehydrate;
- replicated state satisfies the snapshot/update and replacement semantics above;
- plugins activate from a validated graph and own all registered resources;
- a running host can load, unload, structurally replace, and shape-preservingly reload plugin generations;
- stable service facades survive provider replacement as specified;
- the Node bundler emits and reloads independent content-addressed plugin entries;
- all race and lifecycle conformance tests pass;
- the packed package works outside the Pi monorepo; and
- an automated boundary check proves that Chord has no imports or dependencies on the rest of Pi.
