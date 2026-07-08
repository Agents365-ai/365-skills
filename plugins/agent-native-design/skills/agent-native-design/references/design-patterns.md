# Design Patterns

Reference details for specific design areas. SKILL.md states the principles; this file holds the concrete contracts and rules.

---

## Output envelopes

Success:

```json
{ "ok": true, "data": {} }
```

Failure:

```json
{
  "ok": false,
  "error": {
    "code": "validation_error",
    "message": "Missing required field: email",
    "field": "email",
    "retryable": false
  }
}
```

Partial success (batch operations):

```json
{
  "ok": "partial",
  "data": {
    "succeeded": [
      { "id": "msg_001", "status": "sent" },
      { "id": "msg_002", "status": "sent" }
    ],
    "failed": [
      {
        "id": "msg_003",
        "error": { "code": "rate_limited", "message": "Rate limit exceeded for recipient", "retryable": true }
      }
    ]
  }
}
```

A batch command that collapses any per-item failure into a top-level `ok: false` forces every agent to re-process its successful items on retry. AWS SQS's `ReportBatchItemFailures` and similar APIs settled on this per-item shape for the same reason. Pair partial success with an idempotency key on the batch as a whole so that re-running with the same key only re-issues the *failed* items.

Optional `meta` slot for observability:

```json
{
  "ok": true,
  "data": { "id": "abc123" },
  "meta": {
    "request_id": "req_8fa9c1",
    "latency_ms": 412,
    "schema_version": "1.4.0"
  }
}
```

`meta` is a freeform slot for telemetry the orchestrator may want without polluting `data`: `request_id` for log correlation, `latency_ms` for SLO tracking, `schema_version` so an agent can detect drift against a cached schema. When the underlying call has a token / quota cost the CLI knows about, surface it here too — `tokens_used`, `quota_remaining`. Optional and additive: agents that don't need it ignore it; agents that do gain observability without an extra round-trip. Aligns with where the OpenTelemetry GenAI semantic conventions are heading for tool-call traces.

---

## Schema versioning

This is the contract that lets agents cache schemas safely across calls.

Every response should carry `schema_version` in the optional `meta` block (see envelope above). When an agent's cached schema version (e.g., 1.2.0) doesn't match the CLI's current version (1.4.0), the agent knows to re-discover before re-planning.

Schema introspection responses should declare which CLI version produced them, when each method was introduced, and whether any field is deprecated:

```json
{
  "method": "sleep.list",
  "since": "1.2.0",
  "deprecated": false,
  "params": {
    "startDate": { "type": "string", "format": "date", "required": true },
    "endDate":   { "type": "string", "format": "date", "required": true },
    "page_size": { "type": "integer", "default": 20, "max": 100, "deprecated": true, "replaced_by": "pageSize", "removed_in": "1.5.0" }
  }
}
```

This gives agents:

- **Drift detection** — cached version mismatch triggers re-discovery before re-planning.
- **Deprecation awareness** — agents migrate off `page_size` to `pageSize` proactively, before removal.
- **Non-breaking updates** — adding a new optional field or method makes cached schemas incomplete but not incorrect; existing calls keep working.
- **Token efficiency** — agents don't waste tokens on removed methods or obsolete fields; drift is corrected in one round-trip.

API stability is a contract you owe the agent: a CLI that renames flags between point releases forces every dependent agent to re-discover and re-plan. Treat the schema as a versioned, append-mostly surface.

See `references/examples.md` Example 8 for the full request/response pair.

---

## Exit code model

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Runtime / API error |
| `2` | Auth error |
| `3` | Validation error |

Exact codes may vary — the mapping must be documented and deterministic. (`sysexits.h` defines a richer pre-agent vocabulary — `EX_USAGE=64`, `EX_DATAERR=65`, `EX_NOPERM=77`, `EX_CONFIG=78` — and a CLI is free to use it. The 0–3 mapping above is a deliberate simplification for agent routing; what matters is that codes are documented, stable, and distinct per failure class.)

---

## Idempotency and retry

Agents retry. Networks fail, processes get killed, exit codes get misread. A CLI that is not idempotent forces every agent that uses it to write special-case retry logic — and most agents will get it wrong.

Every mutating command should accept `--idempotency-key <string>`. A retried call carrying the same key must be a safe no-op that returns the original result, in the same `ok` / `error` shape. The CLI is responsible for storing the key↔result mapping for long enough that legitimate retries can find it (typically minutes; the upper bound belongs to the underlying API).

This pairs with the `retryable` field in the error envelope: `retryable: true` tells the agent it is *safe* to call again with the same idempotency key, and that doing so will eventually converge; `retryable: false` tells the agent that retrying will not change the outcome.

> "Agents retry. Networks fail. Commands get interrupted. If your `create` command fails on the second run because the resource already exists, the agent has to write special-case retry logic." — Ugo Enyioha, *Writing CLI Tools That AI Agents Actually Want to Use* (Feb 2025)

---

## Non-interactive operation

An agent cannot answer a confirmation prompt, cannot type a password into a TTY, and cannot navigate a curses-style menu. A CLI that hangs waiting for stdin when stdin is not a TTY is, from the agent's perspective, broken.

Rules:

- **Never prompt when stdin is not a TTY.** Detect at startup; if a confirmation would normally fire but `isatty(stdin) == false`, return a structured error instead of blocking:
  ```json
  { "ok": false, "error": { "code": "confirmation_required", "message": "Pass --yes to confirm.", "retryable": false } }
  ```
- **Always support `--yes` / `--no-input` / `--force`** (or equivalent) on every command that would otherwise prompt, so a human running interactively can opt out and an agent always runs without prompts.
- **Never read secrets from interactive prompts in agent contexts.** Secrets come from environment variables or pre-set config (see Principle 7).
- **Pagers off when stdout is not a TTY.** Detect at startup; never invoke `less` / `more` style pagers that would block on a non-TTY consumer.

> "An agent cannot type 'y' at a confirmation prompt. If your CLI hangs waiting for input, the agent's workflow is dead." — Ugo Enyioha (Feb 2025)

---

## Long-running commands and streaming

A command that takes minutes to finish is a hazard for an agent: the agent does not know whether the CLI is making progress, stuck, or dead, and it cannot afford to wait blind on a single JSON envelope at the end. Two patterns work:

**Structured progress on stderr, final JSON on stdout.** The agent reads stderr for liveness and stdout for the result. Progress events are themselves structured (one JSON object per line) so the orchestrator can parse them, but they never pollute the stdout JSON envelope. See `references/examples.md` Example 7 for a full transcript.

**NDJSON streaming for long lists.** When a list command might return thousands of items, offer a `--stream` (or `--ndjson`) mode that emits one JSON object per line on stdout, with a final summary line. Agents can process the stream incrementally and stop when they have enough:

```
$ healthkit sleep list --since 2024-01-01 --stream
{ "ok": true, "data": { "id": "sl_001", "date": "2024-01-01", "minutes": 412 } }
{ "ok": true, "data": { "id": "sl_002", "date": "2024-01-02", "minutes": 388 } }
...
{ "ok": true, "summary": { "count": 730, "has_more": false } }
```

Either way: the agent must be able to tell, from output alone, whether the command is *making progress*, *finished*, or *failed*. Silent multi-minute waits are an availability bug, not a UX preference.

---

## Reducing agent round-trips

The cost of every CLI invocation an agent makes is paid twice: once in latency, once in context tokens. A CLI that takes three calls to surface what an agent needs in order to plan its next step is, for the agent, *worse* than one that takes one call — even if every individual call is faster. Optimize for round-trip count, not just per-call performance.

Concrete tactics:

- **Pre-compute aggregates in list responses.** A `list` that returns `{ "ok": true, "data": [...], "count": 7, "has_more": false }` saves a follow-up `count` call.
- **Definitive empty states.** Return `{ "ok": true, "data": [], "count": 0 }`, never `null`. The agent should never have to disambiguate "no results" from "missing field."
- **Field selection on the response side.** Borrow from `gh --json title,number,state`: let callers ask for only the fields they need so list responses stay small and a follow-up "give me more detail on item N" is the exception, not the rule.
- **Compact default, `--full` escape hatch.** List items should carry 3–4 fields by default; agents that need more pass an opt-in flag rather than parsing huge default payloads on every call.
- **Next-step hints in success responses.** When the agent's likely next action is predictable, include a `next` slot: `{ "ok": true, "data": {...}, "next": ["healthkit sleep summary --start-date 2026-01-01 --end-date 2026-01-07"] }`. The agent saves a discovery turn.
- **Cursor pagination in the envelope.** `{ "ok": true, "data": [...], "page": { "next_cursor": "...", "has_more": true } }` so the agent can decide whether to continue without parsing prose pagination markers.

---

## Help design

Progressive, not monolithic: capability overview → resource → action → schema → examples → dry-run. A CLI with hundreds of commands should not dump its full schema into the agent's context on the first call. Top-level `--help` should be small enough to fit in a few hundred tokens; deeper detail is loaded on demand only when the agent has narrowed its target.

Anthropic's *Code execution with MCP* (Nov 2025) reports the same insight from the MCP world: in one Google-Drive→Salesforce case, lazy-loading tool definitions reduced token usage from 150,000 to 2,000 — a 98.7% saving. The CLI equivalent is the layered help tree plus response-side field selection (`gh pr list --json number,title,state`).

---

## Safety design

Read actions: easy to discover. Write actions: clearly marked. Destructive actions: hidden, gated, or separately enabled. Dry-run: everywhere feasible.

Tier table:

| Tier | Commands | Exposure |
|------|----------|----------|
| preview | all commands | dry-run available everywhere |
| open | list / get / search | full docs, easy to discover |
| warned | create / update / send | explicit warning in help and skills |
| hidden | delete / purge / empty | excluded from skills, gated separately |

Tiers are necessary but not sufficient. Graduated visibility is a prompt-side defense — it works only when the agent reads the warning and respects it, and approval fatigue degrades that defense quickly. Anthropic's *Beyond permission prompts* (Oct 2025) reports that OS-level sandboxing "safely reduces permission prompts by 84%." An agent-native CLI should assume the agent runtime will additionally sandbox it at the OS level (filesystem, network, processes), and design destructive commands to fail closed inside that sandbox rather than relying on a single layer of warnings.

---

## Auth design

Human/system-managed token acquisition. Environment/config-based delegation. No agent involvement in browser auth flows. Separation between auth bootstrap and agent execution. See `references/examples.md` Example 3 for the canonical pattern.

---

## Locale, time, and determinism

Agent behavior breaks subtly when CLI output depends on the host's locale or timezone. Pin determinism at the CLI boundary so the agent never has to second-guess what `2026-04-11` means or whether `1,234.56` is one number or two.

- **All timestamps are UTC ISO-8601** with explicit timezone (`2026-04-11T14:30:00Z`), not local time and not Unix epoch unless explicitly requested.
- **All dates are ISO-8601** (`2026-04-11`), never `04/11/2026` or `11/04/2026`.
- **Numeric formats are locale-independent.** Decimal point `.`, no thousands separators in JSON output. (`1234.56`, never `1,234.56` or `1.234,56`.)
- **Internal subprocess calls run under `LC_ALL=C`** (or equivalent), so any tool the CLI shells out to — `date`, `sort`, `awk` — produces the same bytes on every host.
- **Sort orders are documented and stable.** Default sort is byte-wise unless the schema says otherwise.
