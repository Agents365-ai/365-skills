# Examples and Non-Examples

Concrete patterns and anti-patterns referenced from `SKILL.md`. Read this when you need to show the user what a good envelope, error, dry-run, or batch response actually looks like — or when you need to make an anti-pattern visible.

---

## Good examples

### Example 1 — Structured error with routing fields

```json
{
  "ok": false,
  "error": {
    "code": "auth_expired",
    "message": "Token expired. Re-authenticate to continue.",
    "retryable": true,
    "retry_after_auth": true
  }
}
```

The agent can read `retry_after_auth: true` and escalate to re-authentication without parsing prose.

### Example 2 — Layered self-description

```bash
$ healthkit --help
Usage: healthkit <resource> <action> [options]

Resources:
  sleep       Sleep records and stages
  steps       Step count and activity
  heart       Heart rate and HRV

$ healthkit sleep --help
Actions:
  list        List sleep records by date range
  summary     Aggregate sleep statistics

$ healthkit sleep list --help
Flags:
  --start-date  ISO date (required)
  --end-date    ISO date (required)
  --format      json|table (default: json)
  --dry-run     Preview request, do not execute
```

An agent can traverse this tree to discover valid commands without reading external docs.

### Example 3 — Delegated auth with env trust boundary

```bash
# Human / system runs once, out of band (shell profile, systemd unit, supervisor):
healthkit auth login                              # browser OAuth2 flow, stores token in keychain
export HEALTHKIT_TOKEN="$(healthkit auth token)"  # token is injected into the agent's environment

# Agent's own commands — it never invokes `auth login` or `auth token`:
healthkit sleep list --start-date 2026-01-01 --end-date 2026-01-07
```

The agent inherits `HEALTHKIT_TOKEN` from an environment it did not build. It never runs the login subcommand, never runs the `auth token` retrieval subcommand, and never handles refresh — those belong to the human or the orchestrator. The env var is the trust boundary; the agent consumes credentials, it does not fetch them.

### Example 4 — Dry-run preview before execution

```bash
$ healthkit sleep list --start-date 2026-01-01 --end-date 2026-01-07 --dry-run
{
  "ok": true,
  "dry_run": true,
  "would_request": {
    "method": "GET",
    "url": "https://health.api/v1/sleep",
    "params": { "startDate": "2026-01-01", "endDate": "2026-01-07" }
  }
}
```

The agent can verify the request shape before committing to execution.

### Example 5 — Schema introspection

```bash
$ healthkit schema sleep.list
{
  "method": "sleep.list",
  "params": {
    "startDate": { "type": "string", "format": "date", "required": true },
    "endDate":   { "type": "string", "format": "date", "required": true },
    "pageSize":  { "type": "integer", "default": 20, "max": 100 }
  }
}
```

### Example 6 — Idempotent batch with partial success, next hint, and meta

```bash
$ healthkit alerts send-bulk \
    --recipients "user1,user2,user3" \
    --message "Reminder: log today's sleep" \
    --idempotency-key "alert-batch-2026-04-11-am"
{
  "ok": "partial",
  "data": {
    "succeeded": [
      { "recipient": "user1", "alert_id": "alrt_abc" },
      { "recipient": "user2", "alert_id": "alrt_def" }
    ],
    "failed": [
      {
        "recipient": "user3",
        "error": {
          "code": "rate_limited",
          "message": "Per-recipient rate limit exceeded",
          "retryable": true,
          "retry_after_seconds": 60
        }
      }
    ]
  },
  "next": [
    "healthkit alerts send-bulk --recipients user3 --message 'Reminder: log today\\'s sleep' --idempotency-key alert-batch-2026-04-11-am"
  ],
  "meta": {
    "request_id": "req_8fa9c1",
    "latency_ms": 412,
    "schema_version": "1.4.0"
  }
}
```

`ok: "partial"` plus per-item `error.retryable` plus the `next` slot plus a stable idempotency key give the agent everything it needs to recover in one round-trip — it does not need to re-process `user1` / `user2`, it knows exactly which item to retry, and re-running with the same `--idempotency-key` is safe.

### Example 7 — Long-running export with structured stderr progress

```bash
$ healthkit export run --dataset sleep --since 2024-01-01 --format parquet > result.json
```

stderr — one JSON object per line, agent reads for liveness without blocking on stdout:

```
{ "event": "start",    "command": "export.run", "request_id": "req_abc123" }
{ "event": "progress", "phase": "fetch", "done": 240, "total": 730, "elapsed_ms": 18421 }
{ "event": "progress", "phase": "fetch", "done": 730, "total": 730, "elapsed_ms": 54017 }
{ "event": "progress", "phase": "write", "done": 730, "total": 730, "elapsed_ms": 56103 }
{ "event": "complete", "request_id": "req_abc123", "elapsed_ms": 56234 }
```

stdout — single envelope at the end:

```json
{
  "ok": true,
  "data": { "rows": 730, "path": "/tmp/sleep_export.parquet", "size_bytes": 142336 },
  "meta": { "request_id": "req_abc123", "latency_ms": 56234 }
}
```

What this gives the agent: liveness via stderr without polluting the stdout envelope; phase visibility (`fetch` vs `write`) so it can localize bottlenecks; one clean result object captured by the redirect; and a single `request_id` correlating stderr progress, stdout result, and upstream service logs.

### Example 8 — Schema versioning with deprecation signals

An agent that calls the CLI in a loop may have cached an older view of the schema. Versioning in the response envelope lets the agent detect drift without failing silently.

```bash
$ healthkit sleep list --start-date 2026-01-01 --end-date 2026-01-07
{
  "ok": true,
  "data": [{ "id": "sl_001", "date": "2026-01-01", "minutes": 412 }],
  "meta": {
    "schema_version": "1.4.0",
    "deprecated_fields": ["page_size"],
    "introduced_in": "1.2.0",
    "request_id": "req_abc123"
  }
}
```

Schema introspection route:

```bash
$ healthkit schema sleep.list
{
  "method": "sleep.list",
  "introduced_in": "1.2.0",
  "schema_version": "1.4.0",
  "params": {
    "startDate": { "type": "string", "format": "date", "required": true },
    "endDate":   { "type": "string", "format": "date", "required": true },
    "pageSize":  { "type": "integer", "default": 20, "max": 100 },
    "page_size": { "type": "integer", "deprecated": true, "replaced_by": "pageSize", "removed_in": "1.5.0" }
  }
}
```

The agent compares its cached `schema_version` against the response's; on mismatch, it re-discovers before re-planning. Deprecation signals (`deprecated_fields`, `replaced_by`, `removed_in`) let it migrate proactively, and non-breaking additions don't invalidate cached calls — they just leave the cache incomplete.

---

## Non-examples

### Non-Example 1 — Prose-only error

```
Error: something went wrong with your request. Please check your input and try again.
```

The agent cannot determine: what went wrong, whether to retry, what to fix, which field failed. It must guess or give up.

### Non-Example 2 — Mixed stdout

```
Fetching sleep records...
Found 7 records.
{"records": [...]}
Done.
```

The agent cannot reliably parse JSON because stdout contains prose mixed with data.

### Non-Example 3 — No self-description

```bash
$ mytool --help
Usage: mytool [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.
```

No resources, no actions, no schema. An agent must guess or hallucinate command names.

### Non-Example 4 — Auth via agent-supplied argument

```bash
mytool --token $AGENT_GENERATED_TOKEN delete --id abc123
```

The agent controls the token. A compromised agent can use any token it manufactures, bypassing human trust boundaries.

### Non-Example 5 — Destructive commands fully exposed

```bash
$ mytool --help
Commands:
  list    List records
  get     Get a record
  delete  Delete a record        ← appears at same level as read commands
  purge   Purge all records      ← no warning, no gate
```

An agent browsing help can trivially discover and invoke destructive commands.

### Non-Example 6 — Ambiguous exit codes

```bash
$ mytool list; echo $?
# Returns 1 on API error
# Returns 1 on validation error
# Returns 1 on auth error
# Returns 1 on network error
```

Exit code 1 means everything. The orchestrator cannot route failures deterministically.
