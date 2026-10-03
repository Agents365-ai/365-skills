# Pi: Programmatic Usage (SDK, CLI, RPC, JSON)
Source: https://pi.dev/docs/latest/sdk, /cli-integration, /json, /rpc, /rpc-commands, /rpc-extension-ui

---

> **Auto-built from individual doc pages.**
> Sources: https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/sdk.md, https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/cli-integration.md, https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/json.md, https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/rpc.md, https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/rpc-commands.md, https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/rpc-extension-ui.md

## SDK

`@earendil-works/pi-coding-agent` embeds Pi in a Node.js or Bun process. It provides direct TypeScript access to the agent, sessions, tools, models, and resources used by the command-line application.

Use the SDK for in-process TypeScript integration. For a language-independent or isolated subprocess, see [CLI Integration](cli-integration.md).

```typescript
import { createAgentSession } from "@earendil-works/pi-coding-agent";

const { session } = await createAgentSession();

try {
  await session.prompt("What files are in the current directory?");
  console.log(session.getLastAssistantText());
} finally {
  session.dispose();
}
```

This uses the working directory, discovered resources, stored settings, and configured credentials. `prompt()` resolves when the run finishes.

The [complete minimal example](../examples/sdk/01-minimal.ts) also streams text events. All [SDK examples](../examples/sdk/) are typechecked with the repository.

<a id="session-management"></a>

## Session lifecycle

`createAgentSession()` creates an `AgentSession`. The session owns one conversation, its model and tools, queued messages, compaction state, and extension runtime.

Read current state through `session.messages`, `session.model`, `session.thinkingLevel`, `session.systemPrompt`, and `session.getActiveToolNames()`.

`session.systemPrompt` is read-only and returns the current effective system prompt, including changes that have not yet been sent to the model. Tool changes are declared to the model before the next request.

<a id="sessionmanager-api"></a>

### Session storage

Sessions are persistent by default. `SessionManager` owns the persisted or in-memory entry tree and tracks its active leaf. Branching changes that leaf without deleting abandoned branches. When Pi reconstructs model context, the manager selects the active branch and applies compaction.

`SessionManager` is authoritative for finalized model context. Restore external history by constructing the session with a manager containing those entries. Assigning `session.agent.state.messages` does not replace persisted context.

Use an in-memory manager when the host does not want session files:

```typescript
import { createAgentSession, SessionManager } from "@earendil-works/pi-coding-agent";

const { session } = await createAgentSession({
  sessionManager: SessionManager.inMemory(),
});
```

See the checked [sessions example](../examples/sdk/11-sessions.ts) for creating, opening, continuing, listing, and forking sessions. [Session File Format](session-format.md) defines the persisted JSONL contract, and [Message Types](message-types.md) defines transcript values. For exact methods and signatures, use the exported TypeScript declarations or [`session-manager.ts`](../src/core/session-manager.ts).

`cwd` selects the workspace used for project resource discovery, context files, session grouping, and built-in tool paths. Pass it explicitly when the target differs from `process.cwd()`.

`session.dispose()` aborts active work, invalidates extension contexts, disconnects from the agent, and removes event listeners. Call it when the session is no longer needed.

`AgentSessionRuntime` adds `newSession()`, `switchSession()`, `fork()`, and `importFromJsonl()`. Each operation replaces the active `AgentSession` and recreates services for the target working directory.

After a runtime replacement, subscriptions belong to the old `AgentSession` and must be rebound. See the [session runtime example](../examples/sdk/13-session-runtime.ts).

## Prompting

`prompt()` handles extension commands and expands file-based prompt templates before ordinary user messages enter the agent. For an accepted agent run, it resolves after the run finishes, including automatic retries.

A prompt sent while the session is already streaming must specify whether it should steer the current run or follow it. Calling `prompt()` without that choice rejects rather than guessing.

A steering message enters after the current assistant turn and its tool calls. A follow-up enters after the current run finishes its pending work. `steer()` and `followUp()` expose those behaviors directly and return `"queued"` if the input was queued (including after an extension transformed it), or `"handled"` if an extension consumed it.

`abort()` stops the active operation and waits for the session to become idle. `waitForIdle()` waits without aborting it.

## Subscribing to events

Subscribe before prompting when the host needs streamed output:

```typescript
const unsubscribe = session.subscribe((event) => {
  if (event.type === "message_update" && event.assistantMessageEvent.type === "text_delta") {
    process.stdout.write(event.assistantMessageEvent.delta);
  }
});

try {
  await session.prompt("Explain this repository");
} finally {
  unsubscribe();
}
```

Session events report message updates, tool execution, queues, compaction, retries, and run lifecycle changes.

`message_end` contains the authoritative completed message. `agent_end` marks the end of one low-level agent run, but automatic recovery or queued work can still follow.

Use `agent_settled` when the host needs to know that Pi will not continue automatically.

## Configuring a session

Without overrides, the factory creates a `ModelRuntime`, file-backed `SettingsManager`, persistent `SessionManager`, `DefaultResourceLoader`, and the configured default tools.

Each boundary can be supplied explicitly:

- `modelRuntime`, `model`, `thinkingLevel`, and `scopedModels` control model access and selection.
- `settingsManager` supplies merged settings or an in-memory configuration.
- `sessionManager` supplies persistent or in-memory conversation history.
- `resourceLoader` supplies extensions, skills, prompt templates, themes, and context files.
- `tools`, `noTools`, `excludeTools`, and `customTools` control the active tool set.

Use `DefaultResourceLoader` when you want standard discovery with selected overrides. Supply a custom `ResourceLoader` when the host owns resource storage and discovery completely.

<a id="inlineextension"></a>

Inline extension factories can be supplied through `DefaultResourceLoader`. Give one an `InlineExtension` name only when it needs a stable name in diagnostics and startup output. A named inline extension with `replaceable: true` is left out when another extension registers a tool, command, or flag with a name it registers during loading, instead of both loading with a conflict. The CLI's built-in codemode, tool search, and MCP extensions are replaceable. A named entry with `builtin: true` is not an inline extension: it supplies the code of the `builtin:<name>` extension, which loads like a configured extension file. It loads by default, is listed in `pi config`, and is disabled by `-builtin:<name>` in the `extensions` setting or by `noExtensions`; `additionalExtensionPaths: ["builtin:<name>"]` loads it explicitly. It loads after project trust is resolved, so it cannot handle `project_trust`. The CLI's built-in extensions use it.

<a id="codemode-mcp"></a>

The CLI loads `codemode`, `tool_search`, and MCP as built-in extensions. SDK sessions do not; add `createCodemodeExtension()`, `createToolSearchExtension()`, and `createMcpExtension()` to the `extensionFactories` of `DefaultResourceLoader`. `codemode` and `tool_search` are registered inactive: enable them through the `defaultTools` setting (`["+codemode", "+tool_search"]` keeps the other default tools), or let the MCP extension activate them: `codemode` for servers with `codemode` exposure, `tool_search` for servers with `deferred` exposure. The MCP extension connects its servers on `session_start`, so call `session.bindExtensions()`. See [Codemode and MCP](../examples/sdk/14-codemode-mcp.ts).

See the focused examples for [models](../examples/sdk/02-custom-model.ts), [tools](../examples/sdk/05-tools.ts), [extensions](../examples/sdk/06-extensions.ts), and [full control](../examples/sdk/12-full-control.ts).

## Examples

| Example | Purpose |
|---|---|
| [Minimal](../examples/sdk/01-minimal.ts) | Create, prompt, observe, and dispose a session |
| [Custom model](../examples/sdk/02-custom-model.ts) | Select a model and thinking level |
| [System prompt](../examples/sdk/03-custom-prompt.ts) | Replace or append to the system prompt |
| [Skills](../examples/sdk/04-skills.ts) | Discover, filter, and add skills |
| [Tools](../examples/sdk/05-tools.ts) | Select built-in tools and their working directory |
| [Extensions](../examples/sdk/06-extensions.ts) | Load file-based and inline extensions |
| [Context files](../examples/sdk/07-context-files.ts) | Add or replace project instructions |
| [Prompt templates](../examples/sdk/08-prompt-templates.ts) | Add file-style prompt templates |
| [Credentials](../examples/sdk/09-api-keys-and-oauth.ts) | Configure credential and model storage |
| [Settings](../examples/sdk/10-settings.ts) | Supply file-backed or in-memory settings |
| [Sessions](../examples/sdk/11-sessions.ts) | Control session persistence and restoration |
| [Full control](../examples/sdk/12-full-control.ts) | Replace default discovery and state services |
| [Session runtime](../examples/sdk/13-session-runtime.ts) | Replace the active session safely |
| [Codemode and MCP](../examples/sdk/14-codemode-mcp.ts) | Add the `codemode`, `tool_search`, and MCP extensions |

<a id="exports"></a>

## Resources

- [Choose a Model](models.md) covers model selection and compatible endpoints; [Providers](providers.md) covers credentials and provider-specific setup.
- [Configuration](configuration.md) explains normal discovery and settings; [Settings](settings.md) lists every setting.
- [Sessions and Context](sessions.md) explains session behavior; [Session Format](session-format.md) defines persisted entries; [Message Types](message-types.md) defines shared transcript values.
- [Extensions](extensions.md), [Skills](skills.md), and [Prompt Templates](prompt-templates.md) document resources supplied through a `ResourceLoader`.
- [CLI Integration](cli-integration.md) covers print, JSON, and RPC alternatives to an in-process SDK integration.

---

## CLI Integration

By default, running `pi` opens the interactive terminal interface. When input or output is piped or redirected, Pi uses print mode instead. You can also select print, JSON, or RPC mode explicitly for scripts and applications.

All four modes use the same agent, sessions, resources, and tools. The mode determines how input enters Pi, how output is exposed, and whether the process remains available for more commands.

The SDK is not a CLI mode. It embeds the agent directly in a Node.js or Bun process. See the [SDK](sdk.md) when direct TypeScript access is preferable to a process boundary.

## Choose a mode

| Mode | Interface | Lifetime | Use it when |
|---|---|---|---|
| Interactive | Terminal UI | Until the user exits | A person is working with Pi directly |
| Print | Final text on stdout | One invocation | A script needs the final assistant response |
| JSON | JSONL events on stdout | One invocation | A process needs structured progress from a run |
| RPC | JSONL commands, responses, and events | Long-lived | A process needs bidirectional control |

CLI options still select the working directory, model, tools, resources, and session persistence independently of the mode. See [Command Line](cli.md) for the complete startup options.

## Print to stdout

Print mode runs the supplied prompts, writes the final assistant text to stdout, and exits:

```bash
pi --print "Summarize the changes in this repository"
```

Use print mode when only the final text is needed, including command substitution, pipelines, and one-shot jobs. Intermediate events are not exposed.

Print mode writes errors to stderr. A final assistant response with an `error` or `aborted` stop reason produces a nonzero exit status.

When no mode is selected explicitly, non-TTY stdin or stdout also selects print mode. This allows piped input and output without adding `--print`.

## Stream JSON events

JSON mode writes a session header followed by agent and session events as newline-delimited JSON:

```bash
pi --mode json "Review this repository" > events.jsonl
```

This is structured event output, not a single JSON result or a constraint on the format of the model’s response.

All prompts are supplied when the process starts. The process streams events for that run and then exits; it does not accept later commands.

A failed or aborted assistant response appears in the event stream but does not by itself produce a nonzero exit status. Inspect the events when success or failure matters. Pi still exits nonzero if the invocation throws an error.

Streaming `message_update` records contain deltas rather than a growing message snapshot. Assemble live output from the delta events, then replace it with the authoritative message from `message_end`.

`agent_end` can be followed by automatic recovery or queued work. `agent_settled` marks the end of automatic work for the current run.

Stdout is reserved for JSONL. Diagnostics and application logging are written to stderr. See [JSON Event Stream](json.md) for framing, event shapes, and reconstruction rules.

## Control Pi with RPC

RPC mode keeps Pi running while another process sends commands and receives responses and events:

```bash
pi --mode rpc --no-session
```

Commands are JSON objects written to stdin. Responses and events are JSON objects written to stdout. Every record occupies one line.

Add an `id` to commands that need correlation. The matching response repeats that ID. Events generally have no command ID because they describe session activity rather than one request.

A successful `prompt` response means the prompt was accepted, queued, or handled. It does not mean the run completed. Continue consuming events through `agent_settled` when completion matters.

RPC commands can change models, inspect state, manage sessions, run shell commands, and answer extension UI requests.

Extension dialogs form a request-response subprotocol. Other extension UI updates are notifications that a client may display or ignore. TUI-only extension capabilities are unavailable or degraded outside interactive mode.

For Node.js or TypeScript integrations, prefer `RpcClient` from `@earendil-works/pi-coding-agent`. It starts a Pi RPC child process, correlates requests, exposes typed command methods, and delivers session events to listeners.

The [RPC client example](../examples/rpc-client.ts) sends one prompt, streams text and tool activity, waits for `agent_settled`, and shuts down the child process. It is included in the repository’s TypeScript checks.

`RpcClient.promptAndWait()` installs its event listener before sending the prompt, avoiding a race with fast completions. For separate operations, subscribe before calling `prompt()` and call `waitForIdle()` only while a run is active.

The client requires a path to a runnable Pi CLI. The repository example points at `dist/cli.js`, so the package must be built before that example runs from a checkout.

If you are building a client without `RpcClient`, start with [RPC Protocol](rpc.md), then use [RPC Commands](rpc-commands.md) and [JSON Event Stream](json.md) as the wire references.

## Fork and rebrand Pi

A source fork can change the CLI name and configuration directory through `package.json`:

```json
{
  "piConfig": {
    "name": "my-agent",
    "configDir": ".my-agent"
  }
}
```

Change the top-level `bin` field to set the executable name. These settings affect the CLI banner, configuration paths, and derived environment variable names.

## Examples and references

- [RPC client](../examples/rpc-client.ts): typed Node.js integration
- [RPC extension UI](../examples/rpc-extension-ui.ts): custom terminal client with extension dialogs
- [Command Line](cli.md): startup options and mode selection
- [JSON Event Stream](json.md): JSON event reference
- [RPC Protocol](rpc.md): RPC lifecycle, framing, errors, and shutdown
- [RPC Commands](rpc-commands.md): command and response reference
- [RPC Extension UI](rpc-extension-ui.md): extension interaction subprotocol
- [SDK examples](../examples/sdk/): in-process TypeScript integrations

---

## JSON Event Stream

JSON mode emits structured progress for one invocation:

```bash
pi --mode json "Review this repository"
```

Pi writes one session header followed by session events, then exits after the supplied prompts finish. RPC mode emits the same session-event shapes but has no session header because it is a bidirectional, long-lived protocol. See [RPC Mode](rpc.md).

This page is the canonical reference for events shared by JSON and RPC mode. Message values use the [shared message types](message-types.md).

## Framing and process I/O

The stream uses strict JSONL framing. Each record is one JSON object terminated by LF (`\n`). Split records only on LF and strip an optional preceding carriage return. Unicode line and paragraph separators are valid inside JSON strings and are not record boundaries.

Node.js `readline` is not suitable for this stream because it also recognizes those Unicode separators. Use a byte or UTF-8 stream decoder and split on LF.

Read stdout continuously. A reader that stops consuming records can stall Pi when the pipe buffer fills. Stdout is reserved for JSONL; diagnostics and application logging go to stderr.

## Session header

The first JSON-mode record is the current [session header](session-format.md#sessionheader):

```json
{"type":"session","version":3,"id":"uuid","timestamp":"2024-12-03T14:00:00.000Z","cwd":"/path"}
```

RPC mode does not emit this record. Use [`get_state`](rpc-commands.md#get_state) for its current session ID and file.

## Event sequence

A basic run produces records like these:

```json
{"type":"agent_start"}
{"type":"turn_start"}
{"type":"message_start","message":{"role":"user","content":"Review this repository","timestamp":1733234401000}}
{"type":"message_end","message":{"role":"user","content":"Review this repository","timestamp":1733234401000}}
{"type":"message_start","message":{"role":"assistant","content":[],"stopReason":"pending","...":"..."}}
{"type":"message_update","usage":{"...":"..."},"assistantMessageEvent":{"type":"text_delta","contentIndex":0,"delta":"Hello"}}
{"type":"message_end","message":{"role":"assistant","...":"..."}}
{"type":"turn_end","message":{"role":"assistant","...":"..."},"toolResults":[]}
{"type":"agent_end","messages":[{"...":"..."}],"willRetry":false}
{"type":"agent_settled"}
```

`agent_end` closes one low-level agent run. Automatic retry, overflow recovery, compaction retry, steering, or follow-up work can still continue. `agent_settled` means Pi has no remaining automatic work for that session-level run.

## Agent and turn events

| Event | Fields | Meaning |
|---|---|---|
| `agent_start` | None | A low-level agent run started. |
| `agent_end` | `messages`, `willRetry` | That low-level run ended. `messages` contains messages generated by the run. |
| `agent_settled` | None | Pi will not continue automatically through retries, compaction recovery, or queued messages. |
| `turn_start` | None | One assistant turn started. |
| `turn_end` | `message`, `toolResults` | One assistant response and its resulting tool calls finished. |

A turn is one assistant response plus any tool calls and tool results produced by that response.

## Message events

| Event | Fields | Meaning |
|---|---|---|
| `message_start` | `message` | A message started. |
| `message_update` | `usage`, `assistantMessageEvent` | An assistant message emitted a content-block update. |
| `message_end` | `message` | A message completed. This is the authoritative final message. |

### Reconstruct streaming messages

Wire `message_update` records are delta-only. They omit the SDK event's cumulative `message` field and every `assistantMessageEvent.partial` snapshot so stream size remains linear.

The nested event is one of:

| Type | Fields in addition to `type` | Meaning |
|---|---|---|
| `start` | None | The provider stream started; its cumulative `partial` field is removed on the wire. |
| `text_start` | `contentIndex` | A text block started. |
| `text_delta` | `contentIndex`, `delta` | Append text to the block. |
| `text_end` | `contentIndex`, `content` | The text block ended with authoritative content. |
| `thinking_start` | `contentIndex` | A thinking block started. |
| `thinking_delta` | `contentIndex`, `delta` | Append thinking text to the block. |
| `thinking_end` | `contentIndex`, `content` | The thinking block ended with authoritative content. |
| `toolcall_start` | `contentIndex`, `id`, `toolName` | A tool-call block started. |
| `toolcall_delta` | `contentIndex`, `delta` | Append serialized argument data. |
| `toolcall_end` | `contentIndex`, `toolCall` | The tool call ended with the complete `ToolCall`. |
| `done` | `reason`, `message` | The provider stream completed successfully. |
| `error` | `reason`, `error` | The provider stream ended with an error or abort message. |

The normal agent loop translates provider-level `start`, `done`, and `error` into `message_start` and `message_end` session events rather than emitting them as `message_update`. They remain admitted by the exported `JsonAgentSessionEvent` transformation for callers that construct a matching session event.

Use `contentIndex` to identify the content block. Buffer `delta` fields for a live display, but replace reconstructed data with the completed content in `text_end`, `thinking_end`, or `toolcall_end`. Replace the whole partial message with `message_end.message` when it arrives.

The top-level `usage` is the latest cumulative provider-reported usage for the assistant response. It can remain zero until completion when a provider does not report usage while streaming.

```json
{"type":"message_update","usage":{"input":100,"output":1,"cacheRead":0,"cacheWrite":0,"totalTokens":101,"cost":{"input":0,"output":0,"cacheRead":0,"cacheWrite":0,"total":0}},"assistantMessageEvent":{"type":"text_delta","contentIndex":0,"delta":"Hello "}}
```

## Tool execution events

| Event | Fields | Meaning |
|---|---|---|
| `tool_execution_start` | `toolCallId`, `toolName`, `args` | Tool execution started. |
| `tool_execution_update` | `toolCallId`, `toolName`, `args`, `partialResult` | The tool reported a partial result. |
| `tool_execution_end` | `toolCallId`, `toolName`, `result`, `isError` | Tool execution finished. |

Use `toolCallId` to correlate the lifecycle. `partialResult` is the latest partial result supplied by the tool. Whether it replaces or extends an earlier update depends on that tool's result contract.

```json
{"type":"tool_execution_start","toolCallId":"call_abc123","toolName":"bash","args":{"command":"ls -la"}}
{"type":"tool_execution_update","toolCallId":"call_abc123","toolName":"bash","args":{"command":"ls -la"},"partialResult":{"content":[{"type":"text","text":"partial output"}],"details":{}}}
{"type":"tool_execution_end","toolCallId":"call_abc123","toolName":"bash","result":{"content":[{"type":"text","text":"complete output"}],"details":{}},"isError":false}
```

## Queue and state events

| Event | Fields | Meaning |
|---|---|---|
| `queue_update` | `steering`, `followUp` | The pending steering or follow-up queue changed. Both fields contain the complete current queue. |
| `entry_appended` | `entry` | An extension appended a custom session entry through `pi.appendEntry()`. |
| `session_info_changed` | `name` | The session display name changed. An absent `name` means it was cleared. |
| `thinking_level_changed` | `level` | The active thinking level changed. |

The `entry` value uses a persisted [session entry type](session-format.md#entry-types).

## Compaction events

`compaction_start` reports why compaction began:

```json
{"type":"compaction_start","reason":"threshold"}
```

`reason` is `"manual"`, `"threshold"`, or `"overflow"`.

`compaction_end` contains the result when compaction succeeds:

```json
{
  "type": "compaction_end",
  "reason": "threshold",
  "result": {
    "summary": "Summary of conversation...",
    "firstKeptEntryId": "abc123",
    "tokensBefore": 150000,
    "estimatedTokensAfter": 32000,
    "usage": {"...": "..."},
    "details": {}
  },
  "aborted": false,
  "willRetry": false
}
```

If compaction was aborted, `result` is absent and `aborted` is true. If it failed, `result` is absent, `aborted` is false, and `errorMessage` describes the failure. Successful overflow recovery sets `willRetry` to true before Pi retries the prompt.

See [Compaction and Branch Summaries](compaction.md) for result semantics.

## Retry events

Assistant-turn retry emits:

```json
{"type":"auto_retry_start","attempt":1,"maxAttempts":3,"delayMs":2000,"errorMessage":"529 overloaded"}
{"type":"auto_retry_end","success":true,"attempt":2}
```

On final failure, `auto_retry_end` has `success: false` and a `finalError` string.

Compaction and branch-summary retry emit:

```json
{"type":"summarization_retry_scheduled","attempt":1,"maxAttempts":3,"delayMs":2000,"errorMessage":"terminated"}
{"type":"summarization_retry_attempt_start","source":"compaction","reason":"threshold"}
{"type":"summarization_retry_finished"}
```

For a branch summary, `source` is `"branchSummary"` and `reason` is absent. The `reason` on a compaction retry is `"manual"`, `"threshold"`, or `"overflow"`.

## RPC-only events

A direct RPC [`bash`](rpc-commands.md#bash) command emits one `bash_execution_update` for each output chunk. Its optional `id` matches the command ID. The final command response can contain truncated output, but these events stream all output:

```json
{"type":"bash_execution_update","id":"req-1","delta":"total 48\n"}
```

RPC also adds `extension_error` when an extension handler throws:

```json
{"type":"extension_error","extensionPath":"/path/to/extension.ts","event":"tool_call","error":"Error message"}
```

Extension UI records are a separate RPC subprotocol, not `AgentSessionEvent` values. See [RPC Extension UI](rpc-extension-ui.md).

## TypeScript types

The SDK's `AgentSessionEvent` contains cumulative streaming snapshots for in-process consumers. JSON and RPC transform only `message_update`:

```typescript
type WithoutPartial<T> = T extends { partial: unknown } ? Omit<T, "partial"> : T;

type JsonAssistantMessageEvent<T> = T extends { type: "toolcall_start"; partial: unknown }
  ? WithoutPartial<T> & { id: string; toolName: string }
  : WithoutPartial<T>;

type JsonAgentSessionEvent =
  | Exclude<AgentSessionEvent, { type: "message_update" }>
  | {
      type: "message_update";
      usage: Usage;
      assistantMessageEvent: JsonAssistantMessageEvent<AssistantMessageEvent>;
    };
```

Use the exported `JsonAgentSessionEvent` type from `@earendil-works/pi-coding-agent`. Its implementation is in [`json-event.ts`](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/src/modes/json-event.ts).

## Example

Print completed messages from a one-shot run:

```bash
pi --mode json "List files" 2>/dev/null | jq -c 'select(.type == "message_end")'
```

---

## RPC Protocol

RPC mode runs Pi as a long-lived subprocess controlled through JSON records on stdin and stdout. Use it for language-independent integrations, process isolation, IDEs, and custom user interfaces.

For an in-process Node.js or Bun integration, prefer the [SDK](sdk.md). For a subprocess-based TypeScript integration, prefer the exported `RpcClient`, which starts Pi, correlates responses, exposes typed command methods, and delivers events to listeners.

| Interface | Process boundary | Control model | Best fit |
|---|---|---|---|
| [SDK](sdk.md) | In process | Direct TypeScript methods and events | Node.js or Bun hosts that want complete API access |
| RPC | Child process | JSONL commands, responses, and events | Other languages, isolated processes, IDEs, or custom clients |

## Start RPC mode

```bash
pi --mode rpc --no-session
```

Normal CLI options still select the working folder, model, tools, resources, and session behavior. Common choices include `--provider`, `--model`, `--name`, `--no-session`, and `--session-dir`. See [Command Line](cli.md) for the complete, version-specific interface; `pi --help` is authoritative for the installed version.

RPC mode rejects `@file` prompt arguments. Send prompts through the [`prompt`](rpc-commands.md#prompt) command instead.

## Protocol records

The protocol has four record families:

| Direction | Record | Purpose |
|---|---|---|
| stdin | Command | Ask Pi to prompt, inspect state, change configuration, or manage the session |
| stdout | `response` | Report whether one command succeeded and return any command data |
| stdout | Session event | Stream run, message, tool, queue, compaction, and retry activity |
| Both | Extension UI record | Forward supported extension interactions between Pi and the client |

See [RPC Commands](rpc-commands.md), [JSON Event Stream](json.md), and [RPC Extension UI](rpc-extension-ui.md) for the canonical record definitions.

### Correlate commands and responses

Every command accepts an optional string `id`. A matching response repeats it:

```json
{"id":"req-1","type":"get_state"}
{"id":"req-1","type":"response","command":"get_state","success":true,"data":{"...":"..."}}
```

Use unique IDs whenever more than one command can be outstanding. Command handling is asynchronous, so clients should correlate by ID rather than response order.

Session events generally have no command ID because they describe session activity. `bash_execution_update` is the exception: when the originating [`bash`](rpc-commands.md#bash) command has an ID, its output events repeat that ID.

An `extension_ui_response` uses the ID supplied by its `extension_ui_request`. It does not produce a normal command response.

## Framing

RPC uses strict JSONL framing. Write one complete JSON object per record and terminate it with LF (`\n`). Read stdout as a byte or UTF-8 stream and split records only on LF. Strip an optional preceding carriage return to accept CRLF input.

Do not use a generic line reader that treats Unicode line or paragraph separators as record boundaries. In particular, Node.js `readline` also splits on `U+2028` and `U+2029`, which are valid inside JSON strings.

Read stdout continuously. Pi honors stdout backpressure, but a client that stops reading can stall the process. Honor stdin backpressure when writing commands. Stdout is reserved for protocol records; diagnostics and application logging go to stderr.

## Run lifecycle

A successful `prompt` response means the prompt was accepted, queued, or handled. It does not mean model work completed:

```json
{"id":"req-2","type":"prompt","message":"Review this repository"}
{"id":"req-2","type":"response","command":"prompt","success":true,"data":{"disposition":"started"}}
```

`data.disposition` reports what happened to the prompt. If it is `"handled"`, no run started for this prompt, so don't wait for `agent_settled`. See [RPC Commands](rpc-commands.md#prompt) for all values.

Continue consuming [events](json.md) after that response. `agent_end` marks the end of one low-level agent run, but retries, overflow recovery, compaction, steering, or follow-up work can still follow. Wait for `agent_settled` when the client needs to know Pi will not continue automatically.

Subscribe before sending a prompt to avoid missing a fast completion. `RpcClient.promptAndWait()` does this internally. If using separate `RpcClient` calls, install the event listener before `prompt()` and call `waitForIdle()` only while a run is active.

## Errors

A failed command returns one response with `success: false`:

```json
{"id":"req-3","type":"response","command":"set_model","success":false,"error":"Model not found: invalid/model"}
```

Malformed JSON produces a parse response without a request ID:

```json
{"type":"response","command":"parse","success":false,"error":"Failed to parse command: Unexpected token..."}
```

A success response only covers command handling. Provider failures and aborts after a prompt is accepted appear in the message and event stream.

Clients must also handle child-process startup failures, unexpected exits, stderr diagnostics, cancellation, and their own deadlines. Do not parse stderr as protocol data.

## Shutdown

Close the child's stdin to request an orderly shutdown. Pi disposes the active runtime before exiting. Clients should still handle process signals and unexpected exits.

An extension can also request shutdown through its extension context. Pi completes shutdown after the current command or after the active run emits `agent_settled`.

## Minimal client

This Python example uses a binary pipe reader, which splits on LF without treating Unicode separators as protocol boundaries:

```python
import json
import subprocess

process = subprocess.Popen(
    ["pi", "--mode", "rpc", "--no-session"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
)

assert process.stdin is not None
assert process.stdout is not None

command = {"id": "prompt-1", "type": "prompt", "message": "Hello"}
process.stdin.write(json.dumps(command).encode("utf-8") + b"\n")
process.stdin.flush()

while line := process.stdout.readline():
    record = json.loads(line)
    if record.get("type") == "message_update":
        update = record["assistantMessageEvent"]
        if update["type"] == "text_delta":
            print(update["delta"], end="", flush=True)
    elif record.get("type") == "agent_settled":
        print()
        break

process.stdin.close()
process.wait()
```

For maintained TypeScript clients, use the checked [RPC client example](../examples/rpc-client.ts). It requires a built Pi CLI because the repository example points to `dist/cli.js`.

## Reference

- [RPC Commands](rpc-commands.md): every stdin command and response
- [JSON Event Stream](json.md): shared stdout session events and streaming reconstruction
- [RPC Extension UI](rpc-extension-ui.md): dialogs, notifications, responses, and limitations
- [Message Types](message-types.md): messages and content blocks used by responses and events
- [Session File Format](session-format.md): entries returned by session commands
- [`rpc-types.ts`](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/src/modes/rpc/rpc-types.ts): exported TypeScript protocol definitions
- [`RpcClient`](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/src/modes/rpc/rpc-client.ts): subprocess client implementation

## Moved reference anchors

The detailed references formerly on this page now have dedicated pages. These anchors preserve existing links.

<a id="prompt"></a>
<a id="steer"></a>
<a id="follow_up"></a>
<a id="abort"></a>
<a id="clear_queue"></a>
<a id="new_session"></a>
<a id="get_state"></a>
<a id="get_messages"></a>
<a id="set_model"></a>
<a id="cycle_model"></a>
<a id="get_available_models"></a>
<a id="set_thinking_level"></a>
<a id="cycle_thinking_level"></a>
<a id="get_available_thinking_levels"></a>
<a id="set_steering_mode"></a>
<a id="set_follow_up_mode"></a>
<a id="compact"></a>
<a id="set_auto_compaction"></a>
<a id="set_auto_retry"></a>
<a id="abort_retry"></a>
<a id="bash"></a>
<a id="abort_bash"></a>
<a id="get_session_stats"></a>
<a id="export_html"></a>
<a id="switch_session"></a>
<a id="fork"></a>
<a id="clone"></a>
<a id="get_fork_messages"></a>
<a id="get_entries"></a>
<a id="get_tree"></a>
<a id="get_last_assistant_text"></a>
<a id="set_session_name"></a>
<a id="get_commands"></a>

Command details moved to [RPC Commands](rpc-commands.md).

<a id="message_update-streaming"></a>
<a id="bash_execution_update"></a>
<a id="compaction_start--compaction_end"></a>
<a id="summarization_retry_scheduled--summarization_retry_attempt_start--summarization_retry_finished"></a>

Event details moved to [JSON Event Stream](json.md).

<a id="extension-ui-protocol"></a>

Extension interaction details moved to [RPC Extension UI](rpc-extension-ui.md).

---

## RPC Commands

This reference lists commands accepted on stdin in [RPC mode](rpc.md). Each command and response is one JSON object. Shared message values use the [message types](message-types.md).

## Prompting

### prompt

Send a user prompt to the agent. The command response is emitted after the prompt is accepted, queued, or handled. Events continue streaming asynchronously after acceptance.

```json
{"id": "req-1", "type": "prompt", "message": "Hello, world!"}
```

With images:
```json
{"type": "prompt", "message": "What's in this image?", "images": [{"type": "image", "data": "base64-encoded-data", "mimeType": "image/png"}]}
```

**During streaming**: If the agent is already streaming, you must specify `streamingBehavior` to queue the message:

```json
{"type": "prompt", "message": "New instruction", "streamingBehavior": "steer"}
```

- `"steer"`: Queue the message while the agent is running. It is delivered after the current assistant turn finishes executing its tool calls, before the next LLM call.
- `"followUp"`: Wait until the agent finishes. Message is delivered only when agent stops.

If the agent is streaming and no `streamingBehavior` is specified, the command returns an error.

**Extension commands**: If the message is an extension command (e.g., `/mycommand`), it executes immediately even during streaming. Extension commands manage their own LLM interaction via `pi.sendMessage()`.

**Input expansion**: Skill commands (`/skill:name`) and prompt templates (`/template`) are expanded before sending/queueing.

Response:
```json
{"id": "req-1", "type": "response", "command": "prompt", "success": true, "data": {"disposition": "started"}}
```

`data.disposition` is `"handled"` if an extension command or input handler consumed the prompt, `"queued"` if Pi queued it during a run, or `"started"` if Pi accepted it to start a run. This describes the submitted prompt, not independent work started by an extension or a guarantee of completion.

`success: true` means the prompt was accepted, queued, or handled immediately. `success: false` means the prompt was rejected before acceptance. Failures after acceptance are reported through the normal event and message stream, not as a second `response` for the same request id.

The `images` field is optional. Each image uses `ImageContent` format: `{"type": "image", "data": "base64-encoded-data", "mimeType": "image/png"}`.

### steer

Queue a steering message while the agent is running. It is delivered after the current assistant turn finishes executing its tool calls, before the next LLM call. Skill commands and prompt templates are expanded. Extension commands are not allowed (use `prompt` instead).

```json
{"type": "steer", "message": "Stop and do this instead"}
```

With images:
```json
{"type": "steer", "message": "Look at this instead", "images": [{"type": "image", "data": "base64-encoded-data", "mimeType": "image/png"}]}
```

The `images` field is optional. Each image uses `ImageContent` format (same as `prompt`).

Response:
```json
{"type": "response", "command": "steer", "success": true, "data": {"disposition": "queued"}}
```

`data.disposition` is `"handled"` if an input handler consumed this steer, or `"queued"` if Pi queued it (including after a handler transformed it). It does not guarantee this message remains queued.

See [set_steering_mode](#set_steering_mode) for controlling how steering messages are processed.

### follow_up

Queue a follow-up message to be processed after the agent finishes. Delivered only when agent has no more tool calls or steering messages. Skill commands and prompt templates are expanded. Extension commands are not allowed (use `prompt` instead).

```json
{"type": "follow_up", "message": "After you're done, also do this"}
```

With images:
```json
{"type": "follow_up", "message": "Also check this image", "images": [{"type": "image", "data": "base64-encoded-data", "mimeType": "image/png"}]}
```

The `images` field is optional. Each image uses `ImageContent` format (same as `prompt`).

Response:
```json
{"type": "response", "command": "follow_up", "success": true, "data": {"disposition": "queued"}}
```

`data.disposition` has the same `"handled"` or `"queued"` meaning as for `steer`, applied to this follow-up.

See [set_follow_up_mode](#set_follow_up_mode) for controlling how follow-up messages are processed.

### abort

Abort the current operation and wait for the session to become idle before responding.

```json
{"type": "abort"}
```

Response:
```json
{"type": "response", "command": "abort", "success": true}
```

### clear_queue

Remove queued steering and follow-up messages and return their text.

```json
{"type": "clear_queue"}
```

Response:
```json
{
  "type": "response",
  "command": "clear_queue",
  "success": true,
  "data": {
    "steering": ["Change direction"],
    "followUp": ["Summarize when finished"]
  }
}
```

To implement interactive Esc behavior, send `clear_queue` before `abort`, then restore the returned text in the client editor. `abort` continues queued messages when they remain in the session.

### new_session

Start a fresh session. Can be canceled by a `session_before_switch` extension event handler.

```json
{"type": "new_session"}
```

With optional parent session tracking:
```json
{"type": "new_session", "parentSession": "/path/to/parent-session.jsonl"}
```

Response:
```json
{"type": "response", "command": "new_session", "success": true, "data": {"cancelled": false}}
```

If an extension canceled:
```json
{"type": "response", "command": "new_session", "success": true, "data": {"cancelled": true}}
```

## State

### get_state

Get current session state.

```json
{"type": "get_state"}
```

Response:
```json
{
  "type": "response",
  "command": "get_state",
  "success": true,
  "data": {
    "model": {...},
    "thinkingLevel": "medium",
    "isStreaming": false,
    "isCompacting": false,
    "steeringMode": "all",
    "followUpMode": "one-at-a-time",
    "sessionFile": "/path/to/session.jsonl",
    "sessionId": "abc123",
    "sessionName": "my-feature-work",
    "autoCompactionEnabled": true,
    "messageCount": 5,
    "pendingMessageCount": 0
  }
}
```

The `model` field is a full [Model](#model-object) object, or omitted when no model is selected. The `sessionName` field is the display name set via `set_session_name`, or omitted if not set.

### get_messages

Get all messages in the conversation.

```json
{"type": "get_messages"}
```

Response:
```json
{
  "type": "response",
  "command": "get_messages",
  "success": true,
  "data": {"messages": [...]}
}
```

Messages are `AgentMessage` objects (see [Message Types](message-types.md)).

## Model

### set_model

Switch to a specific model.

```json
{"type": "set_model", "provider": "anthropic", "modelId": "claude-sonnet-4-20250514"}
```

Response contains the full [Model](#model-object) object:
```json
{
  "type": "response",
  "command": "set_model",
  "success": true,
  "data": {...}
}
```

### cycle_model

Cycle to the next available model. Returns `null` data if only one model available.

```json
{"type": "cycle_model"}
```

Response:
```json
{
  "type": "response",
  "command": "cycle_model",
  "success": true,
  "data": {
    "model": {...},
    "thinkingLevel": "medium",
    "isScoped": false
  }
}
```

The `model` field is a full [Model](#model-object) object.

### get_available_models

List all configured models.

```json
{"type": "get_available_models"}
```

Response contains an array of full [Model](#model-object) objects:
```json
{
  "type": "response",
  "command": "get_available_models",
  "success": true,
  "data": {
    "models": [...]
  }
}
```

## Thinking

### set_thinking_level

Set the reasoning/thinking level for models that support it.

```json
{"type": "set_thinking_level", "level": "high"}
```

Levels: `"off"`, `"minimal"`, `"low"`, `"medium"`, `"high"`, `"xhigh"`, `"max"`

`"xhigh"` and `"max"` are exposed only when supported by the selected model. Some models, including GPT-5.6, expose both.

Response:
```json
{"type": "response", "command": "set_thinking_level", "success": true}
```

### cycle_thinking_level

Cycle through available thinking levels. Returns `null` data if model doesn't support thinking.

```json
{"type": "cycle_thinking_level"}
```

Response:
```json
{
  "type": "response",
  "command": "cycle_thinking_level",
  "success": true,
  "data": {"level": "high"}
}
```

### get_available_thinking_levels

List the thinking levels supported by the current model. Returns `["off"]` for a model without reasoning support.

```json
{"type": "get_available_thinking_levels"}
```

Response:
```json
{
  "type": "response",
  "command": "get_available_thinking_levels",
  "success": true,
  "data": {
    "levels": ["off", "minimal", "low", "medium", "high"]
  }
}
```

## Queue modes

### set_steering_mode

Control how steering messages (from `steer`) are delivered.

```json
{"type": "set_steering_mode", "mode": "one-at-a-time"}
```

Modes:
- `"all"`: Deliver all steering messages after the current assistant turn finishes executing its tool calls
- `"one-at-a-time"`: Deliver one steering message per completed assistant turn (default)

Response:
```json
{"type": "response", "command": "set_steering_mode", "success": true}
```

### set_follow_up_mode

Control how follow-up messages (from `follow_up`) are delivered.

```json
{"type": "set_follow_up_mode", "mode": "one-at-a-time"}
```

Modes:
- `"all"`: Deliver all follow-up messages when agent finishes
- `"one-at-a-time"`: Deliver one follow-up message per agent completion (default)

Response:
```json
{"type": "response", "command": "set_follow_up_mode", "success": true}
```

## Compaction

### compact

Manually compact conversation context to reduce token usage.

```json
{"type": "compact"}
```

With custom instructions:
```json
{"type": "compact", "customInstructions": "Focus on code changes"}
```

Response:
```json
{
  "type": "response",
  "command": "compact",
  "success": true,
  "data": {
    "summary": "Summary of conversation...",
    "firstKeptEntryId": "abc123",
    "tokensBefore": 150000,
    "estimatedTokensAfter": 32000,
    "usage": {
      "input": 32000,
      "output": 1200,
      "cacheRead": 0,
      "cacheWrite": 0,
      "totalTokens": 33200,
      "cost": {"input": 0.01, "output": 0.02, "cacheRead": 0, "cacheWrite": 0, "total": 0.03}
    },
    "details": {}
  }
}
```

`estimatedTokensAfter` is a heuristic estimate over the rebuilt message context immediately after compaction, not a provider-exact token count. `usage` reports the LLM call or calls that generated the summary and may be omitted by custom compaction handlers.

### set_auto_compaction

Enable or disable automatic compaction when context is nearly full.

```json
{"type": "set_auto_compaction", "enabled": true}
```

Response:
```json
{"type": "response", "command": "set_auto_compaction", "success": true}
```

## Retry

### set_auto_retry

Enable or disable automatic retry on transient errors (overloaded, rate limit, 5xx).

```json
{"type": "set_auto_retry", "enabled": true}
```

Response:
```json
{"type": "response", "command": "set_auto_retry", "success": true}
```

### abort_retry

Abort an in-progress retry (cancel the delay and stop retrying).

```json
{"type": "abort_retry"}
```

Response:
```json
{"type": "response", "command": "abort_retry", "success": true}
```

## Bash

### bash

Execute a shell command and add output to conversation context. Output streams as `bash_execution_update` events while the command runs; the response contains the final result.

```json
{"id": "req-1", "type": "bash", "command": "ls -la"}
```

Set `excludeFromContext` to `true` when the command output should be stored in the session but omitted from the model context on the next prompt.

Include an `id` to associate streamed `bash_execution_update` events with this command.

Response:
```json
{
  "id": "req-1",
  "type": "response",
  "command": "bash",
  "success": true,
  "data": {
    "output": "total 48\ndrwxr-xr-x ...",
    "exitCode": 0,
    "cancelled": false,
    "truncated": false
  }
}
```

If output was truncated, includes `fullOutputPath`:
```json
{
  "type": "response",
  "command": "bash",
  "success": true,
  "data": {
    "output": "truncated output...",
    "exitCode": 0,
    "cancelled": false,
    "truncated": true,
    "fullOutputPath": "/tmp/pi-bash-abc123.log"
  }
}
```

**How bash results reach the LLM:**

The `bash` command executes immediately and returns a `BashResult`. Internally, a `BashExecutionMessage` is created and stored in the agent's message state.

When the next `prompt` command is sent, Pi transforms context messages before sending them to the model. Unless `excludeFromContext` is true, the `BashExecutionMessage` becomes a `UserMessage` with this format:

````
Ran `ls -la`
```
total 48
drwxr-xr-x ...
```
````

This means:
1. Included bash output reaches the model on the **next prompt**, not immediately.
2. Multiple bash commands can run before a prompt; Pi includes each output that does not set `excludeFromContext`.

### abort_bash

Abort a running bash command.

```json
{"type": "abort_bash"}
```

Response:
```json
{"type": "response", "command": "abort_bash", "success": true}
```

## Session

### get_session_stats

Get token usage, cost statistics, and current context window usage.

```json
{"type": "get_session_stats"}
```

Response:
```json
{
  "type": "response",
  "command": "get_session_stats",
  "success": true,
  "data": {
    "sessionFile": "/path/to/session.jsonl",
    "sessionId": "abc123",
    "userMessages": 5,
    "assistantMessages": 5,
    "toolCalls": 12,
    "toolResults": 12,
    "totalMessages": 22,
    "tokens": {
      "input": 50000,
      "output": 10000,
      "cacheRead": 40000,
      "cacheWrite": 5000,
      "total": 105000
    },
    "cost": 0.45,
    "contextUsage": {
      "tokens": 60000,
      "contextWindow": 200000,
      "percent": 30
    }
  }
}
```

`tokens` and `cost` include assistant messages, usage reported by tools, and compaction/branch-summary generation across the full session. `contextUsage` contains the actual current context-window estimate used for compaction and footer display.

`contextUsage` is omitted when no model or context window is available. `contextUsage.tokens` and `contextUsage.percent` are `null` immediately after compaction until a fresh post-compaction assistant response provides valid usage data.

### export_html

Export session to an HTML file.

```json
{"type": "export_html"}
```

With custom path:
```json
{"type": "export_html", "outputPath": "/tmp/session.html"}
```

Response:
```json
{
  "type": "response",
  "command": "export_html",
  "success": true,
  "data": {"path": "/tmp/session.html"}
}
```

### switch_session

Load a different session file. Can be canceled by a `session_before_switch` extension event handler.

```json
{"type": "switch_session", "sessionPath": "/path/to/session.jsonl"}
```

Response:
```json
{"type": "response", "command": "switch_session", "success": true, "data": {"cancelled": false}}
```

If an extension canceled the switch:
```json
{"type": "response", "command": "switch_session", "success": true, "data": {"cancelled": true}}
```

### fork

Create a new fork from a previous user message on the active branch. Can be canceled by a `session_before_fork` extension event handler. Returns the text of the message being forked from.

```json
{"type": "fork", "entryId": "abc123"}
```

Response:
```json
{
  "type": "response",
  "command": "fork",
  "success": true,
  "data": {"text": "The original prompt text...", "cancelled": false}
}
```

If an extension canceled the fork:
```json
{
  "type": "response",
  "command": "fork",
  "success": true,
  "data": {"cancelled": true}
}
```

### clone

Duplicate the current active branch into a new session at the current position. Can be canceled by a `session_before_fork` extension event handler.

```json
{"type": "clone"}
```

Response:
```json
{
  "type": "response",
  "command": "clone",
  "success": true,
  "data": {"cancelled": false}
}
```

If an extension canceled the clone:
```json
{
  "type": "response",
  "command": "clone",
  "success": true,
  "data": {"cancelled": true}
}
```

### get_fork_messages

Get user messages available for forking.

```json
{"type": "get_fork_messages"}
```

Response:
```json
{
  "type": "response",
  "command": "get_fork_messages",
  "success": true,
  "data": {
    "messages": [
      {"entryId": "abc123", "text": "First prompt..."},
      {"entryId": "def456", "text": "Second prompt..."}
    ]
  }
}
```

### get_entries

Get all session entries in append order (excluding the session header). The session is an append-only tree of entries with stable ids, so an entry id works as a durable cursor: pass the last entry id you have seen as `since` to get only entries strictly after it, even across client restarts. Unlike `get_messages`, this includes pre-compaction history and abandoned branches.

```json
{"type": "get_entries"}
```

With a cursor:
```json
{"type": "get_entries", "since": "abc123"}
```

Response:
```json
{
  "type": "response",
  "command": "get_entries",
  "success": true,
  "data": {
    "entries": [
      {"type": "message", "id": "def456", "parentId": "abc123", "timestamp": "...", "message": {"role": "user", "...": "..."}}
    ],
    "leafId": "def456"
  }
}
```

`leafId` is the id of the current leaf entry (`null` for an empty session), so a client can tell in one round trip whether the active branch moved. If `since` does not match any entry id, the response is `success: false`.

### get_tree

Get the session as a tree of entries. Each node is `{entry, children, label?, labelTimestamp?}`. The result is an array because navigation APIs can create multiple roots; orphaned entries with broken parent chains also appear as roots.

```json
{"type": "get_tree"}
```

Response:
```json
{
  "type": "response",
  "command": "get_tree",
  "success": true,
  "data": {
    "tree": [
      {
        "entry": {"type": "message", "id": "abc123", "parentId": null, "...": "..."},
        "children": [
          {"entry": {"type": "message", "id": "def456", "parentId": "abc123", "...": "..."}, "children": []}
        ]
      }
    ],
    "leafId": "def456"
  }
}
```

### get_last_assistant_text

Get the text content of the last assistant message.

```json
{"type": "get_last_assistant_text"}
```

Response:
```json
{
  "type": "response",
  "command": "get_last_assistant_text",
  "success": true,
  "data": {"text": "The assistant's response..."}
}
```

The `text` value is `null` if no assistant text exists.

### set_session_name

Set a display name for the current session. The name appears in session listings and helps identify sessions.

```json
{"type": "set_session_name", "name": "my-feature-work"}
```

Response:
```json
{
  "type": "response",
  "command": "set_session_name",
  "success": true
}
```

The current session name is available via `get_state` in the `sessionName` field. To set the initial name when starting RPC mode, pass `--name <name>` or `-n <name>` to the `pi --mode rpc` process.

## Discoverable commands

### get_commands

Get available commands (extension commands, prompt templates, and skills). Run one through the `prompt` command by prefixing its name with `/`.

```json
{"type": "get_commands"}
```

Response:
```json
{
  "type": "response",
  "command": "get_commands",
  "success": true,
  "data": {
    "commands": [
      {
        "name": "fix-tests",
        "description": "Fix failing tests",
        "source": "prompt",
        "sourceInfo": {
          "path": "/home/user/myproject/.pi/agent/prompts/fix-tests.md",
          "source": "local",
          "scope": "project",
          "origin": "top-level"
        }
      }
    ]
  }
}
```

Each command has:
- `name`: Command name (use `/name`)
- `description`: Human-readable description (optional for extension commands)
- `source`: What kind of command:
  - `"extension"`: Registered via `pi.registerCommand()` in an extension
  - `"prompt"`: Loaded from a prompt template `.md` file
  - `"skill"`: Loaded from a skill directory (name is prefixed with `skill:`)
- `sourceInfo`: Metadata for the resource that registered the command:
  - `path`: Absolute path to the resource
  - `source`: How Pi discovered it, such as `"local"`, `"auto"`, or `"cli"`
  - `scope`: `"user"`, `"project"`, or `"temporary"`
  - `origin`: `"top-level"` for a directly loaded resource or `"package"` for a package resource
  - `baseDir`: Package base directory, when applicable

**Note**: Built-in TUI commands (`/settings`, `/hotkeys`, etc.) are not included. They are handled only in interactive mode and would not execute if sent via `prompt`.

## Model object

Model commands return the complete configured model definition. Costs are in US dollars per million tokens.

```json
{
  "id": "claude-sonnet-4-20250514",
  "name": "Claude Sonnet 4",
  "api": "anthropic-messages",
  "provider": "anthropic",
  "baseUrl": "https://api.anthropic.com",
  "reasoning": true,
  "input": ["text", "image"],
  "contextWindow": 200000,
  "maxTokens": 16384,
  "cost": {
    "input": 3.0,
    "output": 15.0,
    "cacheRead": 0.3,
    "cacheWrite": 3.75
  }
}
```

For model configuration, see [Configure a compatible endpoint](models.md#configure-a-compatible-endpoint). For TypeScript, use the exported `Model` type from `@earendil-works/pi-ai`.

---

## RPC Extension UI

Extensions can request user interaction through `ctx.ui`. In RPC mode, supported calls become a request/response subprotocol alongside normal [RPC commands](rpc-commands.md) and [session events](json.md).

There are two categories of extension UI methods:

- **Dialog methods** (`select`, `confirm`, `input`, `editor`): emit an `extension_ui_request` on stdout and block until the client sends back an `extension_ui_response` on stdin with the matching `id`.
- **Fire-and-forget methods** (`notify`, `setStatus`, `setWidget`, `setTitle`, `set_editor_text`): emit an `extension_ui_request` on stdout but do not expect a response. The client can display the information or ignore it.

If a dialog method includes a `timeout` field, the agent-side will auto-resolve with a default value when the timeout expires. The client does not need to track timeouts.

## Limitations

Some `ExtensionUIContext` methods are not supported or degraded in RPC mode because they require direct terminal UI access:

- `custom()` returns `undefined`.
- `onTerminalInput()` returns a no-op unsubscribe function.
- `setWorkingMessage()`, `setWorkingVisible()`, `setWorkingIndicator()`, `setHiddenThinkingLabel()`, `setFooter()`, `setHeader()`, `addAutocompleteProvider()`, `setEditorComponent()`, and `setToolsExpanded()` are no-ops.
- `getEditorText()` returns `""` and `getEditorComponent()` returns `undefined`.
- `getToolsExpanded()` returns `false`.
- `pasteToEditor()` delegates to `setEditorText()` without terminal paste handling.
- `getAllThemes()` returns `[]`, and `getTheme()` returns `undefined`.
- `setTheme()` returns `{ success: false, error: "Theme switching not supported in RPC mode" }`.

Note: `ctx.mode` is `"rpc"` and `ctx.hasUI` is `true` in RPC mode because the dialog and fire-and-forget methods are functional via the extension UI sub-protocol. Use `ctx.mode === "tui"` to guard TUI-specific features like `custom()` that require a real terminal.

## Requests from Pi

All requests have `type: "extension_ui_request"`, a unique `id`, and a `method` field.

### select

Prompt the user to choose from a list. Dialog methods with a `timeout` field include the timeout in milliseconds; the agent auto-resolves with `undefined` if the client doesn't respond in time.

```json
{
  "type": "extension_ui_request",
  "id": "uuid-1",
  "method": "select",
  "title": "Allow dangerous command?",
  "options": ["Allow", "Block"],
  "timeout": 10000
}
```

Expected response: `extension_ui_response` with `value` (the selected option string) or `cancelled: true`.

### confirm

Prompt the user for yes/no confirmation.

```json
{
  "type": "extension_ui_request",
  "id": "uuid-2",
  "method": "confirm",
  "title": "Clear session?",
  "message": "All messages will be lost.",
  "timeout": 5000
}
```

Expected response: `extension_ui_response` with `confirmed: true/false` or `cancelled: true`.

### input

Prompt the user for free-form text.

```json
{
  "type": "extension_ui_request",
  "id": "uuid-3",
  "method": "input",
  "title": "Enter a value",
  "placeholder": "type something..."
}
```

Expected response: `extension_ui_response` with `value` (the entered text) or `cancelled: true`.

### editor

Open a multi-line text editor with optional prefilled content.

```json
{
  "type": "extension_ui_request",
  "id": "uuid-4",
  "method": "editor",
  "title": "Edit some text",
  "prefill": "Line 1\nLine 2\nLine 3"
}
```

Expected response: `extension_ui_response` with `value` (the edited text) or `cancelled: true`.

### notify

Display a notification. Fire-and-forget, no response expected.

```json
{
  "type": "extension_ui_request",
  "id": "uuid-5",
  "method": "notify",
  "message": "Command blocked by user",
  "notifyType": "warning"
}
```

The `notifyType` field is `"info"`, `"warning"`, or `"error"`. Defaults to `"info"` if omitted.

### setStatus

Set or clear a status entry in the footer/status bar. Fire-and-forget.

```json
{
  "type": "extension_ui_request",
  "id": "uuid-6",
  "method": "setStatus",
  "statusKey": "my-ext",
  "statusText": "Turn 3 running..."
}
```

Send `statusText: undefined` (or omit it) to clear the status entry for that key.

### setWidget

Set or clear a widget (block of text lines) displayed above or below the editor. Fire-and-forget.

```json
{
  "type": "extension_ui_request",
  "id": "uuid-7",
  "method": "setWidget",
  "widgetKey": "my-ext",
  "widgetLines": ["--- My Widget ---", "Line 1", "Line 2"],
  "widgetPlacement": "aboveEditor"
}
```

Send `widgetLines: undefined` (or omit it) to clear the widget. The `widgetPlacement` field is `"aboveEditor"` (default) or `"belowEditor"`. Only string arrays are supported in RPC mode; component factories are ignored.

### setTitle

Set the terminal window/tab title. Fire-and-forget.

```json
{
  "type": "extension_ui_request",
  "id": "uuid-8",
  "method": "setTitle",
  "title": "pi - my project"
}
```

### set_editor_text

Set the text in the input editor. Fire-and-forget.

```json
{
  "type": "extension_ui_request",
  "id": "uuid-9",
  "method": "set_editor_text",
  "text": "prefilled text for the user"
}
```

## Responses to Pi

Responses are sent for dialog methods only (`select`, `confirm`, `input`, `editor`). The `id` must match the request.

### Value response (select, input, editor)

```json
{"type": "extension_ui_response", "id": "uuid-1", "value": "Allow"}
```

### Confirmation response (confirm)

```json
{"type": "extension_ui_response", "id": "uuid-2", "confirmed": true}
```

### Cancellation response (any dialog)

Dismiss any dialog method. The extension receives `undefined` (for select/input/editor) or `false` (for confirm).

```json
{"type": "extension_ui_response", "id": "uuid-3", "cancelled": true}
```

## Example

See the checked [RPC extension UI client](../examples/rpc-extension-ui.ts) and its [demo extension](../examples/extensions/rpc-demo.ts).

The exported request and response unions are defined in [`rpc-types.ts`](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/src/modes/rpc/rpc-types.ts). See [Extensions](extensions.md#ui-and-modes) for mode-independent extension guidance.
